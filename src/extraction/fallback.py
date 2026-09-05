"""Gemini fallback module for transcript extraction.

Steps 5 & 6:
- Calls Gemini to extract missing or ambiguous fields from raw dialogue
- Enforces the Revision Needed rule (Low/Mid/High) based on hint count
- Enforces the Revision Notes rule (must state whether user independently recalled/derived approach)
- Solved-status check: flags segments as unsolved/rejected if no working solution was reached
"""

import json
import os
import re
from typing import Any, Dict, Optional, Tuple
from dotenv import load_dotenv

from src.extraction.contracts import (
    DOMAIN_DSA,
    DOMAIN_SQL,
    KNOWN_DSA_TOPICS,
    TYPE_FIRST_SOLVE,
    TYPE_REVISION,
    normalize_dsa_topic,
    normalize_revision_level,
)

load_dotenv()


def get_gemini_client():
    """Initialize and return a Gemini API client."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        raise ValueError("Missing or placeholder GEMINI_API_KEY in environment.")

    # Try official google-genai first
    try:
        from google import genai
        return ("genai", genai.Client(api_key=api_key))
    except ImportError:
        pass

    # Fallback to google-generativeai
    try:
        import google.generativeai as gai
        gai.configure(api_key=api_key)
        return ("gai", gai.GenerativeModel("gemini-1.5-flash"))
    except ImportError:
        raise ImportError("Neither 'google-genai' nor 'google-generativeai' is installed.")


def call_gemini(prompt: str, max_retries: int = 3) -> str:
    """Send prompt to Gemini and return raw text response with retry logic for transient errors."""
    import time
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    client_type, client = get_gemini_client()
    
    last_ex = None
    for attempt in range(max_retries):
        try:
            if client_type == "genai":
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                return response.text or ""
            else:
                response = client.generate_content(prompt)
                return response.text or ""
        except Exception as ex:
            last_ex = ex
            err_str = str(ex).lower()
            if "503" in err_str or "unavailable" in err_str or "429" in err_str or "resource_exhausted" in err_str:
                sleep_time = (attempt + 1) * 3
                print(f"[WARN] Gemini API transient error ({ex}), retrying in {sleep_time}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(sleep_time)
                continue
            raise ex
    raise last_ex


def build_fallback_prompt(
    segment_text: str,
    problem_hint: str,
    existing_partial: Dict[str, Any],
    domain_hint: Optional[str] = None,
    type_hint: Optional[str] = None,
) -> str:
    """Build structured extraction prompt for Gemini adhering to all required rules."""
    partial_json = json.dumps(existing_partial, indent=2) if existing_partial else "{}"

    prompt = f"""You are an expert technical interviewer and extraction agent for a coding tracker.
Analyze the following transcript segment between a human and an AI assistant solving a coding or database problem.

Transcript Problem Hint: {problem_hint}
Domain Hint: {domain_hint or "Infer (DSA or SQL)"}
Type Hint: {type_hint or "Infer (First Solve or Revision)"}

Previously extracted partial fields (if any):
{partial_json}

----------------- TRANSCRIPT SEGMENT START -----------------
{segment_text}
------------------ TRANSCRIPT SEGMENT END ------------------

TASK:
1. SOLVED-STATUS CHECK:
   - Check whether a correct working solution was actually reached during this dialogue.
   - If the user gave up, the problem remained unsolved, or the transcript is inconclusive about whether a correct solution was reached, set "solved": false and "rejection_reason": "unsolved".
   - If the problem was solved, set "solved": true and "rejection_reason": null.

2. CLASSIFICATION:
   - "domain": "DSA" or "SQL"
   - "type": "First Solve" or "Revision" (A revision occurs when the user is revisiting/practicing an already solved problem or explicitly doing a 2nd revision).
   - "problem_name": The standardized name of the problem (e.g. "LC 404 - Sum of Left Leaves" or "LC 993 - Cousins in Binary Tree").

3. EXTRACT REQUIRED FIELDS according to the contract:

   If Domain is DSA and Type is First Solve:
   - "Topic": MUST be exactly one of the known DSA topic page names:
     ["LinkedList", "Binary Search", "Sorting", "Recursion", "Arrays", "Bit Manipulation", "Sliding Window and Two Pointer", "Greedy Algorithm", "Stack & Queue", "Heaps", "Binary Trees"].
     This is used for routing to the correct Notion database.
   - "Bucket": The curriculum category value that gets written to the Bucket property inside that topic's database (e.g. "Basic Properties & Structural Checks", "Level Order Traversal", "Two Pointers", etc. Check transcript dialogue for explicit mentions like "Basic Properties bucket" or category).
   - "Brute-Force": Summary of the brute-force or initial approach.
   - "Optimal Approach": Summary of the optimal approach with time/space complexity if mentioned.
   - "Gotcha-Point": Key edge cases, gotchas, or counterexamples learned.
   - "My Mistake": Mistakes made by the user during the solve.
   - "Revision Needed": Must follow this strict rule:
     * "Low": Solved independently or only a small/syntax error.
     * "Mid": Needed 2-3 hints from the assistant but then solved correctly.
     * "High": Still unsolved after hints or needed 5+ hints.

   If Domain is SQL and Type is First Solve:
   - "Bucket": Category (e.g. "Aggregations", "Joins", "Window Functions").
   - "Query": The final working SQL query.
   - "Difficulty": "Easy", "Medium", or "Hard".
   - "Notes": Concise notes on the query logic and techniques used.
   - "Revision Needed":
     * "Low": Solved independently or only a small/syntax error.
     * "Mid": Needed 2-3 hints but then solved correctly.
     * "High": Still unsolved after hints or needed 5+ hints.

   If Type is Revision (either domain):
   - "Notes": REVISION NOTES RULE: The note MUST explicitly state whether the user could independently recall/derive the optimal approach during the revision, not just restate the solution.
   - "2nd Revision Needed":
     * "Low": Recalled and solved independently.
     * "Mid": Needed 2-3 hints to recall or fix approach.
     * "High": Could not recall or needed 5+ hints.

You must output ONLY a valid JSON object with the following schema, and no other text or explanation:
{{
  "solved": true,
  "rejection_reason": null,
  "domain": "DSA",
  "type": "First Solve",
  "problem_name": "...",
  "fields": {{
     ... all required fields for the specific domain and type ...
  }}
}}
"""
    return prompt


def extract_with_gemini_fallback(
    segment_text: str,
    problem_hint: str,
    date_str: Optional[str],
    existing_partial: Dict[str, Any],
    domain_hint: Optional[str] = None,
    type_hint: Optional[str] = None,
) -> Tuple[bool, Optional[str], Optional[str], Dict[str, Any], str]:
    """Execute Gemini fallback extraction and solved check.

    Returns:
        (success, domain, segment_type, data_dict, rejection_reason_or_status)
    """
    prompt = build_fallback_prompt(
        segment_text=segment_text,
        problem_hint=problem_hint,
        existing_partial=existing_partial,
        domain_hint=domain_hint,
        type_hint=type_hint,
    )

    try:
        raw_response = call_gemini(prompt)
    except Exception as e:
        return (
            False,
            domain_hint,
            type_hint,
            {},
            f"Gemini API call failed: {str(e)}",
        )

    # Clean response and parse JSON
    cleaned_json_str = raw_response.strip()
    if cleaned_json_str.startswith("```"):
        cleaned_json_str = re.sub(r"^```(?:json)?\s*", "", cleaned_json_str)
        cleaned_json_str = re.sub(r"\s*```$", "", cleaned_json_str)

    try:
        parsed = json.loads(cleaned_json_str)
    except json.JSONDecodeError:
        # Try extracting JSON object substring
        m = re.search(r"\{[\s\S]*\}", cleaned_json_str)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except json.JSONDecodeError:
                return (
                    False,
                    domain_hint,
                    type_hint,
                    {},
                    "malformed block, fallback also inconclusive",
                )
        else:
            return (
                False,
                domain_hint,
                type_hint,
                {},
                "malformed block, fallback also inconclusive",
            )

    solved = parsed.get("solved", False)
    if not solved:
        reason = parsed.get("rejection_reason") or "unsolved"
        return False, None, None, {}, reason

    domain = parsed.get("domain", domain_hint or DOMAIN_DSA)
    segment_type = parsed.get("type", type_hint or TYPE_FIRST_SOLVE)
    problem_name = parsed.get("problem_name", problem_hint)
    fields = parsed.get("fields", {})

    # Merge with existing partial (giving precedence to complete field contents)
    merged_data: Dict[str, Any] = {
        "Problem": problem_name,
        "Type": segment_type,
    }

    if segment_type == TYPE_FIRST_SOLVE:
        merged_data["Date solved"] = date_str or ""
    else:
        merged_data["Revision Date"] = date_str or ""

    # Merge fields: prioritize existing well-formed text if present, otherwise use LLM fields
    for k, v in fields.items():
        if k in ("Problem", "Type", "Date solved", "Revision Date"):
            continue
        merged_data[k] = v

    # Overlay existing non-empty partial fields if they exist
    for k, v in existing_partial.items():
        if k in ("Problem", "Type", "Date solved", "Revision Date"):
            continue
        if v and isinstance(v, str) and v.strip():
            merged_data[k] = v

    # Drop obsolete fields if present
    merged_data.pop("Pattern/Bucket", None)

    # Normalize Topic and revision levels
    if "Topic" in merged_data and domain == DOMAIN_DSA:
        merged_data["Topic"] = normalize_dsa_topic(merged_data["Topic"])
    if "Revision Needed" in merged_data:
        merged_data["Revision Needed"] = normalize_revision_level(merged_data["Revision Needed"])
    if "2nd Revision Needed" in merged_data:
        merged_data["2nd Revision Needed"] = normalize_revision_level(merged_data["2nd Revision Needed"])

    return True, domain, segment_type, merged_data, "Success"
