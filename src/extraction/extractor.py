"""Transcript extraction module for SynapseSync.

Orchestrates the 7-step extraction pipeline:
1. Strip export noise
2. Split transcript into problem segments
3. Extract Created metadata timestamp (Date solved or Revision Date)
4. Parse standardized '<Problem> — Notion Notes' block
5. LLM fallback via Gemini for missing/malformed blocks
6. Solved-status verification (reject inconclusive/unsolved segments)
7. Strict field contract validation
"""

from typing import Any, Dict, List

from src.extraction.cleaner import strip_export_noise
from src.extraction.contracts import (
    DOMAIN_DSA,
    DOMAIN_SQL,
    TYPE_FIRST_SOLVE,
    TYPE_REVISION,
    validate_contract,
)
from src.extraction.fallback import extract_with_gemini_fallback
from src.extraction.parser import parse_standardized_block
from src.extraction.splitter import split_transcript_into_segments


def extract_transcript(raw_markdown: str) -> List[Dict[str, Any]]:
    """Extract and validate problem entries from a Claude Exporter transcript.

    Args:
        raw_markdown: Raw markdown string of the transcript export.

    Returns:
        A list of per-segment results. Each result is either:
        - A validated structured dict:
          {"status": "success", "domain": "DSA"|"SQL", "type": "First Solve"|"Revision", "data": {...}}
        - Or a rejection dict:
          {"status": "rejected", "reason": "<reason>", ...}
    """
    if not raw_markdown or not raw_markdown.strip():
        return []

    # Step 1: Strip export noise and UI placeholders
    cleaned_markdown = strip_export_noise(raw_markdown)

    # Step 2 & 3: Split into problem segments and extract Created date
    segments = split_transcript_into_segments(cleaned_markdown)
    if not segments:
        return []

    results: List[Dict[str, Any]] = []

    for seg in segments:
        # Step 4: Try parsing standardized Notion Notes block
        is_complete, domain, seg_type, parsed_data, parse_msg = parse_standardized_block(
            segment_text=seg.text,
            problem_hint=seg.problem_hint,
            date_str=seg.created_date,
        )

        final_data: Dict[str, Any] = {}
        final_domain = domain
        final_type = seg_type

        if is_complete:
            final_data = parsed_data
        else:
            # Step 5: Fall back to Gemini for missing or incomplete blocks
            success, fb_dom, fb_type, fb_data, fb_msg = extract_with_gemini_fallback(
                segment_text=seg.text,
                problem_hint=seg.problem_hint,
                date_str=seg.created_date,
                existing_partial=parsed_data,
                domain_hint=domain,
                type_hint=seg_type,
            )

            # Step 6: Solved status check
            if not success:
                results.append({
                    "status": "rejected",
                    "reason": fb_msg or "unsolved",
                    "problem_hint": seg.problem_hint,
                    "segment_index": seg.segment_index,
                })
                continue

            final_domain = fb_dom or DOMAIN_DSA
            final_type = fb_type or TYPE_FIRST_SOLVE
            final_data = fb_data

        # Step 7: Strict field contract validation
        is_valid, val_err = validate_contract(
            domain=final_domain,
            segment_type=final_type,
            data=final_data,
        )

        if not is_valid:
            results.append({
                "status": "rejected",
                "reason": f"Contract validation failed: {val_err}",
                "problem_hint": seg.problem_hint,
                "segment_index": seg.segment_index,
            })
        else:
            results.append({
                "status": "success",
                "domain": final_domain,
                "type": final_type,
                "data": final_data,
                "segment_index": seg.segment_index,
            })

    return results
