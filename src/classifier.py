
import re
from datetime import datetime


def is_valid_export_filename(filename: str) -> bool:
    """
    Checks whether a filename follows the expected Markdown export format.

    Supported examples:
        Minimum multiplications to reach end-2026-11-06.md
        Minimum multiplications to reach end-2026-11-06(1).md
        Minimum multiplications to reach end-2026-11-06 (2).md
        Minimum_multiplications-2026-11-06.md

    The date must be valid and appear before the optional duplicate suffix.
    """

    pattern = (
        r"^.+[-_]"
        r"(\d{4}-\d{2}-\d{2})"
        r"(?:\s*\(\d+\))?"
        r"\.md$"
    )

    match = re.match(pattern, filename.strip(), re.IGNORECASE)

    if not match:
        return False

    # Reject invalid dates such as 2026-15-40.
    try:
        datetime.strptime(match.group(1), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_genuine_export(content: str) -> bool:
    """
    Verifies that the content contains a valid Created metadata field.

    Supported examples:
        _Created: 2026-11-06T15:20:00Z_
        _Created: 2026-11-06 15:20 UTC_
        _Created: 2026-11-06T15:20:00+00:00_
        Created: 2026-11-06 15:20
        _Created: 2026-11-06T15:20:00.123Z_

    Looks within the first 10 lines to tolerate minor export-format changes.
    """

    lines = content.lstrip("\ufeff").splitlines()[:10]

    for line in lines:
        line = line.strip()

        # Match Created metadata, allowing optional Markdown underscores.
        match = re.match(
            r"^_?\s*Created\s*:\s*(.*?)\s*_?$",
            line,
            re.IGNORECASE
        )

        if not match:
            continue

        timestamp = match.group(1).strip()

        # Normalize common UTC suffixes for fromisoformat().
        timestamp = re.sub(
            r"\s+(UTC|GMT)$",
            "+00:00",
            timestamp,
            flags=re.IGNORECASE
        )

        # Python's fromisoformat does not accept Z in older versions.
        if timestamp.endswith("Z"):
            timestamp = timestamp[:-1] + "+00:00"

        try:
            datetime.fromisoformat(timestamp)
            return True
        except ValueError:
            continue

    return False


def classify_domain(content: str) -> str | None:
    """
    Classifies a transcript's content deterministically.

    Returns:
        "DSA", "SQL", or None if no match.
    """

    # Require a Notion Notes block.
    # Supports hyphen, en dash, em dash, and flexible whitespace.
    if not re.search(
        r"[-—–]\s*Notion\s*Notes",
        content,
        re.IGNORECASE
    ):
        return None

    # Check for DSA.
    if (
        re.search(r"(?m)^\s*\d+\.\s", content)
        or re.search(r"\bLC\s*\d+\b", content, re.IGNORECASE)
    ):
        return "DSA"

    # Check for SQL.
    has_select = re.search(r"\bSELECT\b", content, re.IGNORECASE)
    has_from = re.search(r"\bFROM\b", content, re.IGNORECASE)
    has_datalemur = re.search(r"\bDataLemur\b", content, re.IGNORECASE)

    if (has_select and has_from) or has_datalemur:
        return "SQL"

    return None
