"""Parser module for standardized '<Problem> — Notion Notes' blocks.

Step 4 of the extraction pipeline:
- Identifies and parses standardized Notion Notes blocks for DSA First Solve,
  SQL First Solve, and Revision.
- Normalizes field names and casing (Revision Needed -> Low/Mid/High).
- Populates 'Date solved' (for First Solve) or 'Revision Date' (for Revision)
  from the segment timestamp.
- Detects if the block is complete or requires LLM fallback.
"""

import re
from typing import Any, Dict, Optional, Tuple

from src.extraction.contracts import (
    ALLOWED_REVISION_LEVELS,
    DOMAIN_DSA,
    DOMAIN_SQL,
    TYPE_FIRST_SOLVE,
    TYPE_REVISION,
    get_contract_keys,
    normalize_dsa_topic,
    normalize_revision_level,
    validate_contract,
)

# Canonical field mappings from raw headings/labels
FIELD_ALIASES = {
    # Type
    "type": "Type",
    # DSA & General fields
    "topic": "Topic",
    "bucket": "Bucket",
    "pattern": "Bucket",
    "curriculum bucket": "Bucket",
    "brute-force": "Brute-Force",
    "brute force": "Brute-Force",
    "brute-force / approach": "Brute-Force",
    "brute force / approach": "Brute-Force",
    "brute-force/approach": "Brute-Force",
    "approach / brute-force": "Brute-Force",
    "approach": "Brute-Force",
    "optimal approach": "Optimal Approach",
    "optimal approach / solution": "Optimal Approach",
    "optimal solution": "Optimal Approach",
    "optimal": "Optimal Approach",
    "gotcha-point": "Gotcha-Point",
    "gotcha point": "Gotcha-Point",
    "gotcha-points": "Gotcha-Point",
    "gotcha points": "Gotcha-Point",
    "gotchas": "Gotcha-Point",
    "my mistake": "My Mistake",
    "my mistakes": "My Mistake",
    "mistake": "My Mistake",
    "mistakes": "My Mistake",
    # SQL fields
    "query": "Query",
    "sql query": "Query",
    "difficulty": "Difficulty",
    # Shared / Revision fields
    "notes": "Notes",
    "note": "Notes",
    "revision notes": "Notes",
    "revision needed": "Revision Needed",
    "revision needed?": "Revision Needed",
    "2nd revision needed": "2nd Revision Needed",
    "2nd revision needed?": "2nd Revision Needed",
    "second revision needed": "2nd Revision Needed",
}


def clean_problem_title(raw_title: str) -> str:
    """Clean problem title extracted from Notion Notes header."""
    # Remove markers like ** and trailing — Notion Notes
    cleaned = re.sub(r"[\*#_]", "", raw_title).strip()
    cleaned = re.sub(r"\s*[-—]\s*Notion Notes\s*$", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def find_notion_notes_block(segment_text: str) -> Optional[Tuple[str, str]]:
    """Locate Notion Notes block and return (problem_title_from_header, block_text)."""
    # Pattern 1: **<Problem> — Notion Notes** or similar header
    header_pattern = re.compile(
        r"(?:^|\n)(?:\*\*|#+)?\s*([^\n]+?)\s*[-—]\s*Notion Notes\s*(?:\*\*)?\s*\n([\s\S]+)",
        re.IGNORECASE,
    )
    m = header_pattern.search(segment_text)
    if m:
        raw_title = m.group(1).strip()
        block_text = m.group(2).strip()
        # If there are subsequent user turns (e.g. ## Human), cut block before them
        next_human = re.search(r"\n##\s+Human", block_text)
        if next_human:
            block_text = block_text[: next_human.start()].strip()
        return clean_problem_title(raw_title), block_text

    # Pattern 2: Look for an assistant block with **Brute-Force or **Bucket:** or **Type:**
    approach_pattern = re.compile(
        r"(?:^|\n)(?:\*\*|#+)?\s*(?:Brute-Force|Bucket|Type:\s*Revision)[\s\S]+",
        re.IGNORECASE,
    )
    m2 = approach_pattern.search(segment_text)
    if m2:
        block_text = m2.group(0).strip()
        next_human = re.search(r"\n##\s+Human", block_text)
        if next_human:
            block_text = block_text[: next_human.start()].strip()
        return "", block_text

    return None


def parse_block_sections(block_text: str) -> Dict[str, str]:
    """Parse key-value or bold-header sections from a block text into a dict."""
    sections: Dict[str, str] = {}
    
    # Split lines and identify section headers like:
    # **Gotcha-Points:**
    # or **Difficulty:** Medium
    # or Type: First Solve
    # or **Pattern/Bucket**: Tree
    header_regex = re.compile(
        r"^(?:\*\*|\*|#+\s*)?([A-Za-z0-9_ /?–—-]{2,30}?)(?:\s*:\s*\*\*|\*\*\s*:\s*|\s*:\s*)\s*(.*)$"
    )

    current_canonical_key: Optional[str] = None
    current_content: list[str] = []

    for line in block_text.splitlines():
        match = header_regex.match(line.strip())
        if match:
            raw_key = match.group(1).strip().lower()
            val_rest = match.group(2).strip()
            # Strip any remaining markdown bold markers from value
            val_rest = re.sub(r"^\*+\s*", "", val_rest).strip()
            
            # Check if raw_key matches any alias
            canonical = FIELD_ALIASES.get(raw_key)
            if not canonical:
                # Try trimming punctuation
                trimmed = re.sub(r"^[–—\-\s]+|[–—\-\s]+$", "", raw_key)
                canonical = FIELD_ALIASES.get(trimmed)

            if canonical:
                # Save previous section
                if current_canonical_key:
                    sections[current_canonical_key] = "\n".join(current_content).strip()
                current_canonical_key = canonical
                current_content = [val_rest] if val_rest else []
                continue

        if current_canonical_key:
            current_content.append(line)

    if current_canonical_key:
        sections[current_canonical_key] = "\n".join(current_content).strip()

    return sections


def parse_standardized_block(
    segment_text: str,
    problem_hint: str,
    date_str: Optional[str],
) -> Tuple[bool, Optional[str], Optional[str], Dict[str, Any], str]:
    """Attempt to parse the standardized Notion Notes block.

    Returns:
        (is_complete, domain, segment_type, data_dict, status_message)
    """
    found = find_notion_notes_block(segment_text)
    if not found:
        return False, None, None, {}, "No Notion Notes block found in segment"

    title_from_header, block_text = found
    problem_name = title_from_header if title_from_header else problem_hint

    parsed_sections = parse_block_sections(block_text)
    if not parsed_sections:
        return False, None, None, {}, "Notion Notes block found but no recognized fields parsed"

    # Infer segment type
    explicit_type = parsed_sections.get("Type", "").strip()
    if explicit_type.lower() in ("revision", "2nd revision", "second revision"):
        segment_type = TYPE_REVISION
    elif "2nd Revision Needed" in parsed_sections:
        segment_type = TYPE_REVISION
    else:
        segment_type = TYPE_FIRST_SOLVE

    # Infer domain
    if "Query" in parsed_sections or "sql" in segment_text.lower()[:300]:
        domain = DOMAIN_SQL
    else:
        domain = DOMAIN_DSA

    # Assemble candidate data dictionary
    data: Dict[str, Any] = {
        "Problem": problem_name,
        "Type": segment_type,
    }

    # Date field assignment per contract
    # First solve uses "Date solved", Revision uses "Revision Date"
    date_val = date_str or ""
    if segment_type == TYPE_FIRST_SOLVE:
        data["Date solved"] = date_val
    else:
        data["Revision Date"] = date_val

    # Copy parsed sections relevant to the contract
    expected_keys = get_contract_keys(domain, segment_type)
    for k in expected_keys:
        if k in ("Problem", "Type", "Date solved", "Revision Date"):
            continue
        if k in parsed_sections and parsed_sections[k]:
            data[k] = parsed_sections[k]

    # Normalize Topic and Revision levels if present
    if "Topic" in data and domain == DOMAIN_DSA:
        data["Topic"] = normalize_dsa_topic(data["Topic"])
    if "Revision Needed" in data:
        data["Revision Needed"] = normalize_revision_level(data["Revision Needed"])
    if "2nd Revision Needed" in data:
        data["2nd Revision Needed"] = normalize_revision_level(data["2nd Revision Needed"])

    # Validate against strict contract
    is_valid, error = validate_contract(domain, segment_type, data)
    if is_valid:
        return True, domain, segment_type, data, "Parsed completely from standardized block"

    return False, domain, segment_type, data, f"Incomplete standardized block: {error}"
