from typing import Dict
from notion_client import Client
from src.extraction.contracts import normalize_dsa_topic
from src.notion_tools.helpers import resolve_data_source_id


def discover_dsa_topics(client: Client, parent_page_id: str) -> Dict[str, str]:
    """
    Dynamically discover all DSA topic databases under the given parent page.
    Handles both direct child_databases and databases nested inside child_pages.
    Returns a mapping of normalized Topic -> resolved Data Source ID.
    """
    topic_db_map = {}
    
    has_more = True
    start_cursor = None
    
    while has_more:
        kwargs = {"block_id": parent_page_id}
        if start_cursor:
            kwargs["start_cursor"] = start_cursor
            
        response = client.blocks.children.list(**kwargs)
        
        for block in response.get("results", []):
            if block["type"] == "child_database":
                db_id = block["id"]
                raw_title = block["child_database"]["title"]
                normalized_topic = normalize_dsa_topic(raw_title)
                resolved_id = resolve_data_source_id(client, db_id)
                topic_db_map[normalized_topic] = resolved_id
                
            elif block["type"] == "child_page":
                page_id = block["id"]
                raw_title = block["child_page"]["title"]
                normalized_topic = normalize_dsa_topic(raw_title)
                
                # Fetch children of the page to find the database
                try:
                    page_res = client.blocks.children.list(block_id=page_id)
                    for child in page_res.get("results", []):
                        if child["type"] == "child_database":
                            db_id = child["id"]
                            resolved_id = resolve_data_source_id(client, db_id)
                            topic_db_map[normalized_topic] = resolved_id
                            break
                except Exception:
                    pass
                
        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")
        
    return topic_db_map
