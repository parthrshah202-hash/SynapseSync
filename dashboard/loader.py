"""Read-only data access and normalization layer for the SynapseSync dashboard.

This module provides functions to inspect SynapseSync manifest state, query
Notion databases with full pagination, and normalize Notion records into
dashboard-friendly structures without exposing sensitive personal problem details.

CRITICAL: Strictly read-only. Does not mutate Notion or trigger pipeline runs.
"""

from dataclasses import asdict, dataclass, field
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from notion_client import Client

from src.notion_tools.discovery import discover_dsa_topics
from src.notion_tools.helpers import resolve_data_source_id

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class ReviewItem:
    """Represents a file or segment flagged as needing review."""
    file_id: str
    status: str
    reason: str
    domain: str = "Unknown"
    segment_type: str = "Unknown"
    problem_title: str = "Unknown"
    topic: str = ""
    content_hash: str = ""
    segment_index: int = 1
    has_notion_payload: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ManifestSummary:
    """Summary metrics and review items parsed from manifest.json."""
    version: str = "unknown"
    name: str = "synapse-sync-manifest"
    last_synced_at: Optional[str] = None
    total_processed: int = 0
    success_count: int = 0
    needs_review_count: int = 0
    skipped_unclassified_count: int = 0
    review_items: List[ReviewItem] = field(default_factory=list)
    processed_files: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["review_items"] = [item.to_dict() for item in self.review_items]
        return data


@dataclass
class NormalizedNotionRecord:
    """Normalized metadata for a problem entry in Notion (DSA or SQL)."""
    page_id: str
    title: str
    domain: str
    topic: str
    date_solved: Optional[str] = None
    revision_date: Optional[str] = None
    is_revised: bool = False
    revision_needed: Optional[str] = None
    second_revision_needed: Optional[str] = None
    bucket: Optional[str] = None
    difficulty: Optional[str] = None
    created_time: Optional[str] = None
    last_edited_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Configuration & Client Factory
# ---------------------------------------------------------------------------

def get_config_value(key: str, default: str = "") -> str:
    """
    Retrieves a configuration value.
    Checks Streamlit secrets first if running in Streamlit,
    then falls back to environment variables.
    """
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.environ.get(key, default)


def get_read_only_notion_client(token: Optional[str] = None) -> Client:
    """
    Initializes a read-only Notion Client.
    Uses the project's established Notion API version (2025-09-03).
    """
    notion_token = token or get_config_value("NOTION_TOKEN")
    if not notion_token:
        raise ValueError("NOTION_TOKEN is required for Notion API access.")
    return Client(auth=notion_token, notion_version="2025-09-03")


# ---------------------------------------------------------------------------
# Manifest Loading
# ---------------------------------------------------------------------------

def load_manifest_state(manifest_path: str = "manifest.json") -> ManifestSummary:
    """
    Reads manifest.json and produces a normalized ManifestSummary.
    Defensively handles missing files, malformed JSON, and missing keys.
    Does NOT modify the manifest file.
    """
    if not os.path.exists(manifest_path):
        logger.warning(f"Manifest file not found at: {manifest_path}")
        return ManifestSummary()

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error reading manifest file '{manifest_path}': {e}")
        return ManifestSummary()

    version = str(data.get("version", "unknown"))
    name = str(data.get("name", "synapse-sync-manifest"))
    last_synced_at = data.get("last_synced_at")

    processed = data.get("processed", {})
    if not isinstance(processed, dict):
        processed = {}

    total_processed = len(processed)
    success_count = 0
    needs_review_count = 0
    skipped_unclassified_count = 0
    review_items: List[ReviewItem] = []

    for file_id, file_meta in processed.items():
        if not isinstance(file_meta, dict):
            continue

        status = file_meta.get("status", "")
        content_hash = file_meta.get("content_hash", "")

        if status == "success":
            success_count += 1
        elif status == "skipped_unclassified":
            skipped_unclassified_count += 1
        elif status == "needs_review":
            needs_review_count += 1
            payloads = file_meta.get("payloads", [])

            if isinstance(payloads, list) and payloads:
                for idx, payload in enumerate(payloads, start=1):
                    if not isinstance(payload, dict):
                        continue

                    payload_data = payload.get("data", {})
                    if not isinstance(payload_data, dict):
                        payload_data = {}

                    problem_title = str(payload_data.get("Problem") or "Unknown Problem")
                    domain = str(payload.get("domain") or payload_data.get("Domain") or "Unknown")
                    segment_type = str(payload.get("type") or payload_data.get("Type") or "Unknown")
                    topic = str(payload_data.get("Topic") or "")
                    reason = str(payload.get("reason") or "Flagged for manual review by guardrails")
                    has_payload = bool(payload.get("notion_payload"))

                    review_items.append(ReviewItem(
                        file_id=str(file_id),
                        status=status,
                        reason=reason,
                        domain=domain,
                        segment_type=segment_type,
                        problem_title=problem_title,
                        topic=topic,
                        content_hash=str(content_hash),
                        segment_index=payload.get("segment_index", idx),
                        has_notion_payload=has_payload
                    ))
            else:
                # needs_review without preserved payloads
                review_items.append(ReviewItem(
                    file_id=str(file_id),
                    status=status,
                    reason="Flagged for manual review (no payload details preserved in manifest)",
                    content_hash=str(content_hash),
                    segment_index=1,
                    has_notion_payload=False
                ))

    return ManifestSummary(
        version=version,
        name=name,
        last_synced_at=last_synced_at,
        total_processed=total_processed,
        success_count=success_count,
        needs_review_count=needs_review_count,
        skipped_unclassified_count=skipped_unclassified_count,
        review_items=review_items,
        processed_files=processed
    )


# ---------------------------------------------------------------------------
# Notion Property Normalization
# ---------------------------------------------------------------------------

def extract_property_value(prop: Optional[Dict[str, Any]]) -> Any:
    """Extracts a simple Python value from a raw Notion property object."""
    if not isinstance(prop, dict):
        return None

    prop_type = prop.get("type")

    if prop_type == "title":
        title_list = prop.get("title", [])
        if isinstance(title_list, list):
            return "".join(t.get("plain_text", "") for t in title_list if isinstance(t, dict)).strip()
        return ""

    if prop_type == "rich_text":
        rt_list = prop.get("rich_text", [])
        if isinstance(rt_list, list):
            return "".join(t.get("plain_text", "") for t in rt_list if isinstance(t, dict)).strip()
        return ""

    if prop_type == "date":
        date_obj = prop.get("date")
        if isinstance(date_obj, dict):
            return date_obj.get("start")
        return None

    if prop_type == "select":
        select_obj = prop.get("select")
        if isinstance(select_obj, dict):
            return select_obj.get("name")
        return None

    if prop_type == "status":
        status_obj = prop.get("status")
        if isinstance(status_obj, dict):
            return status_obj.get("name")
        return None

    if prop_type == "multi_select":
        ms_list = prop.get("multi_select", [])
        if isinstance(ms_list, list):
            names = [m.get("name", "") for m in ms_list if isinstance(m, dict)]
            return ", ".join(filter(None, names))
        return None

    return None


def normalize_notion_page(
    raw_page: Dict[str, Any],
    domain: str,
    topic: str
) -> NormalizedNotionRecord:
    """
    Converts a raw Notion page object into a clean NormalizedNotionRecord.
    Defensively searches for properties to accommodate naming variations
    between DSA and SQL databases without leaking sensitive notes or code.
    """
    page_id = str(raw_page.get("id", ""))
    created_time = raw_page.get("created_time")
    last_edited_time = raw_page.get("last_edited_time")
    properties = raw_page.get("properties", {})
    if not isinstance(properties, dict):
        properties = {}

    # 1. Title
    title = ""
    for name, prop in properties.items():
        if isinstance(prop, dict) and prop.get("type") == "title":
            title = extract_property_value(prop) or ""
            break
    if not title:
        title = "Untitled"

    # 2. Date Solved vs Revision Date
    date_solved = None
    revision_date = None
    for name, prop in properties.items():
        norm_name = name.strip().lower()
        if "revision" in norm_name and "date" in norm_name:
            revision_date = extract_property_value(prop)
        elif "date" in norm_name and not date_solved:
            date_solved = extract_property_value(prop)

    # 3. Revision Urgency
    revision_needed = None
    second_revision_needed = None
    for name, prop in properties.items():
        norm_name = name.strip().lower()
        if ("2nd" in norm_name or "second" in norm_name) and "revision" in norm_name:
            second_revision_needed = extract_property_value(prop)
        elif "revision" in norm_name and ("needed" in norm_name or "level" in norm_name):
            revision_needed = extract_property_value(prop)

    is_revised = bool(revision_date or second_revision_needed)

    # 4. Bucket / Pattern
    bucket = None
    for name, prop in properties.items():
        norm_name = name.strip().lower()
        if "bucket" in norm_name or "pattern" in norm_name:
            bucket = extract_property_value(prop)
            if bucket:
                break

    # 5. Difficulty (SQL only)
    difficulty = None
    for name, prop in properties.items():
        if name.strip().lower() == "difficulty":
            difficulty = extract_property_value(prop)
            break

    return NormalizedNotionRecord(
        page_id=page_id,
        title=title,
        domain=domain,
        topic=topic,
        date_solved=date_solved,
        revision_date=revision_date,
        is_revised=is_revised,
        revision_needed=revision_needed,
        second_revision_needed=second_revision_needed,
        bucket=bucket,
        difficulty=difficulty,
        created_time=created_time,
        last_edited_time=last_edited_time
    )


# ---------------------------------------------------------------------------
# Paginated Notion Reads
# ---------------------------------------------------------------------------

def query_all_records(
    client: Client,
    data_source_id: str,
    filter_dict: Optional[Dict[str, Any]] = None,
    sorts: Optional[List[Dict[str, Any]]] = None,
    page_size: int = 100
) -> List[Dict[str, Any]]:
    """
    Performs a fully-paginated query against a Notion data source.
    Iterates using `start_cursor` until `has_more` is False.
    Uses Notion API version 2025-09-03 data_sources endpoint with fallback.
    """
    results: List[Dict[str, Any]] = []
    has_more = True
    start_cursor: Optional[str] = None

    while has_more:
        body: Dict[str, Any] = {"page_size": page_size}
        if filter_dict:
            body["filter"] = filter_dict
        if sorts:
            body["sorts"] = sorts
        if start_cursor:
            body["start_cursor"] = start_cursor

        try:
            # Notion SDK data_sources query endpoint
            kwargs: Dict[str, Any] = {
                "data_source_id": data_source_id,
                "page_size": page_size
            }
            if filter_dict:
                kwargs["filter"] = filter_dict
            if sorts:
                kwargs["sorts"] = sorts
            if start_cursor:
                kwargs["start_cursor"] = start_cursor

            response = client.data_sources.query(**kwargs)
        except AttributeError:
            # Fallback for client version if data_sources endpoint not mapped
            response = client.request(
                path=f"data_sources/{data_source_id}/query",
                method="POST",
                body=body
            )

        page_results = response.get("results", [])
        if isinstance(page_results, list):
            results.extend(page_results)

        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")

    return results


# ---------------------------------------------------------------------------
# Domain-Specific Notion Data Loading
# ---------------------------------------------------------------------------

def load_dsa_data(
    client: Client,
    parent_page_id: Optional[str] = None
) -> Tuple[Dict[str, str], List[NormalizedNotionRecord]]:
    """
    Discovers all DSA topic databases under `parent_page_id`, queries all records
    with pagination, and normalizes them into NormalizedNotionRecord objects.

    Returns:
        Tuple of (topic_db_map, list_of_normalized_records)
    """
    parent_id = parent_page_id or get_config_value("NOTION_DSA_PARENT_PAGE_ID")
    if not parent_id:
        raise ValueError("NOTION_DSA_PARENT_PAGE_ID is required for DSA loading.")

    topic_db_map = discover_dsa_topics(client, parent_id)
    all_records: List[NormalizedNotionRecord] = []

    for topic_name, data_source_id in topic_db_map.items():
        try:
            raw_pages = query_all_records(client, data_source_id)
            for raw_page in raw_pages:
                record = normalize_notion_page(raw_page, domain="DSA", topic=topic_name)
                all_records.append(record)
        except Exception as e:
            logger.error(f"Failed to query DSA topic '{topic_name}' (ID: {data_source_id}): {e}")

    return topic_db_map, all_records


def load_sql_data(
    client: Client,
    sql_db_id: Optional[str] = None
) -> List[NormalizedNotionRecord]:
    """
    Resolves NOTION_SQL_DB_ID to its underlying data source, queries all
    records with pagination, and normalizes them.

    Returns:
        List of normalized SQL records.
    """
    db_id = sql_db_id or get_config_value("NOTION_SQL_DB_ID")
    if not db_id:
        raise ValueError("NOTION_SQL_DB_ID is required for SQL loading.")

    data_source_id = resolve_data_source_id(client, db_id)
    raw_pages = query_all_records(client, data_source_id)
    return [normalize_notion_page(p, domain="SQL", topic="SQL") for p in raw_pages]


# ---------------------------------------------------------------------------
# High-Level Pipeline Overview Aggregator
# ---------------------------------------------------------------------------

def get_pipeline_overview(
    manifest_path: str = "manifest.json",
    notion_client: Optional[Client] = None,
    include_notion_counts: bool = False,
    dsa_parent_page_id: Optional[str] = None,
    sql_db_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Assembles a high-level summary of SynapseSync pipeline health.
    Combines manifest execution states and optional Notion problem inventory counts.
    """
    manifest_summary = load_manifest_state(manifest_path)

    overview: Dict[str, Any] = {
        "manifest": manifest_summary.to_dict(),
        "status": "operational" if manifest_summary.needs_review_count == 0 else "attention_needed",
        "total_manifest_processed": manifest_summary.total_processed,
        "success_count": manifest_summary.success_count,
        "needs_review_count": len(manifest_summary.review_items),
        "skipped_unclassified_count": manifest_summary.skipped_unclassified_count,
        "last_synced_at": manifest_summary.last_synced_at,
        "review_items_count": len(manifest_summary.review_items)
    }

    if include_notion_counts and notion_client:
        try:
            _, dsa_records = load_dsa_data(notion_client, dsa_parent_page_id)
            sql_records = load_sql_data(notion_client, sql_db_id)
            overview["notion_inventory"] = {
                "dsa_total": len(dsa_records),
                "sql_total": len(sql_records),
                "total_problems": len(dsa_records) + len(sql_records)
            }
        except Exception as e:
            logger.warning(f"Could not fetch live Notion counts for overview: {e}")
            overview["notion_inventory"] = None

    return overview
