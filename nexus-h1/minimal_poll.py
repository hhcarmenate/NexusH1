import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('TELEGRAM_BOT_TOKEN')
url = f"https://api.telegram.org/bot{token}/getUpdates"

print("Minimal Telegram polling started")
print("Send ANY message to @nexusH1bot now!")
print("="*50)

offset = 0
while True:
    try:
        resp = requests.get(url, params={"offset": offset, "limit": 10}, timeout=30).json()
        if resp.get("ok"):
            updates = resp.get("result", [])
            for u in updates:
                offset = u["update_id"] + 1
                msg = u.get("message", {})
                text = msg.get("text", "")
                user = msg.get("from", {}).get("username", "unknown")
                print(f"\n[RECEIVED] From @{user}: {text}")
            if updates:
                print(f"\nTotal updates received: {len(updates)}")
        else:
            print(f"API error: {resp}")
    except Exception as e:
        print(f"Error: {e}")
    
    time.sleep(2)