import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure stdout handles non-ASCII for Windows
sys.stdout.reconfigure(encoding="utf-8")

# Add the project root to the sys.path
project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.agent.core import process_transcript


def test_agent_dry_run():
    # Load env vars
    load_dotenv(os.path.join(project_root, ".env"))
    
    # Check for required tokens
    required = ["NOTION_TOKEN", "NOTION_DSA_PARENT_PAGE_ID", "NOTION_SQL_DB_ID"]
    missing = [req for req in required if not os.environ.get(req)]
    if missing:
        print(f"Skipping test: Missing required Notion env vars: {missing}")
        return

    fixtures_dir = Path(__file__).parent / "fixtures"
    fixture_files = [
        "Solving LeetCode 103-2026-09-05.md",
        "Finding unfinished parts in assembly-2026-09-05.md"
    ]
    
    for filename in fixture_files:
        fixture_path = fixtures_dir / filename
        if not fixture_path.exists():
            print(f"Fixture not found: {fixture_path}")
            continue
            
        print(f"\n=======================================================")
        print(f"--- Running Agent on {fixture_path.name} (dry_run=True) ---")
        print(f"=======================================================")
        with open(fixture_path, "r", encoding="utf-8") as f:
            raw_markdown = f.read()
            
        results = process_transcript(raw_markdown, dry_run=True)
        
        print(f"\nProcessed {len(results)} segments for {filename}.")
        for idx, res in enumerate(results):
            print(f"\n--- Segment {idx+1} Result ---")
            print(json.dumps(res, indent=2))
            
            if "notion_payload" in res:
                print(f"\n>>> LITERAL NOTION PAYLOAD (to be sent to Notion API):")
                print(json.dumps(res["notion_payload"], indent=2))

    # Synthetic Revision Test Case (LC 206 - Reverse Linked List)
    print(f"\n=======================================================")
    print(f"--- Running Agent on Synthetic Revision: LC 206 Reverse Linked List (dry_run=True) ---")
    print(f"=======================================================")
    synthetic_revision_transcript = """# Revision of LC 206 - Reverse Linked List

_Created: 2026-09-01T15:30:00.000000Z_

## Human

Let's do revision of Reverse Linked List

## Assistant

**Reverse Linked List (LC 206) — Notion Notes**

**Type:** Revision
**Notes:** User independently recalled the 3-pointer iterative approach (prev, curr, next) and dry-ran without any hints.
**2nd Revision Needed:** low
"""
    rev_results = process_transcript(synthetic_revision_transcript, dry_run=True)
    print(f"\nProcessed {len(rev_results)} segments for Synthetic Revision.")
    for idx, res in enumerate(rev_results):
        print(f"\n--- Segment {idx+1} Result ---")
        print(json.dumps(res, indent=2))
        
        if "notion_payload" in res:
            print(f"\n>>> LITERAL NOTION PAYLOAD (to be sent to Notion API):")
            print(json.dumps(res["notion_payload"], indent=2))


if __name__ == "__main__":
    test_agent_dry_run()
