"""Smoke test for Google Drive API connectivity via OAuth credentials.

Loads OAuth credentials from environment variables, builds the Drive v3 service,
and lists files inside GOOGLE_DRIVE_FOLDER_ID.
"""

import os
import sys
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def main():
    load_dotenv()

    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN")

    missing = [
        var_name
        for var_name, val in [
            ("GOOGLE_DRIVE_FOLDER_ID", folder_id),
            ("GOOGLE_OAUTH_CLIENT_ID", client_id),
            ("GOOGLE_OAUTH_CLIENT_SECRET", client_secret),
            ("GOOGLE_OAUTH_REFRESH_TOKEN", refresh_token),
        ]
        if not val or val.startswith("your_")
    ]

    if missing:
        print(f"[ERROR] Missing or placeholder environment variables: {', '.join(missing)}")
        print("Please configure them in your .env file before running this script.")
        sys.exit(1)

    print("[INFO] Authenticating with Google Drive API...")
    try:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
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
