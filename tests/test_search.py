import pytest
from unittest.mock import patch, MagicMock
from src.notion_tools.search import search_problem

# Dummy schema just to satisfy get_title_property_name
dummy_schema = {
    "Problem": {"type": "title"}
}

def create_mock_candidate(page_id: str, title: str) -> dict:
    return {
        "id": page_id,
        "properties": {
            "Problem": {
                "title": [{"text": {"content": title}}]
            }
        }
    }

@patch("src.notion_tools.search._query_db")
def test_search_sql_parts_assembly(mock_query):
    # Case 1: "Parts Assembly \u2014 Unfinished Parts" vs stored "Unfinished Parts"
    client = MagicMock()
    mock_query.return_value = [
        create_mock_candidate("page_sql", "Unfinished Parts")
    ]
    
    result = search_problem(client, "db_id", "Parts Assembly \u2014 Unfinished Parts", dummy_schema)
    assert result == "page_sql", "Should match because 'unfinished parts' is in 'parts assembly unfinished parts'"
    
    # Verify the fallback words used in the query
    args, kwargs = mock_query.call_args
    filter_dict = kwargs.get("filter") or args[2]
    # The words > 3 chars are 'parts', 'assembly', 'unfinished', 'parts'
    or_conditions = filter_dict["or"]
    assert len(or_conditions) == 4
    assert or_conditions[0]["title"]["contains"] == "parts"

@patch("src.notion_tools.search._query_db")
def test_search_dsa_reverse_linked_list(mock_query):
    # Case 2: "Reverse Linked List (LC 206)" vs stored "206. Reverse Linked List"
    client = MagicMock()
    mock_query.return_value = [
        create_mock_candidate("page_dsa", "206. Reverse Linked List")
    ]
    
    result = search_problem(client, "db_id", "Reverse Linked List (LC 206)", dummy_schema)
    assert result == "page_dsa", "Should match because both normalize to 'reverse linked list'"

@patch("src.notion_tools.search._query_db")
def test_search_different_problems_common_word(mock_query):
    # Case 3: "Unfinished Parts" vs "Spare Parts" (share word "parts")
    client = MagicMock()
    mock_query.return_value = [
        create_mock_candidate("page_different", "Spare Parts")
    ]
    
    result = search_problem(client, "db_id", "Unfinished Parts", dummy_schema)
    assert result is None, "Should NOT match because neither normalized string contains the other"

@patch("src.notion_tools.search._query_db")
def test_search_sequel_collision(mock_query):
    # Case 4: "Reverse Linked List" vs "206. Reverse Linked List" AND "92. Reverse Linked List II"
    client = MagicMock()
    mock_query.return_value = [
        create_mock_candidate("page_92", "92. Reverse Linked List II"),
        create_mock_candidate("page_206", "206. Reverse Linked List")
    ]
    
    result = search_problem(client, "db_id", "Reverse Linked List", dummy_schema)
    assert result == "page_206", "Should match ONLY the original, not the sequel"

