import os
from notion_client import Client


def get_notion_client() -> Client:
    """Initializes and returns a Notion Client using NOTION_TOKEN from the environment."""
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise ValueError("NOTION_TOKEN environment variable is required.")
    return Client(auth=token, notion_version="2025-09-03")


def resolve_data_source_id(client: Client, database_id: str) -> str:
    """
    Resolves a raw database_id to its data_source_id.
    
    In Notion API version 2025-09-03 architecture, every database_id must be resolved
    to its data_source_id before reading schema, querying, or creating/updating pages.
    """
    db = client.databases.retrieve(database_id=database_id)
    return db["data_sources"][0]["id"]
