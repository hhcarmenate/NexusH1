import os
from dotenv import load_dotenv
load_dotenv()

from integrations.telegram import get_updates, send_message

print("Testing Telegram integration...")

# Try to get updates
updates = get_updates(offset=0, limit=10)
print(f"Got {len(updates)} updates")

# Send test message to ourselves
chat_id = "6275323845"
result = send_message(chat_id, "Test from simple_test.py")
print(f"Message sent: {result.get('message_id')}")

# Get updates again
updates = get_updates(offset=0, limit=10)
print(f"After sending, got {len(updates)} updates")

print("Done")