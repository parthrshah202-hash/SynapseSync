import os
from src.classifier import is_valid_export_filename, is_genuine_export, classify_domain

def test_is_valid_export_filename_fails():
    # Case a: A filename that fails is_valid_export_filename (wrong pattern)
    assert is_valid_export_filename("Solving LeetCode 103-2026-09-05.pdf") is False
    assert is_valid_export_filename("Solving LeetCode 103.md") is False
    assert is_valid_export_filename("image.png") is False

def test_is_genuine_export_fails():
    # Case b: A filename that passes is_valid_export_filename but fails is_genuine_export
    # (no _Created: signature)
    assert is_valid_export_filename("random-doc-2026-09-05.md") is True
    
    invalid_content = (
        "# Some Random Project Doc\n"
        "\n"
        "This is just a regular markdown file that happened to be saved\n"
        "with a date suffix, like random-doc-2026-09-05.md\n"
        "\n"
        "It has no Created signature.\n"
    )
    assert is_genuine_export(invalid_content) is False

def test_classify_domain_dsa():
    # Case c: The real DSA fixture (LC 103) classifies as "DSA"
    fixture_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    dsa_path = os.path.join(fixture_dir, "Solving LeetCode 103-2026-09-05.md")
    with open(dsa_path, "r", encoding="utf-8") as f:
        dsa_content = f.read()
    
    assert classify_domain(dsa_content) == "DSA"

def test_classify_domain_sql():
    # Case d: The real SQL fixture (assembly-parts) classifies as "SQL"
    fixture_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    sql_path = os.path.join(fixture_dir, "Finding unfinished parts in assembly-2026-09-05.md")
    with open(sql_path, "r", encoding="utf-8") as f:
        sql_content = f.read()
        
    assert classify_domain(sql_content) == "SQL"

def test_classify_domain_none():
    # Case e: Content that matches NEITHER domain
    # Confirm classify_domain returns None rather than defaulting to one domain
    unknown_content = (
        "# General chat\n"
        "_Created: 2026-09-05T12:40:20.928990Z_\n"
        "Let's write a poem about the weather.\n"
    )
    assert classify_domain(unknown_content) is None

def test_classify_domain_unrelated_sql_like():
    # Case f: Real conversational export that happens to have SQL keywords
    # but no "Notion Notes" signature. It should NOT be classified as SQL.
    unrelated_sql_content = (
        "# Takuforward Plus plan reviews and analysis\n"
        "\n"
        "_Created: 2026-09-02T10:15:00.000000Z_\n"
        "\n"
        "User: Can you summarize the Takuforward Plus plan?\n"
        "Also I want to SELECT the best plan FROM the available options.\n"
    )
    assert classify_domain(unrelated_sql_content) is None
