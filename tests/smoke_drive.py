"""Smoke test for Google Drive API connectivity via service account credentials.

Loads service account credentials from environment variables, builds the Drive v3
service, and lists files inside GOOGLE_DRIVE_FOLDER_ID.
"""

import os
import sys
import json
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def main():
    load_dotenv()

    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    missing = [
        var_name
        for var_name, val in [
            ("GOOGLE_DRIVE_FOLDER_ID", folder_id),
            ("GOOGLE_SERVICE_ACCOUNT_JSON", service_account_json),
        ]
        if not val or val.startswith("your_")
    ]

    if missing:
        print(f"[ERROR] Missing or placeholder environment variables: {', '.join(missing)}")
        print("Please configure them in your .env file before running this script.")
        sys.exit(1)

    print("[INFO] Authenticating with Google Drive API...")
    try:
        try:
            service_account_info = json.loads(service_account_json)
        except json.JSONDecodeError as e:
            print(f"[ERROR] GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON: {e}")
            sys.exit(1)

        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )

        service = build("drive", "v3", credentials=creds)

        query = f"'{folder_id}' in parents and trashed = false"
        print(f"[INFO] Querying files in folder ID: {folder_id}...")

        results = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                pageSize=50,
            )
            .execute()
        )
        items = results.get("files", [])

        print(f"\n[SUCCESS] Connected to Google Drive! Found {len(items)} file(s) in folder:")
        print("-" * 60)
        if not items:
            print("  (Folder is empty)")
        else:
            for item in items:
                print(f"  • {item['name']} (ID: {item['id']}, Type: {item['mimeType']})")
        print("-" * 60)

    except HttpError as err:
        print(f"[ERROR] Google Drive API request failed: {err}")
        sys.exit(1)
    except Exception as ex:
        print(f"[ERROR] An unexpected error occurred: {ex}")
        sys.exit(1)


if __name__ == "__main__":
    main()