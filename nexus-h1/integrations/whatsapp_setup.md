# WhatsApp Integration Setup

## Prerequisites

1. Node.js installed (v18+)
2. WhatsApp on your phone

## Steps

1. Install dependencies:
   ```bash
   cd integrations
   npm install whatsapp-web.js qrcode-terminal
   ```

2. Start the client:
   ```bash
   python whatsapp.py start
   ```

3. On first run, a QR code will be saved to `secrets/whatsapp_qr.txt`
   - Open WhatsApp on your phone
   - Settings → Linked Devices → Link a Device
   - Scan the QR code

4. Session is persisted in `secrets/whatsapp_session/`
   - No need to scan again unless you log out

## Usage

```python
from integrations.whatsapp import start, send, chats, pending, stop

# Start client
start()

# Send message
send("1234567890", "Hello from Nexus H1!")

# Get chats
recent_chats = chats()

# Get pending messages
msgs = pending()
for msg in msgs:
    print(f"From {msg['from']}: {msg['body']}")

# Stop
stop()
```

## Architecture

- `whatsapp.js` — Node.js process using whatsapp-web.js library
- `whatsapp.py` — Python wrapper that manages the Node process
- Communication via stdin/stdout JSON commands
