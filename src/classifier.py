import re

def is_valid_export_filename(filename: str) -> bool:
    """
    Checks if a filename matches the expected Claude Exporter format:
    <ChatTitle>-<YYYY-MM-DD>.md
    """
    return bool(re.match(r"^.*-\d{4}-\d{2}-\d{2}\.md$", filename))

def is_genuine_export(content: str) -> bool:
    """
    Verifies that the content contains the expected Claude Exporter signature
    within roughly the first 5 lines.
    Signature: _Created: YYYY-MM-DDTHH:MM:SSZ_
    """
    # Look at the first few lines (up to 5)
    lines = content.splitlines()[:5]
    for line in lines:
        if re.match(r"^_Created:\s*\d{4}-\d{2}-\d{2}T.*Z_$", line.strip()):
            return True
    return False

def classify_domain(content: str) -> str | None:
    """
    Classifies a transcript's content deterministically.
    Returns "DSA", "SQL", or None if no match.
    """
    # Strong requirement: Must contain the "Notion Notes" block
    # Matches hyphen, en-dash, or em-dash followed by Notion Notes
    if not re.search(r"(?i)[-—–]\s*Notion\s*Notes", content):
        return None

    # Check for DSA
    if re.search(r"(?m)^\d+\.\s", content) or re.search(r"(?i)LC\s*\d+", content):
        return "DSA"
    
    # Look for standalone keywords SELECT and FROM, or DataLemur
    if (re.search(r"\bSELECT\b", content, re.IGNORECASE) and 
        re.search(r"\bFROM\b", content, re.IGNORECASE)) or \
       re.search(r"(?i)DataLemur", content):
        return "SQL"
        
    return None
