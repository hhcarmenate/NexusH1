#!/usr/bin/env python3
"""
Nexus H1 — Start Script
Turns on the entire assistant: AI, Telegram, WhatsApp, and all integrations.
"""

import os
import sys
import time
import signal
import threading
from pathlib import Path
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Ensure integrations are importable
sys.path.insert(0, str(Path(__file__).parent))

# Global flag for shutdown
running = True

def log(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
    print(line)
    
    # Append to daily log
    log_dir = Path("memory")
    log_dir.mkdir(exist_ok=True)
    with open(log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global running
    log("Shutdown signal received. Stopping Nexus H1...")
    running = False


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


class NexusH1Daemon:
    """Main daemon that runs all integrations."""
    
    def __init__(self):
        self.ai = None
        self.telegram_bridge = None
        self.whatsapp_bridge = None
        self.threads = []
        self.integrations = {}
        
    def init_ai(self):
        """Initialize AI engine."""
        try:
            from integrations.gemini import create_gemini
            self.ai = create_gemini(session_id="main")
            self.integrations["ai"] = "ready"
            log("AI engine initialized (Gemini)")
            return True
        except Exception as e:
            log(f"AI init failed: {e}", "ERROR")
            self.integrations["ai"] = f"error: {e}"
            return False
    
    def init_telegram(self):
        """Initialize Telegram bridge with AI."""
        try:
            from integrations.telegram_bridge import TelegramBridge
            
            if not self.ai:
                log("AI not ready for Telegram", "WARN")
                return False
            
            def ai_callback(message: str, source: str = "telegram", user: str = "") -> str:
                context = f"[Message from {user} via Telegram] "
                return self.ai.chat(context + message)
            
            self.telegram_bridge = TelegramBridge(ai_callback=ai_callback)
            self.telegram_bridge.start(interval=2)
            self.integrations["telegram"] = "ready"
            log("Telegram bridge started")
            return True
            
        except Exception as e:
            log(f"Telegram init failed: {e}", "ERROR")
            self.integrations["telegram"] = f"error: {e}"
            return False
    
    def init_whatsapp(self):
        """Initialize WhatsApp bridge."""
        try:
            from integrations.whatsapp import start as wa_start
            wa_start()
            self.integrations["whatsapp"] = "ready"
            log("WhatsApp bridge started")
            return True
        except Exception as e:
            log(f"WhatsApp init failed: {e}", "ERROR")
            self.integrations["whatsapp"] = f"error: {e}"
            return False
    
    def init_pi_monitor(self):
        """Initialize Pi5 periodic monitor."""
        try:
            from integrations.pi_monitor import run_periodic_monitor
            self.pi_monitor_thread = run_periodic_monitor(
                telegram_bridge=self.telegram_bridge,
                interval_minutes=30
            )
            self.integrations["pi_monitor"] = "ready"
            log("Pi5 monitor started (30 min interval)")
            return True
        except Exception as e:
            log(f"Pi5 monitor init failed: {e}", "ERROR")
            self.integrations["pi_monitor"] = f"error: {e}"
            return False
    
    def init_all(self):
        """Initialize all components."""
        log("=" * 50)
        log("Starting Nexus H1...")
        log("=" * 50)
        
        # 1. AI Engine
        self.init_ai()
        
        # 2. Telegram
        self.init_telegram()
        
        # 3. Pi5 Monitor
        self.init_pi_monitor()
        
        # 4. WhatsApp (disabled for now - interferes with Telegram)
        # self.init_whatsapp()
        
        log("-" * 50)
        log(f"Status: {sum(1 for v in self.integrations.values() if v == 'ready')}/{len(self.integrations)} ready")
        for name, status in self.integrations.items():
            icon = "OK" if status == "ready" else "FAIL"
            log(f"  [{icon}] {name}: {status}")
        log("=" * 50)
    
    def run(self):
        """Main loop - keep everything alive."""
        self.init_all()
        
        log("Nexus H1 is running. Press Ctrl+C to stop.")
        log("Send messages to @nexusH1bot on Telegram")
        
        global running
        try:
            while running:
                # Check health every 5 seconds
                time.sleep(5)
                
                # Verify Telegram bridge is still running
                if self.telegram_bridge and not self.telegram_bridge.running:
                    log("Telegram bridge stopped unexpectedly. Restarting...", "WARN")
                    self.init_telegram()
                
                # Verify Pi monitor is alive (thread check)
                if hasattr(self, 'pi_monitor_thread') and not self.pi_monitor_thread.is_alive():
                    log("Pi monitor thread stopped. Restarting...", "WARN")
                    self.init_pi_monitor()
                
        except KeyboardInterrupt:
            log("Keyboard interrupt received.")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown."""
        log("Shutting down Nexus H1...")
        
        if self.telegram_bridge:
            self.telegram_bridge.stop()
            log("Telegram bridge stopped")
        
        log("Goodbye!")


def main():
    """Entry point."""
    print("=" * 50)
    print("  NEXUS H1 — Personal Assistant")
    print("  Version 0.1.0")
    print("=" * 50)
    print()
    
    daemon = NexusH1Daemon()
    daemon.run()


if __name__ == "__main__":
    main()
