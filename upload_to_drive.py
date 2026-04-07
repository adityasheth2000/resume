#!/usr/bin/env python3
"""
Uploads resume files to Google Drive folder.

Prerequisites:
- Python 3
- pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
- credentials.json obtained from Google Cloud Console (OAuth 2.0 Client IDs)
- Folder URL: https://drive.google.com/drive/folders/1ilGE9u7giVp3eQqbawP4YRDjz2yIfn1z

Usage:
- python resume/upload_to_drive.py --folder-url <folder-url> --credentials credentials.json

Notes:
- This script uploads resume.pdf and resume.txt (and resume.tex if present) to the target folder.
- It will create token.json for saved credentials on first run after user consent.
"""

import os
import argparse
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# If modifying these scopes, delete the token.json file.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

FILES_TO_UPLOAD = [
    'resume/resume.pdf',
    'resume/resume.txt',
    'resume/resume.tex',
]

def get_folder_id_from_url(url: str) -> str:
    if 'folders/' in url:
        return url.split('folders/')[1].split('?')[0]
    return url.rstrip('/').split('/')[-1]


def upload_file(service, folder_id: str, file_path: str, mime_type: str) -> None:
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [folder_id],
    }
    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
    request = service.files().create(body=file_metadata, media_body=media, fields='id,webViewLink')
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {file_path}: {int(status.progress() * 100)}%")
    print(f"Uploaded {file_path} (ID: {response.get('id')}) link: {response.get('webViewLink')}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder-url', required=True, help='Drive folder URL or ID')
    parser.add_argument('--credentials', required=True, help='Path to credentials.json (OAuth 2.0 Client ID)')
    args = parser.parse_args()

    folder_id = get_folder_id_from_url(args.folder_url)

    if not Path(args.credentials).exists():
        print('Error: credentials file not found at', args.credentials)
        return

    creds = None
    if Path('token.json').exists():
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(args.credentials, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('drive', 'v3', credentials=creds)

    # Upload supported files that exist
    mime_map = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.tex': 'application/x-tex'
    }

    for f in FILES_TO_UPLOAD:
        if Path(f).exists():
            ext = Path(f).suffix.lower()
            mime = mime_map.get(ext, 'application/octet-stream')
            upload_file(service, folder_id, f, mime)
        else:
            print('Skipping missing file:', f)


if __name__ == '__main__':
    main()
