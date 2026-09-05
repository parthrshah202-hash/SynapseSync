"""Extraction module package for SynapseSync.

Exposes the main entrypoint:
    extract_transcript(raw_markdown: str) -> list[dict]
"""

from src.extraction.contracts import (
    DOMAIN_DSA,
    DOMAIN_SQL,
    TYPE_FIRST_SOLVE,
    TYPE_REVISION,
    validate_contract,
)
from src.extraction.extractor import extract_transcript

__all__ = [
    "extract_transcript",
    "validate_contract",
    "DOMAIN_DSA",
    "DOMAIN_SQL",
    "TYPE_FIRST_SOLVE",
    "TYPE_REVISION",
]
