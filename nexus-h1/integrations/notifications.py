#!/usr/bin/env python3
"""
Nexus H1 — Smart Notifications Engine
Proactively checks Gmail, Calendar, Notion and sends alerts via Telegram.
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Load config
import yaml
config_path = Path(__file__).parent.parent / "config.yaml"
config = yaml.safe_load(config_path.read_text()) if config_path.exists() else {}

NOTIFICATIONS_CONFIG = config.get("notifications", {})
TELEGRAM_CHAT_ID_FILE = Path("secrets/telegram_chat_id.txt")


def _get_chat_id() -> Optional[str]:
    """Get Telegram chat ID from file or env."""
    if TELEGRAM_CHAT_ID_FILE.exists():
        return TELEGRAM_CHAT_ID_FILE.read_text().strip()
    return os.getenv("TELEGRAM_CHAT_ID")


def _save_chat_id(chat_id: str):
    """Save chat ID for future notifications."""
    TELEGRAM_CHAT_ID_FILE.write_text(chat_id)


def _send_telegram(message: str):
    """Send notification to Telegram."""
    try:
        from integrations.telegram import send_message
        chat_id = _get_chat_id()
        if chat_id:
            send_message(chat_id, f"🔔 *Nexus H1 Notification*\n\n{message}", parse_mode="Markdown")
            print(f"[NOTIFY] Sent to {chat_id}: {message[:60]}...")
        else:
            print("[NOTIFY] No chat_id configured. Cannot send Telegram message.")
    except Exception as e:
        print(f"[NOTIFY] Failed to send Telegram: {e}")


def check_calendar() -> Optional[str]:
    """Check for upcoming events in the next 2 hours."""
    if not config.get("integrations", {}).get("calendar", {}).get("enabled"):
        return None
    
    try:
        from integrations.google_calendar import get_upcoming_events
        
        now = datetime.now()
        soon = now + timedelta(hours=2)
        
        events = get_upcoming_events(days=1)
        upcoming = []
        
        for event in events:
            start = event.get("start", {})
            start_time = start.get("dateTime") or start.get("date")
            if start_time:
                try:
                    event_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    if now <= event_dt <= soon:
                        upcoming.append(event)
                except:
                    pass
        
        if upcoming:
            lines = ["📅 *Upcoming Events (next 2h):*"]
            for e in upcoming:
                summary = e.get("summary", "Untitled")
                start = e.get("start", {})
                time_str = start.get("dateTime", start.get("date", ""))
                lines.append(f"  • {summary} — {time_str}")
            return "\n".join(lines)
        
        return None
    except Exception as e:
        print(f"[NOTIFY] Calendar check failed: {e}")
        return None


def check_gmail() -> Optional[str]:
    """Check for unread emails from important senders."""
    if not config.get("integrations", {}).get("gmail", {}).get("enabled"):
        return None
    
    try:
        from integrations.gmail import list_messages
        
        # Get unread emails
        emails = list_messages(max_results=10, query="is:unread in:inbox")
        
        if not emails:
            return None
        
        important_senders = NOTIFICATIONS_CONFIG.get("important_senders", [])
        
        important_emails = []
        for email in emails:
            # list_messages now returns processed messages from get_message
            sender = email.get("from", "")
            subject = email.get("subject", "(no subject)")
            
            # Check if from important sender
            is_important = any(s.lower() in sender.lower() for s in important_senders) if important_senders else True
            
            if is_important:
                # Truncate long subjects
                subject_display = subject[:50] + "..." if len(subject) > 50 else subject
                sender_display = sender.split("<")[0].strip()[:30] if "<" in sender else sender[:30]
                important_emails.append(f"  • {subject_display} — from {sender_display}")
        
        if important_emails:
            lines = [f"📧 *You have {len(emails)} unread email(s):*"]
            lines.extend(important_emails[:5])  # Max 5
            if len(important_emails) > 5:
                lines.append(f"  ... and {len(important_emails) - 5} more")
            return "\n".join(lines)
        
        return None
    except Exception as e:
        print(f"[NOTIFY] Gmail check failed: {e}")
        return None


def check_notion() -> Optional[str]:
    """Check for pending tasks in Notion."""
    if not config.get("integrations", {}).get("notion", {}).get("enabled"):
        return None
    
    try:
        from integrations.notion import search, query_database
        
        # Search for databases
        databases = search("", filter_type="database", page_size=10)
        
        pending_tasks = []
        
        for db in databases:
            db_id = db["id"]
            db_title = db.get("title", [{}])[0].get("text", {}).get("content", "Untitled")
            
            try:
                entries = query_database(db_id, page_size=20)
                for entry in entries:
                    props = entry.get("properties", {})
                    # Check for status property
                    status = None
                    for key, val in props.items():
                        if key.lower() in ["status", "estado", "state"]:
                            if "select" in val:
                                status = val["select"].get("name", "").lower()
                            elif "status" in val:
                                status = val["status"].get("name", "").lower()
                    
                    # Check if task is pending (broader check)
                    pending_statuses = ["not started", "in progress", "pending", "to do", "todo", 
                                      "por hacer", "pendiente", "doing", "en progreso", "backlog"]
                    if status and any(s in status for s in pending_statuses):
                        # Extract title from various property types
                        title = "Untitled"
                        for key, val in props.items():
                            key_lower = key.lower()
                            if key_lower in ["name", "title", "título", "task", "tarea"]:
                                if "title" in val and val["title"]:
                                    title = val["title"][0].get("text", {}).get("content", "Untitled")
                                elif "rich_text" in val and val["rich_text"]:
                                    title = val["rich_text"][0].get("text", {}).get("content", "Untitled")
                                break
                        
                        # Fallback: find any text property
                        if title == "Untitled":
                            for key, val in props.items():
                                if "title" in val and val["title"]:
                                    title = val["title"][0].get("text", {}).get("content", "Untitled")
                                    break
                        
                        title_display = title[:40] + "..." if len(title) > 40 else title
                        pending_tasks.append(f"  • {title_display} ({db_title})")
            except:
                pass
        
        if pending_tasks:
            lines = [f"📝 *Pending Tasks:*"]
            lines.extend(pending_tasks[:5])
            if len(pending_tasks) > 5:
                lines.append(f"  ... and {len(pending_tasks) - 5} more")
            return "\n".join(lines)
        
        return None
    except Exception as e:
        print(f"[NOTIFY] Notion check failed: {e}")
        return None


def run_notifications():
    """Run all notification checks and send combined message."""
    print(f"[{datetime.now()}] Running smart notifications...")
    
    notifications = []
    
    # Check calendar
    cal = check_calendar()
    if cal:
        notifications.append(cal)
    
    # Check gmail
    mail = check_gmail()
    if mail:
        notifications.append(mail)
    
    # Check notion
    tasks = check_notion()
    if tasks:
        notifications.append(tasks)
    
    if notifications:
        message = "\n\n".join(notifications)
        _send_telegram(message)
    else:
        print("[NOTIFY] Nothing to notify.")


def auto_detect_chat_id():
    """Try to detect chat_id from Telegram updates."""
    try:
        from integrations.telegram import get_updates
        updates = get_updates(offset=0, limit=10)
        for update in updates:
            message = update.get("message")
            if message:
                chat_id = message.get("chat", {}).get("id")
                if chat_id:
                    _save_chat_id(str(chat_id))
                    print(f"[NOTIFY] Auto-detected chat_id: {chat_id}")
                    return chat_id
    except Exception as e:
        print(f"[NOTIFY] Could not auto-detect chat_id: {e}")
    return None


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "detect":
        auto_detect_chat_id()
    else:
        run_notifications()
