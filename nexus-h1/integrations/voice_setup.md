# Voice Integration Setup

## Prerequisites

1. ElevenLabs account (recommended) OR OpenAI API key
2. Audio playback capability

## Setup

### Option 1: ElevenLabs (Recommended)

1. Sign up at https://elevenlabs.io
2. Get API key from profile settings
3. Add to `.env`:
   ```
   ELEVENLABS_API_KEY=sk_xxxxxxxx
   ```

### Option 2: OpenAI (Fallback)

1. Get API key from https://platform.openai.com
2. Add to `.env`:
   ```
   OPENAI_API_KEY=sk-xxxxxxxx
   ```

## Usage

### Command Line

```bash
# Speak text immediately
python integrations/voice.py say "Hello, I am Nexus H1"

# Save to file
python integrations/voice.py speak "Hello world"
```

### Python

```python
from integrations.voice import say, speak, listen

# Speak immediately
say("Good morning, Henry!")

# Save audio file
audio_path = speak("Meeting in 5 minutes")

# Transcribe audio file
text = listen("recording.wav")
```

## Voices

### ElevenLabs
- `nova` (default, warm)
- `shimmer` (bright)
- `echo` (deep)
- `onyx` (serious)
- `fable` (storyteller)
- `alloy` (neutral)

### OpenAI
- `nova`, `shimmer`, `echo`, `onyx`, `fable`, `alloy`

## Architecture

- **TTS**: Converts text → audio (MP3)
- **STT**: Converts audio → text (Whisper)
- **Playback**: Cross-platform audio playback
- **Storage**: Audio files saved to `memory/audio/`

## Future Enhancements

- [ ] Real-time streaming TTS
- [ ] Voice activity detection for STT
- [ ] Custom voice cloning (ElevenLabs)
- [ ] Local STT models (faster, offline)
