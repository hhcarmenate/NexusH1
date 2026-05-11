# Gmail Integration Setup

## Prerequisites

1. Google Cloud project with Gmail API enabled
2. OAuth 2.0 credentials (Desktop app type)

## Steps

1. Go to https://console.cloud.google.com/
2. Create/select a project → **APIs & Services** → **Enable APIs** → Search "Gmail API" → Enable
3. **Credentials** → **Create Credentials** → **OAuth client ID**
   - Application type: **Desktop app**
   - Name: "Nexus H1"
4. Download the JSON file
5. Rename it to `gmail_credentials.json` and place it in `nexus-h1/secrets/`
6. Run `python integrations/gmail.py` once to authenticate (opens browser)
7. Token is saved to `secrets/gmail_token.json` for future runs

## Scopes Requested

- `gmail.modify` — read, send, delete, label
- `gmail.send` — send emails
- `gmail.readonly` — read-only access

## Usage Examples

```python
from integrations.gmail import list_messages, send_message, mark_as_read, archive

# List unread emails
emails = list_messages(max_results=5, query="is:unread")

# Send email
msg_id = send_message("friend@example.com", "Hello", "This is Nexus H1.")

# Mark as read
mark_as_read("MESSAGE_ID")

# Archive
archive("MESSAGE_ID")
```
