# Google Calendar Integration Setup

## Prerequisites

1. Google Cloud project with Calendar API enabled
2. OAuth 2.0 credentials (same as Gmail or separate)

## Steps

1. Go to https://console.cloud.google.com/
2. Select your Nexus H1 project
3. **APIs & Services** → **Enable APIs** → Search "Calendar API" → Enable
4. (If not done for Gmail) **Credentials** → **Create Credentials** → **OAuth client ID**
   - Application type: **Desktop app**
   - Name: "Nexus H1 Calendar"
5. Download credentials and save as `secrets/calendar_credentials.json`
   - Or reuse `secrets/gmail_credentials.json` (same Google project works)
6. Run `python integrations/calendar.py today` to authenticate

## Usage

### CLI

```bash
# Today's events
python integrations/calendar.py today

# Next 7 days
python integrations/calendar.py upcoming

# Next 14 days
python integrations/calendar.py upcoming 14
```

### Python

```python
from integrations.calendar import (
    get_todays_events, get_upcoming_events,
    create_event, delete_event, create_quick_reminder
)
from datetime import datetime, timedelta

# Today's events
today = get_todays_events()

# Create meeting
start = datetime(2026, 5, 10, 14, 0)
end = start + timedelta(hours=1)
create_event(
    summary="Team Sync",
    start=start,
    end=end,
    description="Weekly team sync",
    attendees=["colleague@example.com"],
)

# Quick reminder
create_quick_reminder("Call mom", minutes_from_now=60)
```

## Features

- 📅 List events (today, upcoming, date range)
- ➕ Create events with attendees and reminders
- ✏️ Update existing events
- 🗑️ Delete events
- ⏰ Quick reminders
