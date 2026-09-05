from typing import Any, Dict
from notion_client import Client


def get_tracker_schema(client: Client, resolved_db_id: str) -> Dict[str, Any]:
    """
    Fetches the database schema (properties) for a given resolved database ID (data source ID).
    Returns the properties dictionary.
    """
    try:
        ds = client.data_sources.retrieve(data_source_id=resolved_db_id)
        return ds.get("properties", {})
    except AttributeError:
        # Fallback if the client version doesn't map data_sources in Python exactly
        response = client.request(path=f"data_sources/{resolved_db_id}", method="GET")
        return response.get("properties", {})
