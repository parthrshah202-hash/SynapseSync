"""Test harness for transcript extraction module.

Runs against every fixture file (.md) in tests/fixtures/ and prints
structured results for manual inspection and verification.
Also includes synthetic tests for SQL, Revision, and unsolved edge cases.
"""

import os
import sys
from pathlib import Path

# Ensure UTF-8 stdout encoding on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extraction import extract_transcript
from src.extraction.contracts import (
    DOMAIN_DSA,
    DOMAIN_SQL,
    TYPE_FIRST_SOLVE,
    TYPE_REVISION,
    validate_contract,
)


def print_separator(char="=", length=75):
    print(char * length)


def print_segment_result(idx: int, res: dict):
    status = res.get("status", "unknown").upper()
    print(f"\n  --- [Segment #{idx}] Status: {status} ---")
    if status == "SUCCESS":
        domain = res.get("domain")
        seg_type = res.get("type")
        data = res.get("data", {})
        print(f"  Domain:       {domain}")
        print(f"  Type:         {seg_type}")
        print(f"  Problem:      {data.get('Problem')}")
        if seg_type == TYPE_REVISION:
            print(f"  Revision Date: {data.get('Revision Date')}")
        else:
            print(f"  Date solved:  {data.get('Date solved')}")
        print("  Extracted Contract Fields:")
        for k, v in data.items():
            if k in ("Problem", "Type", "Date solved", "Revision Date"):
                continue
            v_str = str(v).strip()
            # Indent multi-line fields
            if "\n" in v_str:
                indented = "\n    ".join(v_str.split("\n"))
                print(f"    - {k}:\n    {indented}")
            else:
                print(f"    - {k}: {v_str}")
    else:
        print(f"  Problem Hint: {res.get('problem_hint')}")
        print(f"  Reason:       {res.get('reason')}")


def run_fixtures(fixtures_dir: Path):
    print_separator("=")
    print("RUNNING EXTRACTION ON FIXTURES IN tests/fixtures/")
    print_separator("=")

    md_files = sorted(fixtures_dir.glob("*.md"))
    if not md_files:
        print(f"[WARN] No .md fixture files found in {fixtures_dir}")
        return

    for fixture_path in md_files:
        print(f"\n[FIXTURE] {fixture_path.name}")
        print_separator("-")
        try:
            with open(fixture_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"[ERROR] Failed to read {fixture_path.name}: {e}")
            continue

        results = extract_transcript(content)
        print(f"Total problem segments processed: {len(results)}")
        for i, res in enumerate(results, start=1):
            print_segment_result(i, res)


def run_synthetic_tests():
    print("\n")
    print_separator("=")
    print("RUNNING SYNTHETIC EDGE CASE TESTS (SQL, REVISION, UNSOLVED)")
    print_separator("=")

    # Test 0: Standardized DSA First Solve with separate Topic and Bucket
    dsa_transcript = """# Solving LC 226 - Invert Binary Tree

_Created: 2026-08-28T12:00:00.000000Z_

## Human

Solve Invert Binary Tree

## Assistant

**Invert Binary Tree (LC 226) — Notion Notes**

**Type:** First Solve
**Topic:** Binary Trees
**Bucket:** Invert / Swap
**Brute-Force:** Recursive DFS swapping left and right children at each node.
**Optimal Approach:** Recursive DFS in O(N) time and O(H) space.
**Gotcha-Point:** Must save pointer before recursing or swap after both children computed.
**My Mistake:** None, solved directly.
**Revision Needed:** Low
"""
    print("\n[TEST 0] Standardized DSA First Solve (Topic & Bucket as separate lines):")
    res_dsa = extract_transcript(dsa_transcript)
    assert len(res_dsa) == 1, f"Expected 1 result, got {len(res_dsa)}"
    assert res_dsa[0]["status"] == "success"
    assert res_dsa[0]["domain"] == DOMAIN_DSA
    assert res_dsa[0]["type"] == TYPE_FIRST_SOLVE
    assert "Topic" in res_dsa[0]["data"]
    assert "Bucket" in res_dsa[0]["data"]
    assert "Pattern/Bucket" not in res_dsa[0]["data"]
    assert res_dsa[0]["data"]["Topic"] == "Binary Trees"
    assert res_dsa[0]["data"]["Bucket"] == "Invert / Swap"
    print_segment_result(1, res_dsa[0])
    print("[PASS] Test 0: DSA First Solve with separate Topic and Bucket correctly validated.")

    # Test 1: Standardized SQL First Solve
    sql_transcript = """# Solving Department Top Three Salaries

_Created: 2026-08-30T10:00:00.000000Z_

## Human

Solve Department Top Three Salaries SQL

## Assistant

**Department Top Three Salaries — Notion Notes**

**Type:** First Solve
**Bucket:** Window Functions / DENSE_RANK
**Query:**
WITH RankedSalaries AS (
    SELECT d.name AS Department, e.name AS Employee, e.salary AS Salary,
           DENSE_RANK() OVER (PARTITION BY e.departmentId ORDER BY e.salary DESC) AS rnk
    FROM Employee e
    JOIN Department d ON e.departmentId = d.id
)
SELECT Department, Employee, Salary
FROM RankedSalaries
WHERE rnk <= 3;
**Difficulty:** Medium
**Notes:** Use DENSE_RANK over RANK because tie salaries shouldn't skip ranking numbers.
**Revision Needed:** Low
"""
    print("\n[TEST 1] Standardized SQL First Solve:")
    res_sql = extract_transcript(sql_transcript)
    assert len(res_sql) == 1, f"Expected 1 result, got {len(res_sql)}"
    assert res_sql[0]["status"] == "success"
    assert res_sql[0]["domain"] == DOMAIN_SQL
    assert res_sql[0]["type"] == TYPE_FIRST_SOLVE
    assert "Date solved" in res_sql[0]["data"]
    assert "Revision Date" not in res_sql[0]["data"]
    assert res_sql[0]["data"]["Date solved"] == "2026-08-30"
    assert res_sql[0]["data"]["Revision Needed"] == "Low"
    print_segment_result(1, res_sql[0])
    print("[PASS] Test 1: SQL First Solve correctly validated.")

    # Test 2: Standardized Revision
    revision_transcript = """# Revision of LC 206 - Reverse Linked List

_Created: 2026-09-01T15:30:00.000000Z_

## Human

Let's do revision of Reverse Linked List

## Assistant

**Reverse Linked List (LC 206) — Notion Notes**

**Type:** Revision
**Notes:** User independently recalled the 3-pointer iterative approach (prev, curr, next) and dry-ran without any hints.
**2nd Revision Needed:** low
"""
    print("\n[TEST 2] Standardized Revision (verifying 'Revision Date' vs 'Date solved'):")
    res_rev = extract_transcript(revision_transcript)
    assert len(res_rev) == 1, f"Expected 1 result, got {len(res_rev)}"
    assert res_rev[0]["status"] == "success"
    assert res_rev[0]["type"] == TYPE_REVISION
    assert "Revision Date" in res_rev[0]["data"], "Revision must have 'Revision Date'"
    assert "Date solved" not in res_rev[0]["data"], "Revision must NEVER have 'Date solved'"
    assert res_rev[0]["data"]["Revision Date"] == "2026-09-01"
    assert res_rev[0]["data"]["2nd Revision Needed"] == "Low", "Casing must normalize to 'Low'"
    print_segment_result(1, res_rev[0])
    print("[PASS] Test 2: Revision correctly extracted 'Revision Date' and excluded 'Date solved'.")

    # Test 3: Unsolved problem (Dialogue abandoned)
    unsolved_transcript = """# LC 9999 - Impossible Problem

_Created: 2026-09-02T12:00:00.000000Z_

## Human

Can we solve LC 9999?

## Assistant

Sure, how would you approach it?

## Human

I have no idea and I am giving up now. Bye.
"""
    print("\n[TEST 3] Unsolved Problem (Dialogue abandoned):")
    res_unsolved = extract_transcript(unsolved_transcript)
    assert len(res_unsolved) == 1
    assert res_unsolved[0]["status"] == "rejected"
    assert "unsolved" in res_unsolved[0]["reason"].lower()
    print_segment_result(1, res_unsolved[0])
    print("[PASS] Test 3: Unsolved dialogue correctly rejected.")

    # Test 4: Strict contract rejection if Date solved is placed in Revision
    print("\n[TEST 4] Contract enforcement check:")
    invalid_revision_data = {
        "Problem": "LC 1",
        "Type": "Revision",
        "Revision Date": "2026-09-01",
        "Date solved": "2026-09-01",  # Illegal! Must never appear in Revision
        "Notes": "Some note",
        "2nd Revision Needed": "Low",
    }
    is_valid, err = validate_contract("DSA", "Revision", invalid_revision_data)
    assert not is_valid
    assert "Date solved" in err or "unexpected" in err.lower()
    print(f"[PASS] Test 4: Contract rejected illegal 'Date solved' in Revision: {err}")


def main():
    fixtures_dir = PROJECT_ROOT / "tests" / "fixtures"
    run_fixtures(fixtures_dir)
    run_synthetic_tests()
    print_separator("=")
    print("ALL EXTRACTION TESTS AND FIXTURES PROCESSED SUCCESSFULLY!")
    print_separator("=")


if __name__ == "__main__":
    main()
