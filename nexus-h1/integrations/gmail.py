#!/usr/bin/env python3
"""
Nexus H1 — Gmail Integration Module
Supports: list, read, send, search, label, archive, trash
"""

import os
import base64
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# Google API libraries
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Constants
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]
TOKEN_PATH = Path("secrets/gmail_token.json")
CREDENTIALS_PATH = Path("secrets/gmail_credentials.json")


def _get_service():
    """Authenticate and return Gmail API service."""
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"Gmail credentials not found at {CREDENTIALS_PATH}. "
                    "Download credentials.json from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def list_messages(
    max_results: int = 10,
    query: str = "",
    label_ids: Optional[List[str]] = None,
) -> List[Dict]:
    """List recent emails matching query."""
    service = _get_service()
    label_ids = label_ids or ["INBOX"]
    results = (
        service.users()
        .messages()
        .list(userId="me", maxResults=max_results, q=query, labelIds=label_ids)
        .execute()
    )
    messages = results.get("messages", [])
    return [get_message(msg["id"], service=service) for msg in messages]


def get_message(msg_id: str, service=None) -> Dict:
    """Fetch full message by ID."""
    if service is None:
        service = _get_service()
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    payload = msg.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}

    return {
        "id": msg_id,
        "thread_id": msg.get("threadId"),
        "subject": headers.get("subject", "(no subject)"),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "date": headers.get("date", ""),
        "snippet": msg.get("snippet", ""),
        "labels": msg.get("labelIds", []),
        "body": _extract_body(payload),
        "unread": "UNREAD" in msg.get("labelIds", []),
    }


def _extract_body(payload: Dict) -> str:
    """Extract plain text body from message payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace") if data else ""

    if payload.get("mimeType") == "text/html":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace") if data else ""

    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace") if data else ""
        if part.get("mimeType") == "multipart/alternative":
            return _extract_body(part)
    return ""


def send_message(to: str, subject: str, body: str, cc: Optional[str] = None) -> str:
    """Send an email. Returns message ID."""
    service = _get_service()
    from email.mime.text import MIMEText

    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    if cc:
        msg["cc"] = cc

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return sent["id"]


def modify_labels(msg_id: str, add_labels: Optional[List[str]] = None, remove_labels: Optional[List[str]] = None) -> Dict:
    """Add or remove labels from a message."""
    service = _get_service()
    body = {}
    if add_labels:
        body["addLabelIds"] = add_labels
    if remove_labels:
        body["removeLabelIds"] = remove_labels
    return service.users().messages().modify(userId="me", id=msg_id, body=body).execute()


def mark_as_read(msg_id: str) -> Dict:
    """Remove UNREAD label."""
    return modify_labels(msg_id, remove_labels=["UNREAD"])


def archive(msg_id: str) -> Dict:
    """Remove INBOX label (archive)."""
    return modify_labels(msg_id, remove_labels=["INBOX"])


def trash(msg_id: str) -> Dict:
    """Move to trash."""
    service = _get_service()
    return service.users().messages().trash(userId="me", id=msg_id).execute()


def get_unread_count(query: str = "is:unread in:inbox") -> int:
    """Count unread messages."""
    service = _get_service()
    results = service.users().messages().list(userId="me", q=query).execute()
    return results.get("resultSizeEstimate", 0)


if __name__ == "__main__":
    # Quick test: print unread count
    try:
        print(f"Unread emails: {get_unread_count()}")
    except Exception as e:
        print(f"Error: {e}")
