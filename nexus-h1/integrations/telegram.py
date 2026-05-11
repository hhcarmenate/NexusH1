#!/usr/bin/env python3
"""
Nexus H1 — Telegram Integration Module (Simplified)
Supports: send messages, receive updates, handle commands
"""

import os
import json
import time
from datetime import datetime
from typing import List, Dict, Optional, Callable
from pathlib import Path

from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

import requests

# Config
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else None

# Callback registry
_command_handlers: Dict[str, Callable] = {}
_message_handlers: List[Callable] = []


def _require_token():
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set. Add it to .env file.")


def _request(method: str, **params) -> Dict:
    """Make synchronous request to Telegram Bot API."""
    _require_token()
    url = f"{BASE_URL}/{method}"
    resp = requests.post(url, json=params, timeout=30)
    result = resp.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result.get('description')}")
    return result["result"]


def send_message(chat_id: int | str, text: str, parse_mode: str = "Markdown") -> Dict:
    """Send text message to a chat."""
    try:
        return _request("sendMessage", chat_id=chat_id, text=text, parse_mode=parse_mode)
    except RuntimeError as e:
        # If markdown parsing fails, retry without parse_mode
        if "can't parse entities" in str(e):
            return _request("sendMessage", chat_id=chat_id, text=text)
        raise


def send_photo(chat_id: int | str, photo_url: str, caption: str = "") -> Dict:
    """Send photo by URL."""
    return _request("sendPhoto", chat_id=chat_id, photo=photo_url, caption=caption)


def get_updates(offset: int = 0, limit: int = 100) -> List[Dict]:
    """Poll for new messages."""
    _require_token()
    return _request("getUpdates", offset=offset, limit=limit)


def get_me() -> Dict:
    """Get bot info."""
    return _request("getMe")


# Command handlers

def on_command(command: str):
    """Decorator to register command handler."""
    def decorator(func: Callable):
        _command_handlers[command.lstrip("/")] = func
        return func
    return decorator


def on_message(func: Callable):
    """Decorator to register message handler."""
    _message_handlers.append(func)
    return func


def poll_updates(interval: int = 2):
    """Long-polling loop for updates."""
    _require_token()
    offset = 0
    print(f"[{datetime.now()}] Telegram bot polling started...")
    print(f"Bot: @{get_me().get('username')}")
    
    while True:
        try:
            updates = get_updates(offset=offset, limit=100)
            
            for update in updates:
                offset = update["update_id"] + 1
                _process_update(update)
                
        except Exception as e:
            print(f"Polling error: {e}")
        
        time.sleep(interval)


def _process_update(update: Dict):
    """Process a single update."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return
    
    text = message.get("text", "")
    chat = message.get("chat", {})
    from_user = message.get("from", {})
    
    msg_data = {
        "update_id": update["update_id"],
        "chat_id": chat.get("id"),
        "chat_type": chat.get("type"),
        "user_id": from_user.get("id"),
        "username": from_user.get("username"),
        "first_name": from_user.get("first_name"),
        "text": text,
        "date": message.get("date"),
    }
    
    # Log message
    log_entry = f"[{datetime.now()}] {from_user.get('username', 'unknown')}: {text}\n"
    log_path = Path("memory/telegram_messages.log")
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_entry)
    
    print(f"Message from {from_user.get('username', 'unknown')}: {text}")
    
    # Run message handlers
    for handler in _message_handlers:
        try:
            handler(msg_data)
        except Exception as e:
            print(f"Message handler error: {e}")
    
    # Check for commands
    if text.startswith("/"):
        parts = text.split()
        command = parts[0][1:].split("@")[0]  # Remove / and @botname
        args = parts[1:]
        
        handler = _command_handlers.get(command)
        if handler:
            try:
                handler(msg_data, args)
            except Exception as e:
                print(f"Command handler error: {e}")


# Default handlers

@on_command("start")
def cmd_start(msg, args):
    """Handle /start command."""
    welcome = (
        "🤖 *Nexus H1* — Your Personal Assistant\n\n"
        "Available commands:\n"
        "/status — Check system status\n"
        "/help — Show this help\n"
        "/notify <message> — Send notification to Henry"
    )
    send_message(msg["chat_id"], welcome)


@on_command("help")
def cmd_help(msg, args):
    """Handle /help command."""
    cmd_start(msg, args)


@on_command("status")
def cmd_status(msg, args):
    """Handle /status command."""
    status_text = "✅ *Nexus H1* is online and operational."
    send_message(msg["chat_id"], status_text)


@on_command("notify")
def cmd_notify(msg, args):
    """Handle /notify command."""
    if args:
        notification = " ".join(args)
        send_message(msg["chat_id"], f"📢 Notification sent: _{notification}_")
    else:
        send_message(msg["chat_id"], "Usage: /notify <your message>")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "poll":
        try:
            poll_updates()
        except KeyboardInterrupt:
            print("\nPolling stopped.")
    else:
        print("Usage: python telegram.py poll")
        print("\nMake sure TELEGRAM_BOT_TOKEN is set in your .env file.")
