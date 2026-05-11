# Nexus H1

_Your personal Jarvis-style assistant for organization, communication, productivity, and infrastructure monitoring._

## Overview

Nexus H1 connects your digital life — email, messaging, calendar, notes, voice, and private cloud infrastructure — into a single intelligent assistant that understands natural language and takes action.

**Philosophy:** You speak naturally. Nexus understands intent, not commands.

---

## What You Can Say

| You say | Nexus does |
|---------|-----------|
| _"¿Cómo está el servidor?"_ | Checks Pi5/Nextcloud status (CPU, RAM, temp, Docker) |
| _"Revisa mi calendario"_ | Shows today's events from Google Calendar |
| _"Archiva los correos de promoción"_ | Archives Gmail promotions automatically |
| _"Envía WhatsApp a Juan"_ | Sends WhatsApp message via AI |
| _"Crea una nota en Notion"_ | Creates Notion page with your content |
| _"¿Cuántos emails tengo?"_ | Counts and shows unread emails |
| _"¿Qué tal la pi?"_ | Full server status report |
| _"Morning brief"_ | Daily summary: calendar, emails, tasks, weather |

All via **voice or text** in Telegram.

---

## Core Features

### 🤖 AI Engine (Gemini)
- **Natural language understanding** — speaks Spanish & English
- **Function calling** — decides which tool to use based on intent
- **Persistent memory** — remembers context across conversations
- **No regex needed** — understands "¿qué tal el server?", "how's the pi?", "estado de nextcloud"

### 🖥️ Private Cloud Monitor (Pi5/Nextcloud)
- **SSH-based monitoring** of your Ubuntu server
- **Metrics:** CPU, RAM, disk, temperature, uptime, Docker containers
- **Smart alerts** — only notifies when something is wrong (temp >75°C, CPU >85%, disk >90%)
- **Periodic reports** — automatic status every 30 minutes via Telegram
- **Voice-activated** — ask "how's my server?" and get instant status

### 📧 Gmail Intelligence
- **Read & search** emails with natural queries
- **Archive by intent** — "archive promotions", "clean social notifications"
- **Send emails** with AI-generated content
- **Unread summaries** — quick digest of what's pending

### 📅 Google Calendar
- **Today's events** — what's coming up
- **Create reminders** — "remind me to call mom at 5pm"
- **Natural queries** — "what do I have tomorrow?"

### 📝 Notion Integration
- **Search pages & databases**
- **Create notes** with structured content
- **Query databases** — tasks, projects, etc.

### 🎙️ Voice (OpenAI Whisper + TTS)
- **Voice messages in Telegram** — send audio, Nexus transcribes and acts
- **Whisper STT** — $0.006/minute (ridiculously cheap)
- **OpenAI TTS** — natural-sounding voice responses
- **Multi-language** — understands Spanish, English, and mixed speech

### 💬 Telegram Bot
- **24/7 running** as Windows service
- **Voice & text input**
- **Rich responses** — formatted with emojis, markdown, and structure
- **Notifications** — proactive alerts for server, calendar, important emails

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     YOU (Telegram)                       │
│              Voice or Text in Natural Language           │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                TELEGRAM BRIDGE                          │
│         - Receives messages & voice files               │
│         - Downloads .ogg audio                          │
│         - Routes to AI or direct handlers               │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              WHISPER (OpenAI) — Voice Only              │
│              Transcribes audio → text                   │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              GEMINI AI (Function Calling)               │
│         - Understands intent from text                  │
│         - Decides which tool to call                    │
│         - Formulates natural response                   │
└─────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌──────────────┐
    │  Gmail   │   │  Pi5/SSH │   │    Notion    │
    │ Calendar │   │  Monitor │   │   Telegram   │
    └──────────┘   └──────────┘   └──────────────┘
```

**Key Design Decision:**
- **Regex is dead.** Gemini understands intent — you don't need exact keywords.
- **Tools are composable.** Add a new integration, Gemini learns to use it automatically.
- **Raw output preserved.** Server status returns formatted markdown with emojis, not re-written text.

---

## Quick Start

### Prerequisites
- Python 3.10+
- Windows 10/11 (for service mode)
- Telegram account
- API keys (see `.env.example`)

### 1. Clone & Setup

```bash
cd "nexus H1/nexus-h1"
cp .env.example .env
# Edit .env with your API keys
```

### 2. Install Dependencies

```bash
py -m pip install -r requirements.txt
```

### 3. Configure Environment

Edit `.env`:

```env
# Required
GEMINI_API_KEY=your_gemini_key
TELEGRAM_BOT_TOKEN=your_bot_token

# Gmail / Calendar / Notion (optional but recommended)
NOTION_TOKEN=your_notion_token
OPENAI_API_KEY=your_openai_key  # For voice

# Pi5 / Private Cloud (optional)
PI_HOST=precisembc-cloud.local
PI_USER=henry
PI_PASSWORD=your_password
```

### 4. Run Interactively (Development)

```bash
py start.py
```

### 5. Install as Windows Service (Production)

Run PowerShell as **Administrator**:

```powershell
& "C:\Users\Yosva\Desktop\nexus H1\install-nexush1.bat"
```

Or use NSSM directly:

```powershell
# Install
C:\Tools\nssm.exe install NexusH1 "C:\Path\To\python.exe" "start.py"

# Configure
C:\Tools\nssm.exe set NexusH1 AppDirectory "C:\Users\Yosva\Desktop\nexus H1\nexus-h1"
C:\Tools\nssm.exe set NexusH1 AppExit Default Restart
C:\Tools\nssm.exe set NexusH1 Start SERVICE_AUTO_START

# Start
net start NexusH1
```

### 6. Access via Telegram

1. Search for `@nexusH1bot` on Telegram
2. Send `/start`
3. Chat naturally — text or voice!

---

## Project Structure

```
nexus-h1/
├── start.py                      # Main entry point — starts all services
├── start.bat                     # Windows quick start (development)
├── stop.bat                      # Stop script
├── nexus.py                      # Core orchestrator
├── config.yaml                   # YAML configuration
├── .env                          # Environment variables (gitignored)
├── .env.example                  # Template for .env
├── requirements.txt              # Python dependencies
├── AGENT.md                      # Assistant identity & personality
├── README.md                     # This file
│
├── memory/                       # Daily logs & persistent memory
│   ├── 2026-05-11.log           # Activity log
│   ├── long_term.md             # Long-term memory
│   └── conversations/           # AI conversation history
│
├── secrets/                      # Credentials (gitignored)
│   ├── gmail_credentials.json
│   ├── gmail_token.json
│   └── telegram_chat_id.txt
│
├── logs/                         # Service logs (when running as service)
│   ├── service.log
│   └── service-error.log
│
└── integrations/                 # Service connectors
    ├── gemini.py                # AI engine with function calling
    ├── gmail.py                 # Read, send, archive emails
    ├── google_calendar.py       # Calendar events
    ├── notion.py                # Notes & databases
    ├── telegram.py              # Telegram API wrapper
    ├── telegram_bridge.py       # Bot polling & message routing
    ├── pi_monitor.py            # Pi5/Nextcloud SSH monitor
    ├── morning_briefing.py      # Daily summary generator
    ├── voice.py                 # TTS (OpenAI) + STT (Whisper)
    └── whatsapp.py              # WhatsApp integration
```

---

## Natural Language Capabilities

### Server Monitoring

| Intent | Example phrases | Action |
|--------|----------------|--------|
| Check status | "¿cómo está la pi?", "server status", "how's nextcloud?" | Runs `get_server_status` |
| Periodic report | Automatic every 30 min | Sends formatted status |
| Alert | When temp/CPU/disk exceeds threshold | Immediate notification |

### Email Management

| Intent | Example phrases | Action |
|--------|----------------|--------|
| Read emails | "check my emails", "unread emails" | Lists recent emails |
| Archive promotions | "archive promotions", "clean spam" | Archives `category:promotions` |
| Archive social | "archive social notifications" | Archives `category:social` |
| Send email | "send email to boss" | Composes and sends |

### Calendar

| Intent | Example phrases | Action |
|--------|----------------|--------|
| Today's events | "what's on my calendar?" | Lists today's events |
| Create reminder | "remind me to call mom at 5pm" | Creates calendar event |

---

## Configuration Reference

### `.env` Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `GEMINI_API_KEY` | Google Gemini AI | ✅ Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram bot (@BotFather) | ✅ Yes |
| `NOTION_TOKEN` | Notion integration | ❌ Optional |
| `OPENAI_API_KEY` | Whisper STT / TTS | ❌ Optional (for voice) |
| `ELEVENLABS_API_KEY` | Alternative TTS | ❌ Optional |
| `PI_HOST` | Pi5 SSH hostname/IP | ❌ Optional |
| `PI_USER` | Pi5 SSH username | ❌ Optional |
| `PI_PASSWORD` | Pi5 SSH password | ❌ Optional |

### `config.yaml`

```yaml
user:
  name: "Henry"
  timezone: "America/New_York"
  language: "en"

integrations:
  gmail:
    enabled: true
  telegram:
    enabled: true
  notion:
    enabled: true
  calendar:
    enabled: true

voice:
  enabled: true
  stt_provider: "openai"
  tts_provider: "openai"
  tts_voice: "nova"

notifications:
  enabled: true
  interval_minutes: 30
```

---

## Service Management

When installed as Windows service via NSSM:

```powershell
# Check status
Get-Service NexusH1

# Restart
Restart-Service NexusH1

# Stop
Stop-Service NexusH1

# View logs
Get-Content "nexus-h1/logs/service.log" -Tail 50 -Wait
```

Or via GUI: `Win + R` → `services.msc` → find **Nexus H1 Assistant**

---

## Troubleshooting

### "Insufficient quota" error
OpenAI API key needs funding. Add $5 at [platform.openai.com](https://platform.openai.com).

### Pi monitor shows "Docker no disponible"
Ensure `docker` is installed on Pi5 and user has permissions.

### Voice transcription fails
Check `OPENAI_API_KEY` is set and has billing enabled.

### Service won't start
Run PowerShell as Administrator. Check logs in `logs/service-error.log`.

---

## Roadmap

- [x] AI conversational engine (Gemini + Function Calling)
- [x] Telegram bot with voice support
- [x] Gmail read/send/archive
- [x] Google Calendar integration
- [x] Notion integration
- [x] Pi5/Nextcloud infrastructure monitoring
- [x] Voice → Text → AI pipeline (Whisper)
- [x] Windows service with auto-restart
- [x] Morning briefing (daily digest)
- [x] Smart alerts (server, email, calendar)
- [ ] WhatsApp full integration
- [ ] Web dashboard (Vue.js)
- [ ] Multi-language morning brief
- [ ] Security monitoring (SSH intrusion detection)
- [ ] Remote command execution via voice

---

## License

Personal use only — your own Jarvis.

---

_Built by Nexus H1 for Henry._
