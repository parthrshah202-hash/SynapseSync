import re

def normalize_title(title: str) -> str:
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
        remainder = longer.replace(shorter, "").strip()
        
        sequel_tokens = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "part", "version"}
        remainder_words = set(remainder.split())
        
        for w in remainder_words:
            if w.isdigit() or w in sequel_tokens:
                return False
                
        return True

    return False

cases = [
    ("Parts Assembly \u2014 Unfinished Parts", "Unfinished Parts"),
    ("Reverse Linked List (LC 206)", "206. Reverse Linked List"),
    ("Unfinished Parts", "Spare Parts"),
    ("LC 404 - Sum of Left Leaves", "Sum of Left Leaves"),
    ("Zigzag Level Order Traversal", "103. Binary Tree Zigzag Level Order Traversal"),
    ("Reverse Linked List", "92. Reverse Linked List II"),
    ("Best Time to Buy and Sell Stock", "Best Time to Buy and Sell Stock III"),
    ("Word Break", "Word Break II"),
    ("Jump Game", "Jump Game V"),
    ("Alien Dictionary", "Alien Dictionary - Part 2")
]

for a, b in cases:
    print(f"'{a}' vs '{b}' -> {is_fuzzy_match(a, b)}")

