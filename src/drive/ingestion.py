import os
import json
import hashlib
from typing import Dict, List, Any
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.classifier import is_valid_export_filename, is_genuine_export, classify_domain

def get_drive_service():
    """Builds and returns the Google Drive API service using OAuth credentials."""
    load_dotenv()
    
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN")
    
    missing = [
        var_name
        for var_name, val in [
            ("GOOGLE_OAUTH_CLIENT_ID", client_id),
            ("GOOGLE_OAUTH_CLIENT_SECRET", client_secret),
            ("GOOGLE_OAUTH_REFRESH_TOKEN", refresh_token),
        ]
        if not val or val.startswith("your_")
    ]
    
    if missing:
        raise ValueError(f"Missing or placeholder environment variables: {', '.join(missing)}")
        
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    
    return build("drive", "v3", credentials=creds)

def load_manifest(manifest_path: str = "manifest.json") -> Dict[str, Any]:
    """Loads the manifest.json file."""
    if not os.path.exists(manifest_path):
        return {"processed": {}}
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)

def calculate_hash(content: bytes) -> str:
    """Calculates the SHA-256 hash of the content."""
    return hashlib.sha256(content).hexdigest()

def fetch_new_transcripts() -> List[Dict[str, Any]]:
    """
    Fetches genuine transcript exports from Google Drive, skips already processed
    ones based on manifest, classifies them, and returns a list of new transcripts.
    """
    load_dotenv()
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id or folder_id.startswith("your_"):
        raise ValueError("Missing or placeholder GOOGLE_DRIVE_FOLDER_ID")

    service = get_drive_service()
    manifest = load_manifest()
    processed = manifest.get("processed", {})
    
    # query inherently restricts to direct children of folder_id (no subfolder traversal)
    query = f"'{folder_id}' in parents and trashed = false"
    
    items = []
    page_token = None
    
    while True:
        results = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType)",
                pageSize=1000,
                pageToken=page_token
            )
            .execute()
        )
        items.extend(results.get("files", []))
        page_token = results.get("nextPageToken")
        if not page_token:
            break
            
    new_transcripts = []
    
    for item in items:
        file_id = item["id"]
        filename = item["name"]
        
        # Pre-filtering based on filename pattern
        if not is_valid_export_filename(filename):
            continue
            
        # Download content
        try:
            content_bytes = service.files().get_media(fileId=file_id).execute()
        except HttpError as e:
            print(f"Failed to download file {file_id}: {e}")
            continue
            
        content_hash = calculate_hash(content_bytes)
        
        # Check manifest
        if file_id in processed and processed[file_id].get("content_hash") == content_hash:
            continue
            
        # Decode content as string
        try:
            content_str = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            continue
            
        # Content verification signature
        if not is_genuine_export(content_str):
            continue
            
        domain = classify_domain(content_str)
        if domain:
            new_transcripts.append({
                "file_id": file_id,
                "filename": filename,
                "content": content_str,
                "content_hash": content_hash,
                "domain": domain
            })
            
    return new_transcripts
