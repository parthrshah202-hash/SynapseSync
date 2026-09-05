"""Field contracts and validation schemas for SynapseSync extraction module.

Defines exact required keys, allowed values, and schemas for:
- DSA First Solve: Topic and Bucket are separate fields
- SQL First Solve: Bucket
- Revision (DSA / SQL): Revision Date
"""

from typing import Any, Dict, Set, Tuple

# Domain and Type Constants
DOMAIN_DSA = "DSA"
DOMAIN_SQL = "SQL"
ALLOWED_DOMAINS: Set[str] = {DOMAIN_DSA, DOMAIN_SQL}

TYPE_FIRST_SOLVE = "First Solve"
TYPE_REVISION = "Revision"
ALLOWED_TYPES: Set[str] = {TYPE_FIRST_SOLVE, TYPE_REVISION}

# Allowed values for Revision Needed and 2nd Revision Needed
ALLOWED_REVISION_LEVELS: Set[str] = {"Low", "Mid", "High"}

# Known DSA Topic Page Names for routing to Notion databases
KNOWN_DSA_TOPICS: Set[str] = {
    "LinkedList",
    "Binary Search",
    "Sorting",
    "Recursion",
    "Arrays",
    "Bit Manipulation",
    "Sliding Window and Two Pointer",
    "Greedy Algorithm",
    "Stack & Queue",
    "Heaps",
    "Binary Trees",
}

# Contract Schemas (Strict required keys)
# Note: "Date solved" is strictly first-solve only.
# "Revision Date" is strictly revision only.
DSA_FIRST_SOLVE_KEYS: Set[str] = {
    "Problem",
    "Date solved",
    "Type",
    "Topic",
    "Bucket",
    "Brute-Force",
    "Optimal Approach",
    "Gotcha-Point",
    "My Mistake",
    "Revision Needed",
}

SQL_FIRST_SOLVE_KEYS: Set[str] = {
    "Problem",
    "Date solved",
    "Type",
    "Bucket",
    "Query",
    "Difficulty",
    "Notes",
    "Revision Needed",
}

REVISION_KEYS: Set[str] = {
    "Problem",
    "Revision Date",
    "Type",
    "Notes",
    "2nd Revision Needed",
}


def normalize_dsa_topic(value: Any) -> str:
    """Normalize a DSA topic name to one of the canonical KNOWN_DSA_TOPICS."""
    if not value:
        return ""
    val_clean = str(value).strip()
    
    # Exact check
    if val_clean in KNOWN_DSA_TOPICS:
        return val_clean

    val_lower = val_clean.lower().replace("_", " ").replace("-", " ")
    val_compact = val_lower.replace(" ", "")

    topic_map = {
        "linkedlist": "LinkedList",
        "linked list": "LinkedList",
        "binarysearch": "Binary Search",
        "binary search": "Binary Search",
        "sorting": "Sorting",
        "recursion": "Recursion",
        "arrays": "Arrays",
        "array": "Arrays",
        "bitmanipulation": "Bit Manipulation",
        "bit manipulation": "Bit Manipulation",
        "sliding window and two pointer": "Sliding Window and Two Pointer",
        "sliding window & two pointer": "Sliding Window and Two Pointer",
        "sliding window and two pointers": "Sliding Window and Two Pointer",
        "sliding window": "Sliding Window and Two Pointer",
        "two pointer": "Sliding Window and Two Pointer",
        "two pointers": "Sliding Window and Two Pointer",
        "greedy algorithm": "Greedy Algorithm",
        "greedy": "Greedy Algorithm",
        "stack & queue": "Stack & Queue",
        "stack and queue": "Stack & Queue",
        "stack": "Stack & Queue",
        "queue": "Stack & Queue",
        "heaps": "Heaps",
        "heap": "Heaps",
        "binary trees": "Binary Trees",
        "binary tree": "Binary Trees",
        "tree": "Binary Trees",
        "trees": "Binary Trees",
    }

    if val_lower in topic_map:
        return topic_map[val_lower]
    if val_compact in topic_map:
        return topic_map[val_compact]

    # Partial / substring match against canonical topics
    for topic in KNOWN_DSA_TOPICS:
        if topic.lower() == val_lower or topic.lower() in val_lower:
            return topic

    return val_clean


def normalize_revision_level(value: Any) -> str:
    """Normalize revision level string to Title Case (Low, Mid, High)."""
    if not value:
        return ""
    cleaned = str(value).strip().title()
    if cleaned in ALLOWED_REVISION_LEVELS:
        return cleaned
    
    # Handle possible variations (e.g. "Medium" -> "Mid")
    upper = str(value).strip().upper()
    if "LOW" in upper:
        return "Low"
    if "MID" in upper or "MED" in upper:
        return "Mid"
    if "HIGH" in upper:
        return "High"
    return cleaned


def get_contract_keys(domain: str, segment_type: str) -> Set[str]:
    """Retrieve expected contract keys for given domain and type."""
    if segment_type == TYPE_REVISION:
        return REVISION_KEYS
    if segment_type == TYPE_FIRST_SOLVE:
        if domain == DOMAIN_SQL:
            return SQL_FIRST_SOLVE_KEYS
        return DSA_FIRST_SOLVE_KEYS
    raise ValueError(f"Unknown segment type: {segment_type}")


def validate_contract(domain: str, segment_type: str, data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate extracted data dictionary against contract schema.

    Returns:
        (is_valid, error_message)
    """
    if domain not in ALLOWED_DOMAINS:
        return False, f"Invalid domain '{domain}', expected one of {ALLOWED_DOMAINS}"
    
    if segment_type not in ALLOWED_TYPES:
        return False, f"Invalid type '{segment_type}', expected one of {ALLOWED_TYPES}"

    expected_keys = get_contract_keys(domain, segment_type)
    actual_keys = set(data.keys())

    missing_keys = expected_keys - actual_keys
    if missing_keys:
        return False, f"Missing required keys: {sorted(list(missing_keys))}"

    unexpected_keys = actual_keys - expected_keys
    if unexpected_keys:
        return False, f"Unexpected keys present: {sorted(list(unexpected_keys))}"

    # Verify Type field matches segment_type
    if data.get("Type") != segment_type:
        return False, f"Field 'Type' value '{data.get('Type')}' does not match segment type '{segment_type}'"

    # Strict contract enforcement: Date solved vs Revision Date
    if segment_type == TYPE_REVISION:
        if "Date solved" in data:
            return False, "Revision contract must never include 'Date solved', use 'Revision Date'"
        rev_level = data.get("2nd Revision Needed", "")
        if rev_level not in ALLOWED_REVISION_LEVELS:
            return False, f"Invalid '2nd Revision Needed' value '{rev_level}', must be one of {ALLOWED_REVISION_LEVELS}"
    else:
        if "Revision Date" in data:
            return False, "First Solve contract must never include 'Revision Date', use 'Date solved'"
        rev_level = data.get("Revision Needed", "")
        if rev_level not in ALLOWED_REVISION_LEVELS:
            return False, f"Invalid 'Revision Needed' value '{rev_level}', must be one of {ALLOWED_REVISION_LEVELS}"

    # Verify DSA Topic is one of the known DSA topics
    if domain == DOMAIN_DSA and segment_type == TYPE_FIRST_SOLVE:
        topic_val = data.get("Topic", "")
        normalized_topic = normalize_dsa_topic(topic_val)
        if normalized_topic not in KNOWN_DSA_TOPICS:
            return (
                False,
                f"Invalid DSA Topic '{topic_val}'. Must be one of known topics: {sorted(list(KNOWN_DSA_TOPICS))}",
            )

    # Check non-empty strings for essential fields
    for k in expected_keys:
        val = data.get(k)
        if val is None or (isinstance(val, str) and not val.strip()):
            return False, f"Field '{k}' cannot be empty"

    return True, ""
