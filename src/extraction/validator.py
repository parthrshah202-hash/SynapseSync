"""Validator module for SynapseSync extraction module.

Step 7 of the extraction pipeline:
- Validates extracted dictionary against the strict contract per domain and Type
- Ensures required keys are present
- Rejects any unexpected keys
- Enforces Date solved vs Revision Date contract rule
- Verifies Revision Needed / 2nd Revision Needed is normalized to Low/Mid/High
"""

from typing import Any, Dict, Tuple

from src.extraction.contracts import validate_contract


def validate_extracted_result(
    domain: str, segment_type: str, data: Dict[str, Any]
) -> Tuple[bool, str]:
    """Validate extracted segment dict against strict schema contract.

    Args:
        domain: "DSA" or "SQL"
        segment_type: "First Solve" or "Revision"
        data: The extracted dictionary to validate

    Returns:
        (is_valid, error_message)
    """
    return validate_contract(domain=domain, segment_type=segment_type, data=data)
