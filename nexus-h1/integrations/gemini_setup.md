# Google Gemini Integration Setup

## Overview

Google Gemini provides a **free tier** with generous limits, making it perfect for Nexus H1 without any extra costs.

## Prerequisites

1. Google account
2. Access to Google AI Studio

## Steps

### 1. Get API Key (Free)

1. Go to https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the key

### 2. Configure Nexus H1

Add to `.env`:
```
GEMINI_API_KEY=AIzaSy...
```

### 3. Install Dependencies

```bash
py -m pip install google-generativeai
```

## Models Available

| Model | Description | Free Tier |
|-------|-------------|-----------|
| `gemini-2.5-flash` | Fast, efficient | ✅ Yes |
| `gemini-2.5-pro` | Best quality | ✅ Yes (limited) |
| `gemini-2.0-flash` | Older but stable | ✅ Yes |

Default in config: `gemini-2.5-flash`

## Usage

### Command Line

```bash
# Chat mode (uses Gemini by default)
py nexus.py chat
```

### Python

```python
from integrations.gemini import create_gemini

ai = create_gemini()
response = ai.chat("What's on my calendar today?")
print(response)
```

## Free Tier Limits

- 1,500 requests per day
- 1 million tokens per minute
- More than enough for personal use

## Switching Back to OpenAI

Edit `config.yaml`:
```yaml
ai:
  provider: "openai"  # or "gemini"
```

Or set environment variable:
```
AI_PROVIDER=openai
```
