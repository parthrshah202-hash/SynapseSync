import os
import sys
import json
from dotenv import load_dotenv
from notion_client import Client

sys.path.insert(0, "c:\\SynapseSync")

from src.notion_tools.discovery import discover_dsa_topics
from src.notion_tools.schema import get_tracker_schema

load_dotenv(".env")
client = Client(auth=os.environ.get("NOTION_TOKEN"), notion_version="2025-09-03")
parent_id = os.environ.get("NOTION_DSA_PARENT_PAGE_ID")

dsa_map = discover_dsa_topics(client, parent_id)
print("DSA MAP:", dsa_map)
if "Binary Trees" in dsa_map:
    schema = get_tracker_schema(client, dsa_map["Binary Trees"])
    print("PROPERTIES:")
    for name, prop in schema.items():
        print(f"  {name}: {prop['type']}")
