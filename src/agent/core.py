import os
from typing import Any, Dict, List, Tuple

from src.extraction.contracts import DOMAIN_DSA, DOMAIN_SQL, TYPE_FIRST_SOLVE, TYPE_REVISION, normalize_dsa_topic
from src.extraction.extractor import extract_transcript
from src.notion_tools import (
    append_revision,
    build_properties_payload,
    create_problem_entry,
    discover_dsa_topics,
    get_notion_client,
    get_tracker_schema,
    resolve_data_source_id,
    search_problem,
)

_dsa_db_map_cache: Dict[str, str] = {}
_sql_db_cache: Dict[str, Tuple[str, Dict[str, Any]]] = {}
_schema_cache: Dict[str, Dict[str, Any]] = {}


def process_transcript(raw_markdown: str, dry_run: bool = True) -> List[Dict[str, Any]]:
    """
    Orchestrates the Phase 1 extraction and Phase 2 Notion routing/mutations.
    
    If dry_run=True, it builds the payloads and validates routing but does not 
    execute actual mutations via the Notion API.
    """
    client = get_notion_client()
    
    # 1. Resolve SQL DB ID
    sql_db_id = os.environ.get("NOTION_SQL_DB_ID")
    if not sql_db_id:
        raise ValueError("NOTION_SQL_DB_ID environment variable is required.")
        
    if sql_db_id not in _sql_db_cache:
        resolved_id = resolve_data_source_id(client, sql_db_id)
        schema = get_tracker_schema(client, resolved_id)
        _sql_db_cache[sql_db_id] = (resolved_id, schema)
    resolved_sql_db_id, sql_schema = _sql_db_cache[sql_db_id]
    
    # 2. Discover DSA Topics
    dsa_parent_id = os.environ.get("NOTION_DSA_PARENT_PAGE_ID")
    if not dsa_parent_id:
        raise ValueError("NOTION_DSA_PARENT_PAGE_ID environment variable is required.")
    
    global _dsa_db_map_cache
    if not _dsa_db_map_cache:
        _dsa_db_map_cache = discover_dsa_topics(client, dsa_parent_id)
    dsa_db_map = _dsa_db_map_cache
    
    def get_dsa_schema(db_id: str) -> Dict[str, Any]:
        if db_id not in _schema_cache:
            _schema_cache[db_id] = get_tracker_schema(client, db_id)
        return _schema_cache[db_id]
        
    # 3. Extract Transcript
    results = extract_transcript(raw_markdown)
    
    final_results = []
    
    # 4. Route and Apply Mutations
    for result in results:
        if result.get("status") == "rejected":
            final_results.append(result)
            continue
            
        domain = result["domain"]
        entry_type = result["type"]
        data = result["data"]
        problem_name = data.get("Problem")
        
        page_id = None
        target_db = None
        schema = None
        
        if domain == DOMAIN_SQL:
            target_db = resolved_sql_db_id
            schema = sql_schema
            page_id = search_problem(client, target_db, str(problem_name), schema)
        elif domain == DOMAIN_DSA:
            topic = data.get("Topic")
            normalized_topic = normalize_dsa_topic(topic) if topic else None
            target_db = dsa_db_map.get(normalized_topic) if normalized_topic else None
            
            if target_db:
                schema = get_dsa_schema(target_db)
                page_id = search_problem(client, target_db, str(problem_name), schema)
            elif entry_type == TYPE_REVISION:
                # Revision contracts do not require a Topic; search across discovered DSA topic databases
                matched_entries = []
                for t_name, db_id in dsa_db_map.items():
                    s = get_dsa_schema(db_id)
                    p_id = search_problem(client, db_id, str(problem_name), s)
                    if p_id:
                        matched_entries.append((t_name, db_id, s, p_id))
                
                if len(matched_entries) == 1:
                    t_name, target_db, schema, page_id = matched_entries[0]
                    result["detected_topic"] = t_name
                elif len(matched_entries) > 1:
                    result["status"] = "needs_review"
                    result["reason"] = f"Ambiguous Revision routing: '{problem_name}' found in multiple topic databases: {[m[0] for m in matched_entries]}."
                    final_results.append(result)
                    continue
                else:
                    result["status"] = "needs_review"
                    result["reason"] = f"Revision for '{problem_name}' has no matching problem entry in any DSA topic database."
                    final_results.append(result)
                    continue
            else:
                # Ambiguous routing: unknown topic
                result["status"] = "needs_review"
                result["reason"] = f"Unknown DSA Topic '{topic}' (normalized: '{normalized_topic}')"
                final_results.append(result)
                continue
        
        # Build the exact properties payload for Notion
        properties = build_properties_payload(schema, data, is_revision=(entry_type == TYPE_REVISION))
        
        if entry_type == TYPE_FIRST_SOLVE:
            result["notion_payload"] = {
                "parent": {"type": "data_source_id", "data_source_id": target_db},
                "properties": properties,
            }
            if page_id:
                # Ambiguous routing: First Solve found existing entry
                result["status"] = "needs_review"
                result["reason"] = f"First Solve entry for '{problem_name}' already exists in database (page_id: {page_id})."
            else:
                if not dry_run:
                    create_problem_entry(client, target_db, data, schema)
                result["status"] = "completed"
                
        elif entry_type == TYPE_REVISION:
            if not page_id:
                # Ambiguous routing: Revision with no matching problem
                result["status"] = "needs_review"
                result["reason"] = f"Revision for '{problem_name}' has no matching problem entry in database."
                result["notion_payload"] = {
                    "properties": properties,
                }
            else:
                result["notion_payload"] = {
                    "page_id": page_id,
                    "properties": properties,
                }
                if not dry_run:
                    append_revision(client, page_id, data, schema)
                result["status"] = "completed"
                
        final_results.append(result)
        
    return final_results
