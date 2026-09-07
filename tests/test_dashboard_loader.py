"""Unit tests for dashboard.loader module.

Verifies manifest parsing, review-item extraction, property normalization,
pagination, DSA discovery aggregation, and SQL data loading using mocks.
Does not make real network calls or mutate any data.
"""

import json
import os
from unittest.mock import MagicMock, patch
import pytest

from dashboard.loader import (
    ManifestSummary,
    NormalizedNotionRecord,
    ReviewItem,
    extract_property_value,
    get_config_value,
    get_pipeline_overview,
    get_read_only_notion_client,
    load_dsa_data,
    load_manifest_state,
    load_sql_data,
    normalize_notion_page,
    query_all_records,
)


# ---------------------------------------------------------------------------
# 1. Manifest Loading & Review Items Tests
# ---------------------------------------------------------------------------

def test_load_manifest_state_from_real_file():
    """Verify loading against the actual repository manifest.json."""
    if not os.path.exists("manifest.json"):
        pytest.skip("manifest.json not present in root")

    summary = load_manifest_state("manifest.json")
    assert isinstance(summary, ManifestSummary)
    assert summary.total_processed >= 1
    assert summary.success_count + summary.needs_review_count + summary.skipped_unclassified_count == summary.total_processed

    # In the actual repository manifest, there are needs_review items
    if summary.needs_review_count > 0:
        assert len(summary.review_items) >= 1
        for item in summary.review_items:
            assert isinstance(item, ReviewItem)
            assert item.status == "needs_review"
            assert item.file_id != ""
            assert item.reason != ""


def test_load_manifest_state_synthetic(tmp_path):
    """Verify manifest loading with various statuses and multi-payload review items."""
    manifest_data = {
        "version": "1.0.0",
        "name": "synapse-sync-manifest",
        "last_synced_at": "2026-09-07T12:00:00Z",
        "processed": {
            "file_success_1": {
                "status": "success",
                "content_hash": "hash_111"
            },
            "file_skipped_1": {
                "status": "skipped_unclassified",
                "content_hash": "hash_222"
            },
            "file_review_multi": {
                "status": "needs_review",
                "content_hash": "hash_333",
                "payloads": [
                    {
                        "domain": "DSA",
                        "type": "First Solve",
                        "data": {
                            "Problem": "Binary Tree Zigzag",
                            "Topic": "Binary Trees"
                        },
                        "segment_index": 1,
                        "reason": "First Solve entry already exists in database.",
                        "notion_payload": {"properties": {}}
                    },
                    {
                        "domain": "DSA",
                        "type": "Revision",
                        "data": {
                            "Problem": "Cousins in Binary Tree"
                        },
                        "segment_index": 2,
                        "reason": "Revision has no matching problem entry.",
                        "notion_payload": {"properties": {}}
                    }
                ]
            },
            "file_review_no_payload": {
                "status": "needs_review",
                "content_hash": "hash_444"
                # payloads key intentionally missing
            }
        }
    }

    manifest_file = tmp_path / "test_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    summary = load_manifest_state(str(manifest_file))

    assert summary.total_processed == 4
    assert summary.success_count == 1
    assert summary.skipped_unclassified_count == 1
    assert summary.needs_review_count == 2
    assert summary.last_synced_at == "2026-09-07T12:00:00Z"

    # file_review_multi has 2 payloads + file_review_no_payload has 1 fallback = 3 review items
    assert len(summary.review_items) == 3

    # First item
    r1 = summary.review_items[0]
    assert r1.file_id == "file_review_multi"
    assert r1.problem_title == "Binary Tree Zigzag"
    assert r1.domain == "DSA"
    assert r1.segment_type == "First Solve"
    assert r1.topic == "Binary Trees"
    assert r1.reason == "First Solve entry already exists in database."
    assert r1.has_notion_payload is True

    # Second item
    r2 = summary.review_items[1]
    assert r2.file_id == "file_review_multi"
    assert r2.problem_title == "Cousins in Binary Tree"
    assert r2.segment_type == "Revision"

    # Third item (fallback for missing payloads)
    r3 = summary.review_items[2]
    assert r3.file_id == "file_review_no_payload"
    assert "no payload details" in r3.reason.lower()
    assert r3.has_notion_payload is False

    # Check to_dict()
    summary_dict = summary.to_dict()
    assert summary_dict["total_processed"] == 4
    assert len(summary_dict["review_items"]) == 3


def test_load_manifest_state_missing_file():
    """Verify defensive handling when manifest.json does not exist."""
    summary = load_manifest_state("non_existent_manifest.json")
    assert summary.total_processed == 0
    assert summary.success_count == 0
    assert summary.needs_review_count == 0
    assert summary.skipped_unclassified_count == 0
    assert summary.review_items == []


def test_load_manifest_state_corrupt_json(tmp_path):
    """Verify defensive handling when manifest file contains corrupt content."""
    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("{ incomplete json ...", encoding="utf-8")

    summary = load_manifest_state(str(corrupt_file))
    assert summary.total_processed == 0
    assert summary.review_items == []


# ---------------------------------------------------------------------------
# 2. Notion Property Normalization Tests
# ---------------------------------------------------------------------------

def test_extract_property_value_types():
    """Test extract_property_value across various Notion property structures."""
    # Title
    assert extract_property_value({"type": "title", "title": [{"plain_text": "Two Sum"}]}) == "Two Sum"
    # Rich text
    assert extract_property_value({"type": "rich_text", "rich_text": [{"plain_text": "Notes"}]}) == "Notes"
    # Date
    assert extract_property_value({"type": "date", "date": {"start": "2026-09-01"}}) == "2026-09-01"
    # Select
    assert extract_property_value({"type": "select", "select": {"name": "High"}}) == "High"
    # Status
    assert extract_property_value({"type": "status", "status": {"name": "In Progress"}}) == "In Progress"
    # Multi-select
    assert extract_property_value({
        "type": "multi_select",
        "multi_select": [{"name": "Arrays"}, {"name": "Hashing"}]
    }) == "Arrays, Hashing"

    # None / Empty cases
    assert extract_property_value(None) is None
    assert extract_property_value({}) is None
    assert extract_property_value({"type": "date", "date": None}) is None
    assert extract_property_value({"type": "select", "select": None}) is None


def test_normalize_notion_page_dsa_first_solve():
    """Test normalizing a DSA first solve page object."""
    raw_page = {
        "id": "page_dsa_1",
        "created_time": "2026-09-01T10:00:00Z",
        "last_edited_time": "2026-09-01T10:05:00Z",
        "properties": {
            "Problem Name": {
                "type": "title",
                "title": [{"plain_text": "Zigzag Traversal"}]
            },
            "Date solved": {
                "type": "date",
                "date": {"start": "2026-09-01"}
            },
            "Pattern / Bucket": {
                "type": "multi_select",
                "multi_select": [{"name": "Tree Views"}]
            },
            "Revision Needed": {
                "type": "select",
                "select": {"name": "Mid"}
            }
        }
    }

    record = normalize_notion_page(raw_page, domain="DSA", topic="Binary Trees")
    assert record.page_id == "page_dsa_1"
    assert record.title == "Zigzag Traversal"
    assert record.domain == "DSA"
    assert record.topic == "Binary Trees"
    assert record.date_solved == "2026-09-01"
    assert record.revision_date is None
    assert record.is_revised is False
    assert record.revision_needed == "Mid"
    assert record.second_revision_needed is None
    assert record.bucket == "Tree Views"
    assert record.difficulty is None


def test_normalize_notion_page_dsa_revision():
    """Test normalizing a DSA page that has been revised."""
    raw_page = {
        "id": "page_dsa_rev",
        "properties": {
            "Problem": {
                "type": "title",
                "title": [{"plain_text": "Reverse Linked List"}]
            },
            "Date solved": {
                "type": "date",
                "date": {"start": "2026-08-15"}
            },
            "Revision Date": {
                "type": "date",
                "date": {"start": "2026-09-05"}
            },
            "2nd Revision Needed": {
                "type": "select",
                "select": {"name": "Low"}
            }
        }
    }

    record = normalize_notion_page(raw_page, domain="DSA", topic="LinkedList")
    assert record.title == "Reverse Linked List"
    assert record.is_revised is True
    assert record.revision_date == "2026-09-05"
    assert record.second_revision_needed == "Low"


def test_normalize_notion_page_sql():
    """Test normalizing an SQL tracker page object."""
    raw_page = {
        "id": "page_sql_1",
        "properties": {
            "Problem": {
                "type": "title",
                "title": [{"plain_text": "Parts Assembly"}]
            },
            "Date Solved": {
                "type": "date",
                "date": {"start": "2026-09-05"}
            },
            "Difficulty": {
                "type": "select",
                "select": {"name": "Easy"}
            },
            "Bucket": {
                "type": "select",
                "select": {"name": "Bucket 1 — Fundamentals"}
            },
            "Revision Needed": {
                "type": "select",
                "select": {"name": "Low"}
            }
        }
    }

    record = normalize_notion_page(raw_page, domain="SQL", topic="SQL")
    assert record.title == "Parts Assembly"
    assert record.domain == "SQL"
    assert record.topic == "SQL"
    assert record.difficulty == "Easy"
    assert record.bucket == "Bucket 1 — Fundamentals"
    assert record.revision_needed == "Low"
    assert record.is_revised is False


# ---------------------------------------------------------------------------
# 3. Paginated Notion Reads Tests
# ---------------------------------------------------------------------------

def test_query_all_records_pagination():
    """Verify that query_all_records iterates cursors until has_more is False."""
    client = MagicMock()

    page_1 = {
        "results": [{"id": "page_1"}, {"id": "page_2"}],
        "has_more": True,
        "next_cursor": "cursor_page_2"
    }
    page_2 = {
        "results": [{"id": "page_3"}],
        "has_more": False,
        "next_cursor": None
    }

    client.data_sources.query.side_effect = [page_1, page_2]

    results = query_all_records(client, "ds_123", page_size=2)

    assert len(results) == 3
    assert [r["id"] for r in results] == ["page_1", "page_2", "page_3"]
    assert client.data_sources.query.call_count == 2

    # Verify cursor passed on second call
    second_call_kwargs = client.data_sources.query.call_args_list[1][1]
    assert second_call_kwargs["start_cursor"] == "cursor_page_2"


def test_query_all_records_fallback_request():
    """Verify fallback to client.request if client.data_sources is not present."""
    client = MagicMock(spec=["request"])  # lacks data_sources attribute

    client.request.return_value = {
        "results": [{"id": "page_fallback"}],
        "has_more": False,
        "next_cursor": None
    }

    results = query_all_records(client, "ds_456")
    assert len(results) == 1
    assert results[0]["id"] == "page_fallback"
    assert client.request.call_count == 1


# ---------------------------------------------------------------------------
# 4. Domain Data Loading Tests (DSA & SQL)
# ---------------------------------------------------------------------------

@patch("dashboard.loader.discover_dsa_topics")
@patch("dashboard.loader.query_all_records")
def test_load_dsa_data(mock_query, mock_discover):
    """Verify load_dsa_data discovers topic databases and normalizes records."""
    client = MagicMock()
    mock_discover.return_value = {
        "Arrays": "ds_arrays",
        "Binary Trees": "ds_trees"
    }

    mock_query.side_effect = [
        # Arrays records
        [
            {
                "id": "p_arr_1",
                "properties": {"Problem": {"type": "title", "title": [{"plain_text": "Two Sum"}]}}
            }
        ],
        # Binary Trees records
        [
            {
                "id": "p_tree_1",
                "properties": {"Problem": {"type": "title", "title": [{"plain_text": "Invert Tree"}]}}
            },
            {
                "id": "p_tree_2",
                "properties": {"Problem": {"type": "title", "title": [{"plain_text": "Max Depth"}]}}
            }
        ]
    ]

    topic_map, records = load_dsa_data(client, parent_page_id="parent_page_123")

    assert topic_map == {"Arrays": "ds_arrays", "Binary Trees": "ds_trees"}
    assert len(records) == 3
    assert records[0].topic == "Arrays"
    assert records[0].title == "Two Sum"
    assert records[1].topic == "Binary Trees"
    assert records[1].title == "Invert Tree"
    assert records[2].topic == "Binary Trees"
    assert records[2].title == "Max Depth"


@patch("dashboard.loader.resolve_data_source_id")
@patch("dashboard.loader.query_all_records")
def test_load_sql_data(mock_query, mock_resolve):
    """Verify load_sql_data resolves DB ID and normalizes SQL records."""
    client = MagicMock()
    mock_resolve.return_value = "ds_sql_resolved"
    mock_query.return_value = [
        {
            "id": "p_sql_1",
            "properties": {
                "Problem": {"type": "title", "title": [{"plain_text": "Active Users"}]},
                "Difficulty": {"type": "select", "select": {"name": "Medium"}}
            }
        }
    ]

    records = load_sql_data(client, sql_db_id="db_sql_raw")

    assert len(records) == 1
    assert records[0].domain == "SQL"
    assert records[0].title == "Active Users"
    assert records[0].difficulty == "Medium"
    mock_resolve.assert_called_once_with(client, "db_sql_raw")


# ---------------------------------------------------------------------------
# 5. Configuration & Client Factory Tests
# ---------------------------------------------------------------------------

def test_get_config_value():
    """Verify configuration reading with fallback."""
    with patch.dict(os.environ, {"TEST_KEY": "test_value"}):
        assert get_config_value("TEST_KEY") == "test_value"
        assert get_config_value("MISSING_KEY", "fallback") == "fallback"


def test_get_read_only_notion_client():
    """Verify client initialization requiring NOTION_TOKEN."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="NOTION_TOKEN is required"):
            get_read_only_notion_client()

    client = get_read_only_notion_client(token="secret_test_token")
    assert client is not None


# ---------------------------------------------------------------------------
# 6. Pipeline Overview Aggregator Tests
# ---------------------------------------------------------------------------

@patch("dashboard.loader.load_manifest_state")
def test_get_pipeline_overview(mock_manifest):
    """Verify pipeline overview aggregation."""
    mock_manifest.return_value = ManifestSummary(
        version="1.0.0",
        total_processed=10,
        success_count=8,
        needs_review_count=1,
        skipped_unclassified_count=1,
        review_items=[ReviewItem(file_id="f1", status="needs_review", reason="Duplicate")]
    )

    overview = get_pipeline_overview("manifest.json")
    assert overview["status"] == "attention_needed"
    assert overview["total_manifest_processed"] == 10
    assert overview["success_count"] == 8
    assert overview["needs_review_count"] == 1
    assert overview["review_items_count"] == 1
