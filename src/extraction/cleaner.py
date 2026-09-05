"""Cleaner module for stripping export noise and unrendered UI artifacts.

Step 1 of the extraction pipeline:
- Strips placeholder blocks like "This block is not supported on your current device yet."
- Strips unrendered tool-call UI artifacts and empty code block shells.
"""

import re


def strip_export_noise(raw_markdown: str) -> str:
    """Clean raw Claude Exporter markdown transcript by removing UI noise.

    Args:
        raw_markdown: The raw markdown text from Claude Exporter.

    Returns:
        Cleaned markdown text.
    """
    if not raw_markdown:
        return ""

    cleaned = raw_markdown

    # 1. Strip code-fenced unsupported block placeholders
    # e.g.:
    # ```
    # This block is not supported on your current device yet.
    # ```
    unsupported_fenced = re.compile(
        r"```[^\n]*\n\s*This block is not supported on your current device yet\.\s*\n```",
        re.IGNORECASE,
    )
    cleaned = unsupported_fenced.sub("", cleaned)

    # 2. Strip standalone unsupported block lines
    unsupported_bare = re.compile(
        r"^[ \t]*This block is not supported on your current device yet\.?[ \t]*$",
        re.MULTILINE | re.IGNORECASE,
    )
    cleaned = unsupported_bare.sub("", cleaned)

    # 3. Strip unrendered tool-call UI artifacts
    # e.g. empty fenced code blocks left behind by UI blocks: ```\n```
    empty_code_block = re.compile(r"```[a-zA-Z0-9_-]*\s*\n\s*```", re.MULTILINE)
    cleaned = empty_code_block.sub("", cleaned)

    # Strip Claude web export tool artifacts if present
    tool_use_patterns = [
        re.compile(r"<antArtifact[^>]*>[\s\S]*?</antArtifact>", re.IGNORECASE),
        re.compile(r"<antThinking>[\s\S]*?</antThinking>", re.IGNORECASE),
    ]
    for pattern in tool_use_patterns:
        cleaned = pattern.sub("", cleaned)

    # 4. Collapse excessive consecutive blank lines (3 or more newlines -> 2 newlines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()
