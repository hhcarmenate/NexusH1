#!/usr/bin/env python3
"""
Nexus H1 — Telegram Bridge
Connects Telegram Bot with AI Assistant
"""

import os
import time
import threading
import requests
from datetime import datetime
from typing import Callable, Optional
from pathlib import Path

from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else None


def _send_message(chat_id: int | str, text: str, parse_mode: str = None) -> dict:
    """Send text message to a chat."""
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set")
    
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    
    resp = requests.post(url, json=payload, timeout=10)
    result = resp.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result.get('description')}")
    return result["result"]


def _send_chat_action(chat_id: int | str, action: str = "typing"):
    """Send chat action (typing, upload_voice, etc.)."""
    if not TOKEN:
        return
    url = f"{BASE_URL}/sendChatAction"
    requests.post(url, json={"chat_id": chat_id, "action": action}, timeout=5)


def _download_telegram_file(file_id: str) -> bytes:
    """Download file from Telegram by file_id."""
    # Step 1: Get file path
    url = f"{BASE_URL}/getFile"
    resp = requests.post(url, json={"file_id": file_id}, timeout=10)
    result = resp.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram getFile error: {result}")
    
    file_path = result["result"]["file_path"]
    
    # Step 2: Download actual file
    download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    file_resp = requests.get(download_url, timeout=30)
    file_resp.raise_for_status()
    return file_resp.content


def _transcribe_voice(file_id: str) -> str:
    """Download voice message and transcribe with Whisper."""
    from integrations.voice import listen_file
    import tempfile
    
    # Download voice file
    voice_data = _download_telegram_file(file_id)
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp.write(voice_data)
        tmp_path = tmp.name
    
    try:
        # Transcribe with Whisper
        transcript = listen_file(tmp_path)
        return transcript
    finally:
        # Cleanup temp file
        Path(tmp_path).unlink(missing_ok=True)


class TelegramBridge:
    """Bridge between Telegram and Nexus H1 AI."""
    
    def __init__(self, ai_callback: Optional[Callable] = None):
        self.ai_callback = ai_callback
        self.running = False
        self.thread = None
        self.offset = 0
        self.authorized_users = set()
        
    def start(self, interval: int = 2):
        """Start polling in background thread."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, args=(interval,), daemon=True)
        self.thread.start()
        print(f"[{datetime.now()}] Telegram bridge started")
        
    def stop(self):
        """Stop polling."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print(f"[{datetime.now()}] Telegram bridge stopped")
    
    def _poll_loop(self, interval: int):
        """Polling loop running in background."""
        print(f"[{datetime.now()}] Poll loop started (offset={self.offset})")
        while self.running:
            try:
                url = f"{BASE_URL}/getUpdates"
                resp = requests.get(url, params={"offset": self.offset, "limit": 10}, timeout=30)
                data = resp.json()
                
                if not data.get("ok"):
                    print(f"[{datetime.now()}] API error: {data}")
                    time.sleep(5)
                    continue
                
                updates = data.get("result", [])
                
                for update in updates:
                    self.offset = update["update_id"] + 1
                    self._process_update(update)
                    
            except Exception as e:
                print(f"[{datetime.now()}] Polling error: {e}")
                import traceback
                traceback.print_exc()
            
            time.sleep(interval)
    
    def _process_update(self, update: dict):
        """Process incoming message and respond via AI."""
        message = update.get("message") or update.get("edited_message")
        if not message:
            return
        
        text = message.get("text", "")
        chat = message.get("chat", {})
        from_user = message.get("from", {})
        
        chat_id = chat.get("id")
        username = from_user.get("username", "unknown")
        
        # Skip own messages
        if from_user.get("is_bot"):
            return
        
        # Handle voice messages
        voice = message.get("voice") or message.get("audio")
        if voice:
            print(f"[{datetime.now()}] Telegram voice from @{username}")
            _send_chat_action(chat_id, "typing")
            try:
                file_id = voice["file_id"]
                transcript = _transcribe_voice(file_id)
                text = transcript.strip()
                print(f"[{datetime.now()}] Voice transcribed: '{text}'")
                if text:
                    _send_message(chat_id, f"🎙️ *Escuché:* _{text}_", parse_mode="Markdown")
                else:
                    _send_message(chat_id, "🎙️ No pude entender el audio. ¿Podés repetirlo?")
                    return
            except Exception as e:
                print(f"[{datetime.now()}] Voice transcription error: {e}")
                _send_message(chat_id, f"🎙️ Error procesando el audio: {e}")
                return
        
        print(f"[{datetime.now()}] Telegram from @{username}: {text}")
        
        # Track authorized user
        self.authorized_users.add(chat_id)
        
        # Save chat_id for notifications
        chat_id_file = Path("secrets/telegram_chat_id.txt")
        if not chat_id_file.exists() or chat_id_file.read_text().strip() != str(chat_id):
            chat_id_file.write_text(str(chat_id))
            print(f"[{datetime.now()}] Saved chat_id: {chat_id}")
        
        # Handle Telegram slash commands directly
        if text.startswith("/"):
            self._handle_command(chat_id, text, username)
            return
        
        # Process via AI (Gemini decides which tool to use based on intent)
        if self.ai_callback:
            try:
                reply = self.ai_callback(text, source="telegram", user=username)
                _send_message(chat_id, reply)
                print(f"[{datetime.now()}] Reply sent")
            except Exception as e:
                error_msg = f"❌ Error: {e}"
                _send_message(chat_id, error_msg)
                print(f"[{datetime.now()}] Error: {e}")
    
    def _handle_command(self, chat_id: int, text: str, username: str):
        """Handle Telegram commands."""
        parts = text.split()
        command = parts[0][1:].split("@")[0]
        
        if command == "start":
            welcome = (
                "🤖 *Nexus H1* — Tu Asistente Personal\n\n"
                f"¡Hola {username}! Soy tu asistente de IA.\n\n"
                "Puedes:\n"
                "- Chatear conmigo en lenguaje natural\n"
                "- Pedirme que revise correos, calendario, etc.\n"
                "- *Monitorear tu servidor*: '¿cómo está la pi?'\n"
                "- Enviarme recordatorios o notas\n\n"
                "¡Escribe lo que sea!"
            )
            _send_message(chat_id, welcome, parse_mode="Markdown")
        
        elif command == "status":
            status = "✅ *Nexus H1* is online and ready to assist you."
            _send_message(chat_id, status, parse_mode="Markdown")
        
        elif command == "help":
            help_text = (
                "*Available Commands:*\n"
                "/start — Welcome message\n"
                "/status — Check system status\n"
                "/help — This help\n\n"
                "*Or just chat with me!*\n"
                "Examples:\n"
                "- What's on my calendar today?\n"
                "- Check my unread emails\n"
                "- Remind me to call mom at 5pm"
            )
            _send_message(chat_id, help_text, parse_mode="Markdown")
        
        elif command == "clear":
            if self.ai_callback:
                try:
                    self.ai_callback("/clear", source="telegram", user=username)
                    _send_message(chat_id, "🧠 Memory cleared.")
                except:
                    _send_message(chat_id, "🧠 Memory cleared.")
        
        else:
            _send_message(chat_id, f"Unknown command: /{command}. Type /help for available commands.")
    
    def send_notification(self, text: str):
        """Send notification to all authorized chats."""
        for chat_id in self.authorized_users:
            try:
                _send_message(chat_id, f"🔔 *Notification*\n{text}", parse_mode="Markdown")
            except Exception as e:
                print(f"Failed to send to {chat_id}: {e}")


if __name__ == "__main__":
    bridge = TelegramBridge()
    bridge.start()
    
    print("Telegram bridge running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bridge.stop()
        print("Stopped.")