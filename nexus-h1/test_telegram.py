#!/usr/bin/env python3
"""Quick Telegram debug test"""
import os
import time
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
print(f"Token loaded: {'YES' if TOKEN else 'NO'}")
print(f"Token prefix: {TOKEN[:15]}..." if TOKEN else "No token")

import requests

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# 1. Check bot info
print("\n--- 1. Bot Info ---")
resp = requests.post(f"{BASE_URL}/getMe", timeout=10).json()
print(f"OK: {resp.get('ok')}")
print(f"Username: {resp.get('result', {}).get('username')}")

# 2. Get updates (without offset to see all pending)
print("\n--- 2. Updates ---")
resp = requests.post(f"{BASE_URL}/getUpdates", json={"limit": 10}, timeout=10).json()
print(f"OK: {resp.get('ok')}")
updates = resp.get("result", [])
print(f"Updates count: {len(updates)}")

for u in updates:
    msg = u.get("message", {})
    chat = msg.get("chat", {})
    user = msg.get("from", {})
    print(f"  Update {u['update_id']}: chat_id={chat.get('id')}, user=@{user.get('username')}, text='{msg.get('text')}'")

# 3. If we have a chat_id, send test message
if updates:
    last_chat_id = updates[-1]["message"]["chat"]["id"]
    print(f"\n--- 3. Sending test to {last_chat_id} ---")
    resp = requests.post(
        f"{BASE_URL}/sendMessage",
        json={"chat_id": last_chat_id, "text": "Nexus H1 debug test ✅"},
        timeout=10
    ).json()
    print(f"Send OK: {resp.get('ok')}")
    if not resp.get('ok'):
        print(f"Error: {resp.get('description')}")
else:
    print("\n--- 3. No updates found, cannot send test ---")
    print("Try: send /start to @nexusH1bot in Telegram, then run this script again.")

print("\nDone.")
