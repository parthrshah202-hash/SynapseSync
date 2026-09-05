import re
from typing import Any, Dict, Optional
from notion_client import Client


def get_title_property_name(schema: Dict[str, Any]) -> str:
    for name, prop in schema.items():
        if prop["type"] == "title":
            return name
    return "Problem"


def _query_db(client: Client, resolved_db_id: str, filter_dict: Dict[str, Any], page_size: int = 1) -> list:
    try:
        response = client.data_sources.query(
            data_source_id=resolved_db_id,
            filter=filter_dict,
            page_size=page_size
        )
    except AttributeError:
        response = client.request(
            path=f"data_sources/{resolved_db_id}/query",
            method="POST",
            body={
                "filter": filter_dict,
                "page_size": page_size
            }
        )
    return response.get("results", [])


def search_problem(client: Client, resolved_db_id: str, problem_name: str, schema: Dict[str, Any]) -> Optional[str]:
    """
    Searches the database (data source) for a given problem name.
    Handles exact match, cleaned titles, and prefix-numbered titles (e.g. '206. Reverse Linked List').
    Returns the page_id if found, else None.
    """
    title_prop = get_title_property_name(schema)
    
    # 1. Direct exact equals search
    results = _query_db(client, resolved_db_id, {
        "property": title_prop,
        "title": {"equals": problem_name}
    }, page_size=1)
    if results:
        return results[0]["id"]
        
    # 2. Extract clean title and LC number
    clean_title = re.sub(r"\(?\s*LC\s*\d+\s*\)?", "", problem_name, flags=re.IGNORECASE).strip(" -—#")
    num_match = re.search(r"(?:LC\s*|#\s*)?(\d+)", problem_name)
    num_str = num_match.group(1) if num_match else None
    
    if clean_title and clean_title != problem_name:
        results = _query_db(client, resolved_db_id, {
            "property": title_prop,
            "title": {"equals": clean_title}
        }, page_size=1)
        if results:
            return results[0]["id"]
            
    # 3. Contains query for prefix-numbered titles (e.g. "206. Reverse Linked List")
    search_query = clean_title if clean_title else problem_name
    candidates = _query_db(client, resolved_db_id, {
        "property": title_prop,
        "title": {"contains": search_query}
    }, page_size=10)
    
    for candidate in candidates:
        title_objs = candidate.get("properties", {}).get(title_prop, {}).get("title", [])
        if not title_objs:
            continue
        c_title = title_objs[0].get("text", {}).get("content", "").strip()
        c_title_clean = re.sub(r"^\d+[\.\s\-]+", "", c_title).strip()
        
        # Match if stripped title equals search_query
        if c_title_clean.lower() == search_query.lower():
            return candidate["id"]
        # Match if number and title both align
        if num_str and re.search(r"\b" + re.escape(num_str) + r"\b", c_title):
            return candidate["id"]
            
    return None
