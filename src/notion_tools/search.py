import re
from typing import Any, Dict, Optional
from notion_client import Client


def get_title_property_name(schema: Dict[str, Any]) -> str:
    for name, prop in schema.items():
        if prop["type"] == "title":
            return name
    return "Problem"


def _query_db(client: Client, resolved_db_id: str, filter_dict: Dict[str, Any], page_size: int = 1) -> list:
    try:
        response = client.data_sources.query(
            data_source_id=resolved_db_id,
            filter=filter_dict,
            page_size=page_size
        )
    except AttributeError:
        response = client.request(
            path=f"data_sources/{resolved_db_id}/query",
            method="POST",
            body={
                "filter": filter_dict,
                "page_size": page_size
            }
        )
    return response.get("results", [])


def normalize_title(title: str) -> str:
    """
    Normalizes a problem title for fuzzy matching:
    - Lowercase
    - Strips '(LC 206)' or 'LC 404' anywhere
    - Strips leading numbers like '206.' or '206 -'
    - Replaces all punctuation/dashes with spaces
    - Collapses multiple spaces
    """
    t = title.lower()
    t = re.sub(r"\(?\s*lc\s*\d+\s*\)?", "", t)
    t = re.sub(r"^\d+[\.\-\s]+", "", t)
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def is_fuzzy_match(t1: str, t2: str) -> bool:
    n1 = normalize_title(t1)
    n2 = normalize_title(t2)
    if not n1 or not n2:
        return False
        
    if n1 == n2:
        return True
        
    if n1 in n2 or n2 in n1:
        longer, shorter = (n1, n2) if len(n1) > len(n2) else (n2, n1)
        # Extract the difference (remainder)
        remainder = longer.replace(shorter, "").strip()
        
        # Tokens that imply a sequel/variation and should block a substring match
        sequel_tokens = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "part", "version"}
        remainder_words = set(remainder.split())
        
        # If the remainder contains a digit (e.g. "2") or a roman numeral/sequel word, reject
        for w in remainder_words:
            if w.isdigit() or w in sequel_tokens:
                return False
                
        return True

    return False

def search_problem(client: Client, resolved_db_id: str, problem_name: str, schema: Dict[str, Any]) -> Optional[str]:
    """
    Searches the database (data source) for a given problem name.
    Uses fuzzy bidirectional matching to handle variations in titles
    (e.g., 'Parts Assembly - Unfinished Parts' vs 'Unfinished Parts').
    Returns the page_id if found, else None.
    """
    title_prop = get_title_property_name(schema)
    
    # 1. Fetch candidates using an OR query on significant words
    norm_name = normalize_title(problem_name)
    words = [w for w in norm_name.split() if len(w) > 3]
    if not words:
        words = norm_name.split()
        
    or_conditions = [
        {"property": title_prop, "title": {"contains": w}}
        for w in words
    ]
    
    # If there are no words to search for (e.g. only punctuation), fallback to direct query
    if not or_conditions:
        or_conditions = [{"property": title_prop, "title": {"contains": problem_name}}]
        
    # We cap at page_size=100 to catch broad matches, then filter locally
    candidates = _query_db(client, resolved_db_id, {
        "or": or_conditions
    }, page_size=100)
    
    # 2. Local fuzzy match
    for candidate in candidates:
        title_objs = candidate.get("properties", {}).get(title_prop, {}).get("title", [])
        if not title_objs:
            continue
        c_title = "".join([obj.get("text", {}).get("content", "") for obj in title_objs]).strip()
        
        if is_fuzzy_match(problem_name, c_title):
            return candidate["id"]
            
    return None
