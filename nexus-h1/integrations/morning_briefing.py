#!/usr/bin/env python3
"""
Nexus H1 — Morning Briefing Engine
Generates and sends a daily morning briefing via Telegram using AI.
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List

from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

TELEGRAM_CHAT_ID_FILE = Path("secrets/telegram_chat_id.txt")


def _get_chat_id() -> Optional[str]:
    if TELEGRAM_CHAT_ID_FILE.exists():
        return TELEGRAM_CHAT_ID_FILE.read_text().strip()
    return os.getenv("TELEGRAM_CHAT_ID")


def _send_telegram(message: str, parse_mode: str = "Markdown"):
    """Send briefing to Telegram."""
    try:
        from integrations.telegram import send_message
        chat_id = _get_chat_id()
        if chat_id:
            send_message(chat_id, message, parse_mode=parse_mode)
            print(f"[BRIEFING] Sent to {chat_id}")
        else:
            print("[BRIEFING] No chat_id configured.")
    except Exception as e:
        print(f"[BRIEFING] Failed to send Telegram: {e}")


def get_calendar_summary() -> str:
    """Get today's calendar events."""
    try:
        from integrations.google_calendar import get_todays_events
        events = get_todays_events()
        if not events:
            return "No calendar events today."
        lines = []
        for e in events:
            summary = e.get("summary", "Untitled")
            start = e.get("start", {})
            time_str = start.get("dateTime", start.get("date", ""))
            lines.append(f"- {summary} at {time_str}")
        return "\n".join(lines)
    except Exception as e:
        return f"Could not fetch calendar: {e}"


def get_email_summary() -> str:
    """Get unread email count and subjects."""
    try:
        from integrations.gmail import list_messages
        emails = list_messages(max_results=5, query="is:unread in:inbox")
        if not emails:
            return "No unread emails."
        lines = [f"{len(emails)} unread email(s):"]
        for e in emails[:3]:
            subject = e.get("subject", "(no subject)")
            sender = e.get("from", "unknown")
            lines.append(f"- {subject} (from {sender})")
        if len(emails) > 3:
            lines.append(f"... and {len(emails) - 3} more")
        return "\n".join(lines)
    except Exception as e:
        return f"Could not fetch emails: {e}"


def get_notion_tasks() -> str:
    """Get pending tasks from Notion."""
    try:
        from integrations.notion import search, query_database
        databases = search("", filter_type="database", page_size=5)
        pending_tasks = []
        for db in databases:
            db_id = db["id"]
            try:
                entries = query_database(db_id, page_size=10)
                for entry in entries:
                    props = entry.get("properties", {})
                    status = None
                    title = "Untitled"
                    for key, val in props.items():
                        if key.lower() in ["status", "estado", "state"]:
                            if "select" in val:
                                status = val["select"].get("name", "").lower()
                            elif "status" in val:
                                status = val["status"].get("name", "").lower()
                        if key.lower() in ["name", "title", "tarea", "task"]:
                            if "title" in val and val["title"]:
                                title = val["title"][0].get("text", {}).get("content", "Untitled")
                    pending_statuses = ["not started", "in progress", "pending", "to do", "todo",
                                       "por hacer", "pendiente", "doing", "en progreso", "backlog"]
                    if status and any(s in status for s in pending_statuses):
                        pending_tasks.append(title)
            except:
                pass
        if pending_tasks:
            return f"{len(pending_tasks)} pending task(s):\n" + "\n".join(f"- {t}" for t in pending_tasks[:5])
        return "No pending tasks found."
    except Exception as e:
        return f"Could not fetch Notion: {e}"


def generate_briefing_with_ai(data: Dict[str, str]) -> str:
    """Use Gemini AI to generate a natural morning briefing."""
    try:
        from integrations.gemini import create_gemini
        ai = create_gemini(session_id="briefing")

        prompt = f"""You are Nexus H1, Henry's personal assistant. It's {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}.

Generate a concise, helpful morning briefing in SPANISH. Keep it under 250 words. Be direct and slightly witty (Jarvis-style). Respond entirely in Spanish.

Here is the raw data:

--- CALENDAR ---
{data.get('calendar', 'No data')}

--- EMAILS ---
{data.get('email', 'No data')}

--- NOTION TASKS ---
{data.get('notion', 'No data')}

Format as a Telegram message with light Markdown (bold, bullet points). Start with a greeting. End with an encouraging sign-off.
"""

        response = ai.chat(prompt)
        return response
    except Exception as e:
        print(f"[BRIEFING] AI generation failed: {e}")
        return _generate_fallback_briefing(data)


def _generate_fallback_briefing(data: Dict[str, str]) -> str:
    """Fallback if AI fails."""
    lines = [
        "🌅 *¡Buenos días, Henry!*",
        "",
        f"📅 *Calendario*\n{data.get('calendar', 'Sin datos')}",
        "",
        f"📧 *Correos*\n{data.get('email', 'Sin datos')}",
        "",
        f"📝 *Tareas*\n{data.get('notion', 'Sin datos')}",
        "",
        "¡Que tengas un día productivo! ⚙️"
    ]
    return "\n".join(lines)


def run_briefing():
    """Main entry point -- collect data, generate briefing, send."""
    print(f"[{datetime.now()}] Generating morning briefing...")

    data = {
        "calendar": get_calendar_summary(),
        "email": get_email_summary(),
        "notion": get_notion_tasks(),
    }

    briefing = generate_briefing_with_ai(data)
    _send_telegram(briefing)
    print(f"[{datetime.now()}] Briefing sent.")


if __name__ == "__main__":
    run_briefing()
