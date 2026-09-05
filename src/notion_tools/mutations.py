from typing import Any, Dict
from notion_client import Client


def map_contract_key_to_schema_prop(schema: Dict[str, Any], contract_key: str) -> str:
    """Maps standard contract keys to actual database property names."""
    if contract_key == "Problem":
        for name, prop in schema.items():
            if prop["type"] == "title":
                return name
                
    elif contract_key == "Bucket":
        if "Bucket" in schema: return "Bucket"
        if "Pattern / Bucket" in schema: return "Pattern / Bucket"
        # Dynamically find the bucket/pattern property in live schema
        for name, prop in schema.items():
            name_lower = name.lower()
            if ("bucket" in name_lower or "pattern" in name_lower) and prop["type"] in ("select", "multi_select"):
                return name
        
    elif contract_key == "2nd Revision Needed":
        if "2nd Revision Needed" in schema: return "2nd Revision Needed"
        # Dynamically find the 2nd revision property in live schema
        for name in schema.keys():
            name_lower = name.lower().replace(" ", "").replace("?", "")
            if "2ndrevision" in name_lower or ("2nd" in name_lower and "revision" in name_lower):
                return name
                
    elif contract_key in schema:
        return contract_key
        
    for name in schema.keys():
        if name.lower() == contract_key.lower():
            return name
            
    return contract_key


def validate_strict_field(schema: Dict[str, Any], prop_name: str, value: str):
    """Ensure value exists in the schema options for the given property."""
    if prop_name not in schema:
        return
        
    prop_type = schema[prop_name]["type"]
    options = []
    if prop_type == "select":
        options = [opt["name"] for opt in schema[prop_name]["select"]["options"]]
    elif prop_type == "status":
        options = [opt["name"] for opt in schema[prop_name]["status"]["options"]]
    elif prop_type == "multi_select":
        options = [opt["name"] for opt in schema[prop_name]["multi_select"]["options"]]
        
    if value and options and value not in options:
        raise ValueError(
            f"Strict validation failed: Value '{value}' not found in schema options "
            f"for '{prop_name}'. Available: {options}"
        )


REVISION_ALLOWED_PROPERTIES = {"Revision Date", "2nd Revision Needed", "Notes"}


def build_properties_payload(
    schema: Dict[str, Any],
    contract_data: Dict[str, Any],
    is_revision: bool = False
) -> Dict[str, Any]:
    properties = {}
    
    strict_contract_keys = {"Difficulty", "Revision Needed", "2nd Revision Needed"}
    
    # Revisions target an existing page by page_id and must NEVER overwrite Problem Name/Title
    # or any other first-solve property. Only the 3 revision properties are allowed.
    if is_revision or contract_data.get("Type") == "Revision":
        data = {k: v for k, v in contract_data.items() if k in REVISION_ALLOWED_PROPERTIES}
    else:
        data = dict(contract_data)
        data.pop("Topic", None)
        data.pop("Type", None)
    
    for key, value in data.items():
        if value is None or value == "":
            continue
            
        mapped_key = map_contract_key_to_schema_prop(schema, key)
        
        if mapped_key not in schema:
            raise ValueError(f"Property '{key}' (mapped to '{mapped_key}') from contract not found in database schema.")
            
        if key in strict_contract_keys:
            validate_strict_field(schema, mapped_key, str(value))
            
        prop_type = schema[mapped_key]["type"]
        
        if prop_type == "title":
            properties[mapped_key] = {"title": [{"text": {"content": str(value)}}]}
        elif prop_type == "rich_text":
            content = str(value)
            rich_texts = []
            for i in range(0, len(content), 2000):
                rich_texts.append({"text": {"content": content[i:i+2000]}})
            properties[mapped_key] = {"rich_text": rich_texts}
        elif prop_type == "date":
            properties[mapped_key] = {"date": {"start": str(value)}}
        elif prop_type == "select":
            properties[mapped_key] = {"select": {"name": str(value)}}
        elif prop_type == "status":
            properties[mapped_key] = {"status": {"name": str(value)}}
        elif prop_type == "multi_select":
            properties[mapped_key] = {"multi_select": [{"name": str(value)}]}
        else:
            raise ValueError(f"Unsupported property type '{prop_type}' for field '{mapped_key}'.")
            
    return properties


def create_problem_entry(client: Client, resolved_db_id: str, contract_data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    properties = build_properties_payload(schema, contract_data, is_revision=False)
    return client.pages.create(
        parent={"type": "data_source_id", "data_source_id": resolved_db_id},
        properties=properties
    )


def append_revision(client: Client, page_id: str, contract_data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    properties = build_properties_payload(schema, contract_data, is_revision=True)
    return client.pages.update(
        page_id=page_id,
        properties=properties
    )
