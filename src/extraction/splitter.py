"""Splitter module for transcript extraction.

Steps 2 & 3:
- Extracts the transcript's metadata timestamp from `_Created: ...Z_`
- Splits transcripts into individual problem segments (handling multiple problems in sequence)
"""

import re
from typing import List, Optional, Tuple


def extract_created_timestamp(text: str) -> Optional[str]:
    """Extract the created timestamp date (YYYY-MM-DD) from transcript metadata.

    Looks for `_Created: 2026-08-29T14:29:53.956836Z_` or similar.
    Returns the YYYY-MM-DD date string (e.g. '2026-08-29').
    """
    match = re.search(
        r"_Created:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})(?:T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z?)?_",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1)
    
    # Fallback to any date YYYY-MM-DD after Created:
    fallback_match = re.search(r"Created:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", text, re.IGNORECASE)
    if fallback_match:
        return fallback_match.group(1)
        
    return None


class ProblemSegment:
    """Represents an isolated problem segment within a transcript."""

    def __init__(
        self,
        problem_hint: str,
        text: str,
        created_date: Optional[str] = None,
        segment_index: int = 0,
    ):
        self.problem_hint = problem_hint.strip()
        self.text = text.strip()
        self.created_date = created_date
        self.segment_index = segment_index

    def __repr__(self) -> str:
        return (
            f"<ProblemSegment(index={self.segment_index}, "
            f"hint='{self.problem_hint}', date='{self.created_date}', length={len(self.text)})>"
        )


def split_transcript_into_segments(cleaned_markdown: str) -> List[ProblemSegment]:
    """Split raw cleaned transcript into individual problem segments.

    Detects boundaries such as:
    - Multiple problem prompts: `## Human\\n\\nlets solve LC ...`
    - Multiple problem headings: `# Solving LC ...`
    - Multiple Notion Notes blocks: `**<Problem> — Notion Notes**`

    Each segment inherits the transcript's created date if not individually specified.
    """
    global_date = extract_created_timestamp(cleaned_markdown)

    # Check for problem initiation prompts in dialogue:
    # e.g., "## Human\n\nlets solve LC 993", "## Human\n\nlet's solve LC 404", "## Human\n\nsolve LC 123"
    prompt_boundary_regex = re.compile(
        r"(?:^|\n)(?=##\s+Human\s*\n\s*(?:(?:lets|let's|can we|now let's|we will|please)\s+)?(?:solve|work on|practice|(?:do\s+(?:LC\s*\d+|problem)))\s+(?:LC\s*\d+|[A-Za-z0-9\s_-]+?)(?:\n|$|\.))",
        re.IGNORECASE,
    )

    # Find all split candidate positions
    matches = list(prompt_boundary_regex.finditer(cleaned_markdown))

    # Also check if there are multiple Notion Notes headers
    notion_notes_regex = re.compile(
        r"(?:^|\n)\*\*([^\n]+?)\s*[-—]\s*Notion Notes\*\*",
        re.IGNORECASE,
    )
    notion_matches = list(notion_notes_regex.finditer(cleaned_markdown))

    # Determine split indices
    split_indices: List[Tuple[int, str]] = []

    # If we have multiple prompt boundaries:
    if len(matches) > 1:
        for idx, m in enumerate(matches):
            pos = m.start()
            # If the first match isn't at the very start of file, include header text in first segment
            if idx == 0:
                pos = 0
            
            # Try to grab problem hint from the match
            matched_slice = cleaned_markdown[m.start():m.start() + 200]
            hint_match = re.search(
                r"(?:solve|do|work on|practice)\s+((?:LC\s*\d+|[A-Za-z0-9\s_-]+?))(?:\n|$|\.)",
                matched_slice,
                re.IGNORECASE,
            )
            hint = hint_match.group(1).strip() if hint_match else f"Problem {idx+1}"
            split_indices.append((pos, hint))

    # If prompt boundaries didn't find multiple problems, check multiple Notion Notes blocks
    elif len(notion_matches) > 1:
        # We have multiple Notion Notes blocks.
        # Boundary between block i and block i+1 can be placed at the first ## Human turn
        # between block i end and block i+1 start.
        last_end = 0
        for i, nm in enumerate(notion_matches):
            hint = nm.group(1).strip()
            if i == 0:
                split_indices.append((0, hint))
            else:
                # Find ## Human between last notion block and this notion block
                sub_text = cleaned_markdown[last_end:nm.start()]
                human_m = re.search(r"(?:^|\n)##\s+Human", sub_text)
                if human_m:
                    split_indices.append((last_end + human_m.start(), hint))
                else:
                    split_indices.append((last_end, hint))
            last_end = nm.end()

    # If no multiple problem boundaries detected, treat entire transcript as one segment
    if len(split_indices) <= 1:
        # Extract title from `# Solving LC 404` or `# LC 404` or first notion notes if present
        title_match = re.search(r"^#+\s+(?:Solving\s+)?([^\n]+)", cleaned_markdown, re.MULTILINE)
        if not title_match and notion_matches:
            hint = notion_matches[0].group(1).strip()
        elif title_match:
            hint = title_match.group(1).strip()
        else:
            hint = "Problem 1"

        return [
            ProblemSegment(
                problem_hint=hint,
                text=cleaned_markdown,
                created_date=global_date,
                segment_index=1,
            )
        ]

    # Otherwise build the segments from split_indices
    segments: List[ProblemSegment] = []
    for i in range(len(split_indices)):
        start_pos, hint = split_indices[i]
        end_pos = split_indices[i + 1][0] if i + 1 < len(split_indices) else len(cleaned_markdown)
        seg_text = cleaned_markdown[start_pos:end_pos].strip()
        if not seg_text:
            continue
        
        # Check if segment has its own _Created: date, else inherit global_date
        seg_date = extract_created_timestamp(seg_text) or global_date
        segments.append(
            ProblemSegment(
                problem_hint=hint,
                text=seg_text,
                created_date=seg_date,
                segment_index=len(segments) + 1,
            )
        )

    return segments
