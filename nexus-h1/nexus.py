#!/usr/bin/env python3
"""
Nexus H1 — Main Orchestrator
Coordinates all integrations and handles the assistant logic.
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Ensure integrations are importable
sys.path.insert(0, str(Path(__file__).parent))

class NexusH1:
    """Main Nexus H1 Assistant Class."""
    
    def __init__(self):
        self.name = "Nexus H1"
        self.version = "0.1.0"
        self.user_name = "Henry"
        self.integrations = {}
        self.memory_path = Path("memory")
        self.memory_path.mkdir(exist_ok=True)
        
        # AI instance
        self.ai = None
        self.ai_provider = "gemini"  # Default to Gemini (free)
        
        # Load config
        self._load_config()
        
    def _load_config(self):
        """Load configuration from config.yaml."""
        import yaml
        config_path = Path("config.yaml")
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
                self.user_name = config.get("user", {}).get("name", "Henry")
                self.timezone = config.get("user", {}).get("timezone", "America/New_York")
    
    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}\n"
        print(log_line.strip())
        
        # Append to daily log
        log_file = self.memory_path / f"{datetime.now().strftime('%Y-%m-%d')}.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line)
    
    def init_integration(self, name: str) -> bool:
        """Initialize an integration by name."""
        try:
            if name == "gmail":
                from integrations.gmail import get_unread_count
                self.integrations["gmail"] = {"status": "ready", "module": "gmail"}
                self.log("Gmail integration ready")
                return True
                
            elif name == "whatsapp":
                from integrations.whatsapp import start as wa_start
                wa_start()
                self.integrations["whatsapp"] = {"status": "ready", "module": "whatsapp"}
                self.log("WhatsApp integration ready")
                return True
                
            elif name == "telegram":
                self.integrations["telegram"] = {"status": "ready", "module": "telegram"}
                self.log("Telegram integration ready")
                return True
                
            elif name == "notion":
                from integrations.notion import search
                # Test connection
                search("", page_size=1)
                self.integrations["notion"] = {"status": "ready", "module": "notion"}
                self.log("Notion integration ready")
                return True
                
            elif name == "calendar":
                from integrations.google_calendar import get_todays_events
                self.integrations["calendar"] = {"status": "ready", "module": "calendar"}
                self.log("Calendar integration ready")
                return True
                
            elif name == "voice":
                from integrations.voice import init_voice
                init_voice()
                self.integrations["voice"] = {"status": "ready", "module": "voice"}
                self.log("Voice integration ready")
                return True
                
        except Exception as e:
            self.log(f"Failed to initialize {name}: {e}", "ERROR")
            self.integrations[name] = {"status": "error", "error": str(e)}
            return False
        
        return False
    
    def init_all(self):
        """Initialize all configured integrations."""
        self.log("Initializing Nexus H1...")
        
        integrations = ["gmail", "whatsapp", "telegram", "notion", "calendar", "voice"]
        for name in integrations:
            self.init_integration(name)
        
        # Initialize AI
        self._init_ai()
        
        ready = sum(1 for v in self.integrations.values() if v.get("status") == "ready")
        self.log(f"Initialized {ready}/{len(integrations)} integrations")
    
    def _init_ai(self):
        """Initialize AI conversational module."""
        try:
            if self.ai_provider == "gemini":
                from integrations.gemini import create_gemini
                self.ai = create_gemini(session_id="main")
                self.integrations["ai"] = {"status": "ready", "module": "gemini"}
                self.log("Gemini AI conversational module ready")
            else:
                from integrations.ai import create_ai
                self.ai = create_ai(session_id="main")
                self.integrations["ai"] = {"status": "ready", "module": "openai"}
                self.log("OpenAI AI conversational module ready")
        except Exception as e:
            self.log(f"AI initialization failed: {e}", "ERROR")
            self.integrations["ai"] = {"status": "error", "error": str(e)}
    
    def status(self) -> Dict:
        """Get system status."""
        return {
            "agent": {"name": self.name, "version": self.version},
            "user": self.user_name,
            "time": datetime.now().isoformat(),
            "integrations": self.integrations,
        }
    
    def handle_command(self, command: str, args: List[str]) -> str:
        """Process a command."""
        command = command.lower()
        
        if command in ["hello", "hi", "hey"]:
            return f"Hello {self.user_name}! I'm {self.name}, ready to assist you."
        
        elif command == "status":
            st = self.status()
            ready = [k for k, v in st["integrations"].items() if v.get("status") == "ready"]
            return f"✅ Online. Active integrations: {', '.join(ready) if ready else 'None'}"
        
        elif command == "help":
            return """Available commands:
- hello / hi / hey — Greeting
- status — System status
- email [query] — Check emails (Gmail)
- calendar [today/upcoming] — Calendar events
- remind <text> — Quick reminder
- send <to> <message> — Send WhatsApp message
- note <text> — Add note to Notion
- speak <text> — Text to speech
- chat — Enter AI chat mode (local)
- telegram — Start Telegram AI bridge
- help — This message

Or just type anything to talk with the AI!"""
        
        elif command == "email":
            if "gmail" not in self.integrations or self.integrations["gmail"].get("status") != "ready":
                return "❌ Gmail not configured. Check gmail_setup.md"
            try:
                from integrations.gmail import list_messages
                query = " ".join(args) if args else "is:unread"
                emails = list_messages(max_results=5, query=query)
                if not emails:
                    return "📭 No emails found."
                lines = [f"📧 {e['subject']} (from: {e['from']})" for e in emails]
                return "Recent emails:\n" + "\n".join(lines)
            except Exception as e:
                return f"❌ Error: {e}"
        
        elif command == "calendar":
            if "calendar" not in self.integrations or self.integrations["calendar"].get("status") != "ready":
                return "❌ Calendar not configured. Check google_calendar_setup.md"
            try:
                from integrations.google_calendar import get_todays_events, get_upcoming_events
                subcmd = args[0] if args else "today"
                if subcmd == "today":
                    events = get_todays_events()
                    if not events:
                        return "📅 No events today."
                    lines = [f"• {e['summary']} — {e['start']}" for e in events]
                    return "Today's events:\n" + "\n".join(lines)
                else:
                    days = int(subcmd) if subcmd.isdigit() else 7
                    events = get_upcoming_events(days=days)
                    return f"Upcoming {days} days: {len(events)} events"
            except Exception as e:
                return f"❌ Error: {e}"
        
        elif command == "remind":
            if not args:
                return "Usage: remind <text>"
            try:
                from integrations.google_calendar import create_quick_reminder
                text = " ".join(args)
                result = create_quick_reminder(text)
                return f"⏰ Reminder set: {text}"
            except Exception as e:
                return f"❌ Error: {e}"
        
        elif command == "send":
            if len(args) < 2:
                return "Usage: send <phone> <message>"
            try:
                from integrations.whatsapp import send
                phone = args[0]
                message = " ".join(args[1:])
                send(phone, message)
                return f"📤 Sent to {phone}: {message}"
            except Exception as e:
                return f"❌ Error: {e}"
        
        elif command == "note":
            if not args:
                return "Usage: note <text>"
            return "📝 Notion integration: Use notion.py directly for now."
        
        elif command == "speak":
            if not args:
                return "Usage: speak <text>"
            try:
                from integrations.voice import say
                text = " ".join(args)
                say(text)
                return f"🔊 Speaking: {text}"
            except Exception as e:
                return f"❌ Error: {e}"
        
        else:
            # Try AI conversational response
            if self.ai:
                full_input = " ".join([command] + args)
                return self.ai.chat(full_input)
            else:
                return f"Unknown command: {command}. Type 'help' for available commands."
    
    def interactive(self):
        """Run interactive shell."""
        print(f"\n🤖 {self.name} v{self.version}")
        print(f"Welcome, {self.user_name}! Type 'help' for commands or just chat with me.\n")
        
        while True:
            try:
                user_input = input("Nexus H1> ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "bye"]:
                    print("Goodbye! 👋")
                    break
                
                parts = user_input.split()
                command = parts[0].lower()
                args = parts[1:]
                
                response = self.handle_command(command, args)
                print(response)
                
            except KeyboardInterrupt:
                print("\nGoodbye! 👋")
                break
            except Exception as e:
                self.log(f"Error in interactive mode: {e}", "ERROR")
                print(f"❌ Error: {e}")
    
    async def poll_telegram(self):
        """Start Telegram polling in background."""
        try:
            from integrations.telegram import poll_updates
            await poll_updates()
        except Exception as e:
            self.log(f"Telegram polling error: {e}", "ERROR")
    
    async def poll_whatsapp(self):
        """Poll WhatsApp for new messages."""
        try:
            from integrations.whatsapp import pending
            while True:
                msgs = pending()
                for msg in msgs:
                    self.log(f"WhatsApp from {msg['from']}: {msg['body']}")
                    # Auto-reply logic could go here
                await asyncio.sleep(5)
        except Exception as e:
            self.log(f"WhatsApp polling error: {e}", "ERROR")
    
    async def run_async(self):
        """Run all async tasks."""
        tasks = []
        
        if self.integrations.get("telegram", {}).get("status") == "ready":
            tasks.append(self.poll_telegram())
        
        if self.integrations.get("whatsapp", {}).get("status") == "ready":
            tasks.append(self.poll_whatsapp())
        
        if tasks:
            await asyncio.gather(*tasks)
        else:
            self.log("No async integrations to poll")
    
    def chat_mode(self):
        """Run in pure chat mode with AI."""
        print(f"\n🤖 {self.name} AI Chat Mode")
        print("Type 'exit' to quit, 'clear' to reset memory.\n")
        
        if not self.ai:
            self._init_ai()
        
        while True:
            try:
                user_input = input("You> ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "bye"]:
                    print("Nexus H1> Goodbye! 👋")
                    break
                if user_input.lower() == "clear":
                    if self.ai:
                        self.ai.clear_memory()
                    print("Nexus H1> Conversation memory cleared.")
                    continue
                
                response = self.ai.chat(user_input)
                print(f"Nexus H1> {response}")
                
            except KeyboardInterrupt:
                print("\nNexus H1> Goodbye! 👋")
                break
            except Exception as e:
                self.log(f"Chat error: {e}", "ERROR")
                print(f"❌ Error: {e}")
    
    def run_telegram_ai(self):
        """Run Telegram bridge with AI in background."""
        from integrations.telegram_bridge import TelegramBridge
        
        if not self.ai:
            self._init_ai()
        
        def ai_callback(message: str, source: str = "telegram", user: str = "") -> str:
            """Process message via AI and return response."""
            # Add context about source
            context = f"[Message from {user} via Telegram] "
            full_message = context + message
            return self.ai.chat(full_message)
        
        bridge = TelegramBridge(ai_callback=ai_callback)
        bridge.start(interval=2)
        
        self.log("Telegram AI bridge started. Messages will be processed by Gemini.")
        print("\n[Nexus H1 Telegram AI Bridge]")
        print("Send messages to @nexusH1bot on Telegram")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            bridge.stop()
            self.log("Telegram bridge stopped")
    
    def run(self, mode: str = "interactive"):
        """Run Nexus H1 in specified mode."""
        if mode == "interactive":
            self.interactive()
        elif mode == "chat":
            self.chat_mode()
        elif mode == "telegram":
            self.run_telegram_ai()
        elif mode == "daemon":
            self.log("Starting daemon mode...")
            try:
                asyncio.run(self.run_async())
            except KeyboardInterrupt:
                self.log("Daemon stopped")
        elif mode == "status":
            print(json.dumps(self.status(), indent=2))
        else:
            print(f"Unknown mode: {mode}")


def main():
    parser = argparse.ArgumentParser(description="Nexus H1 Personal Assistant")
    parser.add_argument("mode", nargs="?", default="interactive", 
                       choices=["interactive", "chat", "telegram", "daemon", "status", "init"],
                       help="Run mode")
    parser.add_argument("--init", action="store_true", 
                       help="Initialize all integrations on startup")
    
    args = parser.parse_args()
    
    nexus = NexusH1()
    
    if args.init or args.mode == "init":
        nexus.init_all()
        if args.mode == "init":
            print(json.dumps(nexus.status(), indent=2))
            return
    
    nexus.run(args.mode)


if __name__ == "__main__":
    main()
