import json
import os
import pytest
from unittest.mock import patch

from src.orchestrate import run_orchestration, load_manifest

def create_synthetic_transcript(problem: str, block_text: str, domain_flag: str) -> dict:
    content = f"""# Testing {problem}

_Created: 2026-09-01T15:30:00.000000Z_

## Human
Let's solve {problem}

## Assistant
{block_text}
"""
    return {
        "file_id": f"file_{problem.replace(' ', '_')}",
        "filename": f"{problem}-2026-09-01.md",
        "content": content,
        "content_hash": f"hash_{problem.replace(' ', '_')}",
        "domain": domain_flag
    }

@pytest.fixture
def mocks():
    with patch("src.orchestrate.fetch_new_transcripts") as mock_fetch, \
         patch("src.agent.core.discover_dsa_topics") as mock_discover, \
         patch("src.agent.core.get_tracker_schema") as mock_schema, \
         patch("src.agent.core.search_problem") as mock_search, \
         patch("src.agent.core.create_problem_entry") as mock_create, \
         patch("src.agent.core.append_revision") as mock_append, \
         patch("src.agent.core.resolve_data_source_id") as mock_resolve, \
         patch("src.extraction.extractor.extract_with_gemini_fallback") as mock_fallback:
        
        mock_resolve.return_value = "db_sql"
        mock_discover.return_value = {"Arrays": "db_arrays"}
        
        mock_schema.return_value = {
            "Problem": {"type": "title"},
            "Type": {"type": "select", "select": {"options": [{"name": "First Solve"}, {"name": "Revision"}]}},
            "Topic": {"type": "select", "select": {"options": [{"name": "Arrays"}]}},
            "Bucket": {"type": "select", "select": {"options": [{"name": "Arrays & Hashing"}, {"name": "SQL Basics"}]}},
            "Brute-Force": {"type": "rich_text"},
            "Optimal Approach": {"type": "rich_text"},
            "Gotcha-Point": {"type": "rich_text"},
            "My Mistake": {"type": "rich_text"},
            "Revision Needed": {"type": "select", "select": {"options": [{"name": "Low"}, {"name": "Mid"}, {"name": "High"}]}},
            "Date solved": {"type": "date"},
            "Query": {"type": "rich_text"},
            "Difficulty": {"type": "select", "select": {"options": [{"name": "Easy"}, {"name": "Medium"}, {"name": "Hard"}]}},
            "Notes": {"type": "rich_text"},
            "Revision Date": {"type": "date"},
            "2nd Revision Needed": {"type": "select", "select": {"options": [{"name": "Low"}, {"name": "Mid"}, {"name": "High"}]}}
        }
        
        mock_search.return_value = None
        mock_fallback.return_value = (False, None, None, {}, "unsolved")
        
        os.environ["NOTION_SQL_DB_ID"] = "db_sql"
        os.environ["NOTION_DSA_PARENT_PAGE_ID"] = "page_dsa_parent"
        
        yield {
            "fetch": mock_fetch,
            "search": mock_search,
            "create": mock_create,
            "append": mock_append,
        }

def test_case_a_new_dsa_problem_create(mocks, tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    block = """**Two Sum — Notion Notes**
**Type:** First Solve
**Topic:** Arrays
**Bucket:** Arrays & Hashing
**Brute-Force:** O(n^2) nested loop
**Optimal Approach:** O(n) hash map
**Gotcha-Point:** None
**My Mistake:** None
**Revision Needed:** Low
"""
    transcript = create_synthetic_transcript("Two Sum", block, "DSA")
    mocks["fetch"].return_value = [transcript]
    
    run_orchestration(dry_run=False, manifest_path=manifest_path)
    
    manifest = load_manifest(manifest_path)["processed"]
    assert manifest[transcript["file_id"]]["status"] == "success"
    
    assert mocks["create"].call_count == 1
    assert mocks["append"].call_count == 0

def test_case_b_dsa_revision_append(mocks, tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    block = """**Two Sum Rev — Notion Notes**
**Type:** Revision
**Notes:** Remembered the hash map approach immediately.
**2nd Revision Needed:** Low
"""
    transcript = create_synthetic_transcript("Two Sum Rev", block, "DSA")
    mocks["fetch"].return_value = [transcript]
    
    # Needs to find an existing problem to append to
    mocks["search"].return_value = "page_two_sum"
    
    run_orchestration(dry_run=False, manifest_path=manifest_path)
    
    manifest = load_manifest(manifest_path)["processed"]
    assert manifest[transcript["file_id"]]["status"] == "success"
    
    assert mocks["create"].call_count == 0
    assert mocks["append"].call_count == 1

def test_case_c_new_sql_problem_create(mocks, tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    block = """**Active Users — Notion Notes**
**Type:** First Solve
**Bucket:** SQL Basics
**Query:** SELECT * FROM users;
**Difficulty:** Medium
**Notes:** Simple query
**Revision Needed:** Low
"""
    transcript = create_synthetic_transcript("Active Users", block, "SQL")
    mocks["fetch"].return_value = [transcript]
    
    run_orchestration(dry_run=False, manifest_path=manifest_path)
    
    manifest = load_manifest(manifest_path)["processed"]
    assert manifest[transcript["file_id"]]["status"] == "success"
    
    assert mocks["create"].call_count == 1
    assert mocks["append"].call_count == 0

def test_case_d_sql_revision_append(mocks, tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    block = """**Active Users Rev — Notion Notes**
**Type:** Revision
**Notes:** Simple window function
**2nd Revision Needed:** Low
"""
    transcript = create_synthetic_transcript("Active Users Rev", block, "SQL")
    mocks["fetch"].return_value = [transcript]
    
    # Needs to find an existing problem
    mocks["search"].return_value = "page_active_users"
    
    run_orchestration(dry_run=False, manifest_path=manifest_path)
    
    manifest = load_manifest(manifest_path)["processed"]
    assert manifest[transcript["file_id"]]["status"] == "success"
    
    assert mocks["create"].call_count == 0
    assert mocks["append"].call_count == 1

def test_case_e_unsolved_transcript_success_no_write(mocks, tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    block = """**Hard Problem — Notion Notes**
**Type:** First Solve
**Topic:** Arrays
**Bucket:** Arrays & Hashing
"""
    transcript = create_synthetic_transcript("Hard Problem", block, "DSA")
    mocks["fetch"].return_value = [transcript]
    
    run_orchestration(dry_run=False, manifest_path=manifest_path)
    
    manifest = load_manifest(manifest_path)["processed"]
    # Rejection because of incomplete data goes to LLM fallback (mocked to reject as well),
    # meaning it's legitimately unsolved. This results in "success" file status.
    assert manifest[transcript["file_id"]]["status"] == "success"
    
    assert mocks["create"].call_count == 0
    assert mocks["append"].call_count == 0

def test_case_f_duplicate_processed_twice_skipped(mocks, tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    block = """**Two Sum — Notion Notes**
**Type:** First Solve
**Topic:** Arrays
**Bucket:** Arrays & Hashing
**Brute-Force:** O(n^2) nested loop
**Optimal Approach:** O(n) hash map
**Gotcha-Point:** None
**My Mistake:** None
**Revision Needed:** Low
"""
    transcript = create_synthetic_transcript("Two Sum", block, "DSA")
    
    # Pre-populate manifest with the same hash
    manifest_data = {
        "processed": {
            transcript["file_id"]: {
                "status": "success",
                "content_hash": transcript["content_hash"]
            }
        }
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)
        
    mocks["fetch"].return_value = [transcript]
    
    # Run orchestration, it should skip it before ever hitting search or create
    run_orchestration(dry_run=False, manifest_path=manifest_path)
    
    assert mocks["search"].call_count == 0
    assert mocks["create"].call_count == 0

def test_case_g_same_problem_resolved_later(mocks, tmp_path):
    manifest_path = str(tmp_path / "manifest.json")
    block = """**Two Sum Later — Notion Notes**
**Type:** Revision
**Notes:** Resolved after a few months, still remember the hash map.
**2nd Revision Needed:** Low
"""
    transcript = create_synthetic_transcript("Two Sum Later", block, "DSA")
    mocks["fetch"].return_value = [transcript]
    
    # Search finds an existing page for this First Solve
    mocks["search"].return_value = "page_two_sum"
    
    run_orchestration(dry_run=False, manifest_path=manifest_path)
    
    manifest = load_manifest(manifest_path)["processed"]
    assert manifest[transcript["file_id"]]["status"] == "success"
    
    assert mocks["create"].call_count == 0
    assert mocks["append"].call_count == 1
