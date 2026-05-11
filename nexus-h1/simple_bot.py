#!/usr/bin/env python3
"""
Minimal Telegram bot for testing - just echoes messages back.
"""
import os
import time
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not set")
    exit(1)

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"
offset = 0

print("=" * 50)
print("Minimal Telegram Bot - Polling Test")
print("=" * 50)
print(f"Bot: {BASE_URL[:30]}...")
print("Send a message to @nexusH1bot now!")
print("=" * 50)

def send_message(chat_id, text):
    try:
        url = f"{BASE_URL}/sendMessage"
        resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        return resp.json().get("ok")
    except Exception as e:
        print(f"Send error: {e}")
        return False

while True:
    try:
        url = f"{BASE_URL}/getUpdates"
        resp = requests.get(url, params={"offset": offset, "limit": 10}, timeout=30)
        data = resp.json()
        
        if not data.get("ok"):
            print(f"API Error: {data}")
            time.sleep(5)
            continue
        
        updates = data.get("result", [])
        
        if updates:
            print(f"\n[{time.strftime('%H:%M:%S')}] Received {len(updates)} update(s)")
            
            for update in updates:
                offset = update["update_id"] + 1
                
                message = update.get("message")
                if not message:
                    continue
                
                text = message.get("text", "")
                chat_id = message["chat"]["id"]
                username = message.get("from", {}).get("username", "unknown")
                
                print(f"  From @{username}: {text[:50]}")
                
                # Echo back
                reply = f"Echo: {text}"
                if send_message(chat_id, reply):
                    print(f"  Replied: {reply[:50]}")
                else:
                    print(f"  Failed to reply")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Polling... (offset={offset})", end="\r")
        
    except Exception as e:
        print(f"\nError: {e}")
    
    time.sleep(2)