#!/usr/bin/env python3
"""
Nexus H1 — Google Calendar Integration Module
Supports: list events, create, update, delete, search
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Same scopes as Gmail + calendar
SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_PATH = Path("secrets/calendar_token.json")
CREDENTIALS_PATH = Path("secrets/calendar_credentials.json")

# Default calendar ID (primary)
DEFAULT_CALENDAR = "primary"


def _get_service():
    """Authenticate and return Calendar API service."""
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                # Try reusing Gmail credentials if available
                gmail_creds = Path("secrets/gmail_credentials.json")
                if gmail_creds.exists():
                    flow = InstalledAppFlow.from_client_secrets_file(str(gmail_creds), SCOPES)
                    creds = flow.run_local_server(port=0)
                else:
                    raise FileNotFoundError(
                        f"Calendar credentials not found at {CREDENTIALS_PATH}. "
                        "Download credentials.json from Google Cloud Console."
                    )
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
                creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def list_events(
    calendar_id: str = DEFAULT_CALENDAR,
    max_results: int = 10,
    time_min: Optional[datetime] = None,
    time_max: Optional[datetime] = None,
    query: str = "",
) -> List[Dict]:
    """List events from calendar."""
    service = _get_service()
    
    now = datetime.utcnow()
    if time_min is None:
        time_min = now
    if time_max is None:
        time_max = now + timedelta(days=7)
    
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min.isoformat() + "Z",
        timeMax=time_max.isoformat() + "Z",
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
        q=query,
    ).execute()
    
    events = events_result.get("items", [])
    return [{
        "id": e["id"],
        "summary": e.get("summary", "(No title)"),
        "description": e.get("description", ""),
        "location": e.get("location", ""),
        "start": e["start"].get("dateTime", e["start"].get("date")),
        "end": e["end"].get("dateTime", e["end"].get("date")),
        "creator": e.get("creator", {}).get("email", ""),
        "attendees": [a.get("email") for a in e.get("attendees", [])],
        "status": e.get("status"),
        "link": e.get("htmlLink"),
        "all_day": "date" in e["start"],
    } for e in events]


def get_event(event_id: str, calendar_id: str = DEFAULT_CALENDAR) -> Dict:
    """Get single event details."""
    service = _get_service()
    e = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    return {
        "id": e["id"],
        "summary": e.get("summary", "(No title)"),
        "description": e.get("description", ""),
        "location": e.get("location", ""),
        "start": e["start"].get("dateTime", e["start"].get("date")),
        "end": e["end"].get("dateTime", e["end"].get("date")),
        "creator": e.get("creator", {}).get("email", ""),
        "attendees": [a.get("email") for a in e.get("attendees", [])],
        "status": e.get("status"),
        "link": e.get("htmlLink"),
        "all_day": "date" in e["start"],
    }


def create_event(
    summary: str,
    start: datetime,
    end: datetime,
    description: str = "",
    location: str = "",
    attendees: Optional[List[str]] = None,
    calendar_id: str = DEFAULT_CALENDAR,
    reminder_minutes: int = 30,
) -> Dict:
    """Create a new event."""
    service = _get_service()
    
    event = {
        "summary": summary,
        "location": location,
        "description": description,
        "start": {
            "dateTime": start.isoformat(),
            "timeZone": "America/New_York",
        },
        "end": {
            "dateTime": end.isoformat(),
            "timeZone": "America/New_York",
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": reminder_minutes},
                {"method": "popup", "minutes": 10},
            ],
        },
    }
    
    if attendees:
        event["attendees"] = [{"email": email} for email in attendees]
    
    created = service.events().insert(calendarId=calendar_id, body=event).execute()
    return {"id": created["id"], "link": created.get("htmlLink")}


def update_event(
    event_id: str,
    calendar_id: str = DEFAULT_CALENDAR,
    **kwargs,
) -> Dict:
    """Update an existing event."""
    service = _get_service()
    
    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    
    if "summary" in kwargs:
        event["summary"] = kwargs["summary"]
    if "description" in kwargs:
        event["description"] = kwargs["description"]
    if "location" in kwargs:
        event["location"] = kwargs["location"]
    if "start" in kwargs:
        event["start"] = {
            "dateTime": kwargs["start"].isoformat(),
            "timeZone": "America/New_York",
        }
    if "end" in kwargs:
        event["end"] = {
            "dateTime": kwargs["end"].isoformat(),
            "timeZone": "America/New_York",
        }
    
    updated = service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
    return {"id": updated["id"], "link": updated.get("htmlLink")}


def delete_event(event_id: str, calendar_id: str = DEFAULT_CALENDAR) -> bool:
    """Delete an event."""
    service = _get_service()
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return True
    except HttpError:
        return False


def get_upcoming_events(days: int = 7, max_results: int = 10) -> List[Dict]:
    """Get upcoming events for next N days."""
    now = datetime.utcnow()
    return list_events(
        time_min=now,
        time_max=now + timedelta(days=days),
        max_results=max_results,
    )


def get_todays_events() -> List[Dict]:
    """Get today's events."""
    now = datetime.utcnow()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    return list_events(time_min=start_of_day, time_max=end_of_day, max_results=50)


def create_quick_reminder(text: str, minutes_from_now: int = 30) -> Dict:
    """Create a quick reminder event."""
    start = datetime.utcnow() + timedelta(minutes=minutes_from_now)
    end = start + timedelta(minutes=15)
    return create_event(
        summary=f"Reminder: {text}",
        start=start,
        end=end,
        description=text,
        reminder_minutes=0,
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "today":
            events = get_todays_events()
            print(f"Today's events ({len(events)}):")
            for e in events:
                print(f"  • {e['summary']} — {e['start']}")
        elif sys.argv[1] == "upcoming":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            events = get_upcoming_events(days=days)
            print(f"Upcoming {days} days ({len(events)} events):")
            for e in events:
                print(f"  • {e['summary']} — {e['start']}")
        else:
            print("Usage: python calendar.py [today|upcoming [days]]")
    else:
        print("Usage: python calendar.py [today|upcoming [days]]")
