# Telegram Integration Setup

## Prerequisites

1. Telegram account
2. Bot created via @BotFather

## Steps

1. Open Telegram and search for **@BotFather**
2. Start chat and send `/newbot`
3. Follow prompts:
   - Name: `Nexus H1`
   - Username: `nexus_h1_bot` (must end in _bot)
4. Copy the **HTTP API token** provided
5. Add to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_token_here
   ```

## Usage

### Start Polling

```bash
python integrations/telegram.py poll
```

### Send Message from Code

```python
from integrations.telegram import send_message

send_message("@your_username", "Hello from Nexus H1!")
```

### Custom Commands

```python
from integrations.telegram import on_command, send_message

@on_command("remind")
async def remind(msg, args):
    text = " ".join(args)
    # Process reminder...
    send_message(msg["chat_id"], f"⏰ Reminder set: {text}")
```

## Architecture

- **Polling mode**: Default for local development
- **Webhook mode**: For production deployment
- Messages logged to `memory/telegram_messages.log`
