"""Smoke test for Notion API connectivity.

1. Uses NOTION_TOKEN to list child blocks/pages/databases under NOTION_DSA_PARENT_PAGE_ID
   and prints each topic name + database ID found.
2. Reads the schema of NOTION_SQL_DB_ID and prints property names and types.
"""

import os
import sys
from dotenv import load_dotenv
from notion_client import Client
from notion_client.errors import APIResponseError


def clean_id(raw_id: str) -> str:
    """Strip hyphens or whitespace if provided."""
    return raw_id.strip() if raw_id else ""


def extract_title(block: dict) -> str:
    """Extract a human-readable title from a child block or page object."""
    b_type = block.get("type", "")
    if b_type == "child_page":
        return block.get("child_page", {}).get("title", "Untitled Page")
    if b_type == "child_database":
        return block.get("child_database", {}).get("title", "Untitled Database")

    # If it's a page or database object directly
    if "title" in block:
        title_val = block["title"]
        if isinstance(title_val, list) and title_val:
            return title_val[0].get("plain_text", "Untitled")
        elif isinstance(title_val, str):
            return title_val
    return f"Unnamed ({b_type or block.get('object', 'unknown')})"


def main():
    load_dotenv()

    notion_token = os.getenv("NOTION_TOKEN")
    dsa_parent_page_id = clean_id(os.getenv("NOTION_DSA_PARENT_PAGE_ID", ""))
    sql_db_id = clean_id(os.getenv("NOTION_SQL_DB_ID", ""))

    missing = [
        name
        for name, val in [
            ("NOTION_TOKEN", notion_token),
            ("NOTION_DSA_PARENT_PAGE_ID", dsa_parent_page_id),
            ("NOTION_SQL_DB_ID", sql_db_id),
        ]
        if not val or val.startswith("your_")
    ]

    if missing:
        print(f"[ERROR] Missing or placeholder environment variables: {', '.join(missing)}")
        print("Please configure them in your .env file before running this script.")
        sys.exit(1)

    notion = Client(auth=notion_token)

    # -------------------------------------------------------------
    # 1. List child pages/databases under NOTION_DSA_PARENT_PAGE_ID
    # -------------------------------------------------------------
    print(f"\n[INFO] Fetching child blocks/databases under DSA Parent Page: {dsa_parent_page_id}...")
    try:
        children_res = notion.blocks.children.list(block_id=dsa_parent_page_id)
        blocks = children_res.get("results", [])

        topics_and_dbs = []
        for blk in blocks:
            blk_type = blk.get("type")
            blk_id = blk.get("id")
            title = extract_title(blk)

            if blk_type in ("child_database", "child_page"):
                topics_and_dbs.append((title, blk_id, blk_type))

        print(f"[SUCCESS] Found {len(topics_and_dbs)} child page(s)/database(s):")
        print("-" * 65)
        if not topics_and_dbs:
            print("  (No child pages or child databases found directly under this block)")
        else:
            for title, item_id, item_type in topics_and_dbs:
                print(f"  - [{item_type}] Topic/Title: {title}")
                print(f"    ID: {item_id}")
        print("-" * 65)

    except APIResponseError as e:
        print(f"[ERROR] Failed to retrieve children for page {dsa_parent_page_id}: {e}")
        sys.exit(1)

    # -------------------------------------------------------------
    # 2. Read SQL database schema (NOTION_SQL_DB_ID)
    # -------------------------------------------------------------
    # In Notion API 2025-09-03+, databases act as containers for data sources.
    # The actual properties/schema live under the data source object.
    # Any operation creating/querying pages requires data_source_id.
    print(f"\n[INFO] Inspecting SQL Database container for DB ID: {sql_db_id}...")
    try:
        db_metadata = notion.databases.retrieve(database_id=sql_db_id)
        db_title_arr = db_metadata.get("title", [])
        db_title = db_title_arr[0].get("plain_text", "Untitled DB") if db_title_arr else "Untitled DB"
        
        data_sources = db_metadata.get("data_sources", [])
        print(f"[SUCCESS] Retrieved Database Container '{db_title}' (found {len(data_sources)} data source(s))")

        properties = {}
        data_source_id = None

        if data_sources:
            data_source_id = data_sources[0].get("id")
            print(f"[INFO] Resolving primary Data Source ID: {data_source_id}...")
            
            ds_obj = notion.data_sources.retrieve(data_source_id=data_source_id)
            properties = ds_obj.get("properties", {})
        else:
            # Fallback for earlier schema formats if data_sources is absent
            properties = db_metadata.get("properties", {})

        print(f"\n[SUCCESS] Retrieved Schema from Data Source ({len(properties)} properties):")
        if data_source_id:
            print(f"  (Data Source ID for queries & page creation: {data_source_id})")
        print("-" * 65)
        if not properties:
            print("  (No properties found on this data source)")
        else:
            for prop_name, prop_data in properties.items():
                prop_type = prop_data.get("type", "unknown")
                prop_id = prop_data.get("id", "")
                print(f"  - {prop_name:<30} | Type: {prop_type:<15} (ID: {prop_id})")
        print("-" * 65)

    except APIResponseError as e:
        print(f"[ERROR] Failed to retrieve database or data source {sql_db_id}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
