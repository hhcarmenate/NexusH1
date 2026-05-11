#!/usr/bin/env python3
"""
Nexus H1 — Voice Integration Module (v2)
TTS (Text-to-Speech) and STT (Speech-to-Text)
"""

import os
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Callable

# Config
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TTS_VOICE = "nova"  # Default voice (works for both OpenAI and ElevenLabs)

# Paths
AUDIO_DIR = Path("memory/audio")
AUDIO_DIR.mkdir(exist_ok=True)


def _init_mixer():
    """Lazy-init pygame mixer for audio playback."""
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        return pygame.mixer
    except Exception as e:
        raise RuntimeError(f"Failed to init pygame mixer: {e}")


class TTS:
    """Text-to-Speech using OpenAI (primary) or ElevenLabs (fallback)."""

    def __init__(self, voice: str = TTS_VOICE):
        self.voice = voice
        self.provider = self._detect_provider()

    def _detect_provider(self) -> str:
        if OPENAI_API_KEY:
            return "openai"
        elif ELEVENLABS_API_KEY:
            return "elevenlabs"
        return "none"

    def speak(self, text: str, save_path: Optional[str] = None) -> str:
        """Convert text to speech and return audio file path."""
        if self.provider == "none":
            raise RuntimeError("No TTS provider configured. Set OPENAI_API_KEY or ELEVENLABS_API_KEY.")

        if save_path is None:
            save_path = AUDIO_DIR / f"tts_{hash(text) % 10000}.mp3"
        else:
            save_path = Path(save_path)

        if self.provider == "elevenlabs":
            return self._elevenlabs_tts(text, save_path)
        elif self.provider == "openai":
            return self._openai_tts(text, save_path)

    def _elevenlabs_tts(self, text: str, save_path: Path) -> str:
        """Use ElevenLabs API."""
        import requests

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice}"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        }
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5,
            },
        }

        response = requests.post(url, json=data, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(f"ElevenLabs error: {response.text}")

        save_path.write_bytes(response.content)
        return str(save_path)

    def _openai_tts(self, text: str, save_path: Path) -> str:
        """Use OpenAI TTS API."""
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.audio.speech.create(
            model="tts-1",
            voice=self.voice,
            input=text,
        )
        response.stream_to_file(save_path)
        return str(save_path)

    def play(self, audio_path: str):
        """Play audio file using pygame mixer (cross-platform, supports mp3)."""
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        mixer = _init_mixer()
        mixer.music.load(str(audio_path))
        mixer.music.play()
        while mixer.music.get_busy():
            import time
            time.sleep(0.1)

    def say(self, text: str):
        """Speak text immediately."""
        path = self.speak(text)
        self.play(path)


class STT:
    """Speech-to-Text using OpenAI Whisper."""

    def __init__(self):
        self.provider = "openai" if OPENAI_API_KEY else "none"

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text."""
        if self.provider == "none":
            raise RuntimeError("OpenAI API key required for STT.")

        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        with open(audio_path, "rb") as audio:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
            )
        return transcript.text

    def record_audio(self, duration: int = 5, output_path: Optional[str] = None) -> str:
        """Record audio from microphone and save to file.

        Uses sounddevice + numpy (cross-platform, works on Windows/Mac/Linux).
        """
        import sounddevice as sd
        import numpy as np
        import wave

        if output_path is None:
            output_path = tempfile.mktemp(suffix=".wav")
        else:
            output_path = str(output_path)

        print(f"[STT] Recording for {duration} seconds... Speak now!")

        # Record at 16kHz (Whisper's preferred sample rate)
        samplerate = 16000
        samples = int(duration * samplerate)
        recording = sd.rec(samples, samplerate=samplerate, channels=1, dtype=np.int16)
        sd.wait()

        # Save as WAV
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(samplerate)
            wf.writeframes(recording.tobytes())

        print(f"[STT] Saved recording to {output_path}")
        return output_path

    def transcribe_microphone(self, duration: int = 5) -> str:
        """Record from microphone and transcribe in one step."""
        wav_path = self.record_audio(duration=duration)
        return self.transcribe(wav_path)


# Convenience functions
tts_engine = None
stt_engine = None


def init_voice():
    """Initialize voice engines."""
    global tts_engine, stt_engine
    tts_engine = TTS()
    stt_engine = STT()


def say(text: str):
    """Speak text."""
    if not tts_engine:
        init_voice()
    tts_engine.say(text)


def speak(text: str, save_path: Optional[str] = None) -> str:
    """Convert text to audio file."""
    if not tts_engine:
        init_voice()
    return tts_engine.speak(text, save_path)


def listen(duration: int = 5) -> str:
    """Record from microphone and transcribe to text."""
    if not stt_engine:
        init_voice()
    return stt_engine.transcribe_microphone(duration=duration)


def listen_file(audio_path: str) -> str:
    """Transcribe an existing audio file."""
    if not stt_engine:
        init_voice()
    return stt_engine.transcribe(audio_path)
