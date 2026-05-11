#!/usr/bin/env python3
"""
Nexus H1 — WhatsApp Integration Module
Python wrapper around whatsapp-web.js Node.js process
"""

import json
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional

JS_PATH = Path(__file__).parent / "whatsapp.js"
NODE_CMD = "node"


class WhatsAppClient:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self._buffer = ""

    def start(self):
        """Start the WhatsApp client process."""
        self.process = subprocess.Popen(
            [NODE_CMD, str(JS_PATH)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        # Wait for ready or QR
        print("Starting WhatsApp client...")
        print("Scan QR code from secrets/whatsapp_qr.txt if prompted")

    def stop(self):
        """Stop the client."""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None

    def _send_cmd(self, cmd: Dict) -> List[Dict]:
        """Send command and collect response lines."""
        if not self.process:
            raise RuntimeError("WhatsApp client not started")
        
        self.process.stdin.write(json.dumps(cmd) + "\n")
        self.process.stdin.flush()
        
        responses = []
        # Wait up to 10 seconds for response
        for _ in range(100):
            line = self.process.stdout.readline().strip()
            if line:
                responses.append(line)
                if line.startswith("SENT") or line.startswith("CHATS") or line.startswith("MESSAGES") or line.startswith("STATUS") or line.startswith("QUEUE"):
                    break
            time.sleep(0.1)
        return responses

    def send_message(self, to: str, message: str) -> str:
        """Send text message. 'to' should be phone number with country code."""
        responses = self._send_cmd({"action": "send", "to": to, "message": message})
        for r in responses:
            if r.startswith("SENT"):
                return r
        return "ERROR"

    def get_chats(self) -> List[Dict]:
        """Get recent chats."""
        responses = self._send_cmd({"action": "get_chats"})
        for r in responses:
            if r.startswith("CHATS"):
                _, data = r.split(" ", 1)
                return json.loads(data)
        return []

    def get_messages(self, chat_id: str, limit: int = 50) -> List[Dict]:
        """Get messages from a chat."""
        responses = self._send_cmd({"action": "get_messages", "chatId": chat_id, "limit": limit})
        for r in responses:
            if r.startswith("MESSAGES"):
                _, data = r.split(" ", 1)
                return json.loads(data)
        return []

    def get_status(self) -> Dict:
        """Get client status."""
        responses = self._send_cmd({"action": "status"})
        for r in responses:
            if r.startswith("STATUS"):
                _, data = r.split(" ", 1)
                return json.loads(data)
        return {"ready": False}

    def get_pending_messages(self) -> List[Dict]:
        """Get and clear pending incoming messages."""
        responses = self._send_cmd({"action": "get_queue"})
        for r in responses:
            if r.startswith("QUEUE"):
                _, data = r.split(" ", 1)
                return json.loads(data)
        return []


# Convenience functions for direct usage
_client = None

def start():
    global _client
    _client = WhatsAppClient()
    _client.start()

def stop():
    global _client
    if _client:
        _client.stop()
        _client = None

def send(to: str, message: str) -> str:
    if not _client:
        raise RuntimeError("WhatsApp not started. Call start() first.")
    return _client.send_message(to, message)

def chats() -> List[Dict]:
    if not _client:
        raise RuntimeError("WhatsApp not started. Call start() first.")
    return _client.get_chats()

def messages(chat_id: str, limit: int = 50) -> List[Dict]:
    if not _client:
        raise RuntimeError("WhatsApp not started. Call start() first.")
    return _client.get_messages(chat_id, limit)

def pending() -> List[Dict]:
    if not _client:
        raise RuntimeError("WhatsApp not started. Call start() first.")
    return _client.get_pending_messages()

def status() -> Dict:
    if not _client:
        return {"ready": False}
    return _client.get_status()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "start":
        start()
        try:
            while True:
                time.sleep(1)
                s = status()
                if s.get("ready"):
                    print("WhatsApp is ready!")
                    break
        except KeyboardInterrupt:
            stop()
    else:
        print("Usage: python whatsapp.py start")
