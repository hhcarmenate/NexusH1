import os
import time
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

token = os.getenv('TELEGRAM_BOT_TOKEN')
if not token:
    print("No token found")
    exit(1)

url = f"https://api.telegram.org/bot{token}"

print(f"Bot: {url[:30]}...")
print("Waiting for messages...")
print("Send a message to the bot now!\n")

offset = 0
for i in range(30):  # Poll for 60 seconds
    try:
        resp = requests.get(f"{url}/getUpdates", params={"offset": offset, "limit": 10}, timeout=10).json()
        if resp.get("ok"):
            updates = resp.get("result", [])
            if updates:
                print(f"[{i}] Got {len(updates)} updates:")
                for u in updates:
                    offset = u["update_id"] + 1
                    msg = u.get("message", {})
                    text = msg.get("text", "")
                    chat_id = msg.get("chat", {}).get("id")
                    from_user = msg.get("from", {}).get("username", "unknown")
                    print(f"  From @{from_user} in chat {chat_id}: {text}")
            else:
                print(f"[{i}] No updates", end="\r")
        else:
            print(f"[{i}] API error: {resp}")
    except Exception as e:
        print(f"[{i}] Error: {e}")
    
    time.sleep(2)

print("\nDone polling.")