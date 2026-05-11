#!/usr/bin/env python3
"""
Nexus H1 — Notion Integration Module
Supports: databases, pages, blocks, search
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from dotenv import load_dotenv
import requests

BASE_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _get_token() -> str:
    """Load token from env, with dotenv fallback."""
    token = os.getenv("NOTION_TOKEN")
    if not token:
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)
        token = os.getenv("NOTION_TOKEN", "")
    return token


def _request(method: str, endpoint: str, **kwargs) -> Dict:
    """Make request to Notion API."""
    token = _get_token()
    if not token:
        raise ValueError("NOTION_TOKEN not set. Add it to .env file.")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }
    
    url = f"{BASE_URL}/{endpoint}"
    response = requests.request(method, url, headers=headers, **kwargs)
    
    if response.status_code >= 400:
        raise RuntimeError(f"Notion API error {response.status_code}: {response.text}")
    
    return response.json()


def search(query: str = "", filter_type: Optional[str] = None, page_size: int = 10) -> List[Dict]:
    """Search pages and databases."""
    body = {"query": query, "page_size": page_size}
    if filter_type:
        body["filter"] = {"value": filter_type, "property": "object"}
    
    result = _request("POST", "search", json=body)
    return result.get("results", [])


def get_database(database_id: str) -> Dict:
    """Get database metadata."""
    return _request("GET", f"databases/{database_id}")


def query_database(
    database_id: str,
    filter_criteria: Optional[Dict] = None,
    sorts: Optional[List] = None,
    page_size: int = 100,
) -> List[Dict]:
    """Query database entries."""
    body = {"page_size": page_size}
    if filter_criteria:
        body["filter"] = filter_criteria
    if sorts:
        body["sorts"] = sorts
    
    result = _request("POST", f"databases/{database_id}/query", json=body)
    return result.get("results", [])


def create_page(
    parent_id: str,
    properties: Dict,
    icon: Optional[str] = None,
    content_blocks: Optional[List] = None,
) -> Dict:
    """Create a new page."""
    body = {
        "parent": {"database_id": parent_id},
        "properties": properties,
    }
    if icon:
        body["icon"] = {"emoji": icon} if len(icon) <= 2 else {"external": {"url": icon}}
    if content_blocks:
        body["children"] = content_blocks
    
    return _request("POST", "pages", json=body)


def update_page(page_id: str, properties: Dict, icon: Optional[str] = None) -> Dict:
    """Update page properties."""
    body = {"properties": properties}
    if icon:
        body["icon"] = {"emoji": icon} if len(icon) <= 2 else {"external": {"url": icon}}
    return _request("PATCH", f"pages/{page_id}", json=body)


def get_page(page_id: str) -> Dict:
    """Get page details."""
    return _request("GET", f"pages/{page_id}")


def get_page_content(page_id: str) -> List[Dict]:
    """Get page content blocks."""
    result = _request("GET", f"blocks/{page_id}/children")
    return result.get("results", [])


def append_blocks(page_id: str, blocks: List[Dict]) -> Dict:
    """Append content blocks to page."""
    return _request("PATCH", f"blocks/{page_id}/children", json={"children": blocks})


def archive_page(page_id: str) -> Dict:
    """Archive (soft-delete) a page."""
    return _request("PATCH", f"pages/{page_id}", json={"archived": True})


# Helper builders for common block types

def text_block(text: str, bold: bool = False) -> Dict:
    """Create a paragraph block."""
    annotations = {"bold": bold}
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text}, "annotations": annotations}]
        },
    }


def heading_block(text: str, level: int = 2) -> Dict:
    """Create a heading block (1-3)."""
    block_type = f"heading_{level}"
    return {
        "object": "block",
        "type": block_type,
        block_type: {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        },
    }


def todo_block(text: str, checked: bool = False) -> Dict:
    """Create a to-do block."""
    return {
        "object": "block",
        "type": "to_do",
        "to_do": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "checked": checked,
        },
    }


def bulleted_list_block(text: str) -> Dict:
    """Create a bulleted list item."""
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        },
    }


def divider_block() -> Dict:
    """Create a divider block."""
    return {"object": "block", "type": "divider", "divider": {}}


# Property builders

def title_prop(text: str) -> Dict:
    """Create title property."""
    return {"title": [{"type": "text", "text": {"content": text}}]}


def rich_text_prop(text: str) -> Dict:
    """Create rich text property."""
    return {"rich_text": [{"type": "text", "text": {"content": text}}]}


def select_prop(name: str) -> Dict:
    """Create select property."""
    return {"select": {"name": name}}


def multi_select_prop(names: List[str]) -> Dict:
    """Create multi-select property."""
    return {"multi_select": [{"name": n} for n in names]}


def date_prop(start: str, end: Optional[str] = None) -> Dict:
    """Create date property (ISO 8601 format)."""
    date = {"start": start}
    if end:
        date["end"] = end
    return {"date": date}


def checkbox_prop(checked: bool) -> Dict:
    """Create checkbox property."""
    return {"checkbox": checked}


def number_prop(value: float) -> Dict:
    """Create number property."""
    return {"number": value}


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        results = search(query)
        for r in results:
            obj_type = r.get("object")
            title = ""
            if obj_type == "database":
                title = r.get("title", [{}])[0].get("text", {}).get("content", "Untitled")
            else:
                title = r.get("properties", {}).get("title", {}).get("title", [{}])[0].get("text", {}).get("content", "Untitled")
            print(f"[{obj_type}] {title} — {r['id']}")
    else:
        print("Usage: python notion.py search [query]")
        print("\nMake sure NOTION_TOKEN is set in your .env file.")