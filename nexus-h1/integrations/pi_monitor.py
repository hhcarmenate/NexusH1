#!/usr/bin/env python3
"""
Nexus H1 — Pi5 / Private Cloud Monitor
Monitors Ubuntu server via SSH with natural language triggers.
"""

import os
import re
import unicodedata
import paramiko
from typing import Optional, Dict
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# SSH Config from environment
PI_HOST = os.getenv("PI_HOST", "")
PI_USER = os.getenv("PI_USER", "")
PI_PASSWORD = os.getenv("PI_PASSWORD", "")
PI_KEY_PATH = os.getenv("PI_KEY_PATH", "")

# Thresholds for alerts
TEMP_ALERT_C = 75.0
CPU_ALERT_PERCENT = 85.0
DISK_ALERT_PERCENT = 90.0


def _get_ssh_client() -> paramiko.SSHClient:
    """Create and connect SSH client."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    if PI_KEY_PATH and Path(PI_KEY_PATH).exists():
        client.connect(PI_HOST, username=PI_USER, key_filename=PI_KEY_PATH, timeout=10)
    elif PI_PASSWORD:
        client.connect(PI_HOST, username=PI_USER, password=PI_PASSWORD, timeout=10)
    else:
        raise ValueError("No SSH credentials configured. Set PI_HOST, PI_USER, and PI_PASSWORD or PI_KEY_PATH in .env")
    
    return client


def _run_command(cmd: str) -> str:
    """Execute command via SSH and return output."""
    client = _get_ssh_client()
    try:
        stdin, stdout, stderr = client.exec_command(cmd)
        output = stdout.read().decode("utf-8", errors="replace").strip()
        error = stderr.read().decode("utf-8", errors="replace").strip()
        if error and not output:
            return f"Error: {error}"
        return output
    finally:
        client.close()


def get_system_status() -> Dict[str, str]:
    """Get comprehensive system status."""
    status = {}
    
    # Uptime
    try:
        uptime = _run_command("uptime -p")
        status["uptime"] = uptime or "Unknown"
    except Exception as e:
        status["uptime"] = f"Error: {e}"
    
    # CPU Load
    try:
        load = _run_command("cat /proc/loadavg | awk '{print $1, $2, $3}'")
        status["cpu_load"] = load or "N/A"
    except Exception as e:
        status["cpu_load"] = f"Error: {e}"
    
    # CPU Usage
    try:
        cpu = _run_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1")
        status["cpu_percent"] = f"{cpu}%" if cpu else "N/A"
    except Exception as e:
        status["cpu_percent"] = f"Error: {e}"
    
    # Memory
    try:
        mem = _run_command("free -h | awk '/^Mem:/ {print $3 \" / \" $2 \" (\" $3/$2*100 \"%)\"}'")
        status["memory"] = mem or "N/A"
    except Exception as e:
        status["memory"] = f"Error: {e}"
    
    # Disk
    try:
        disk = _run_command("df -h / | awk 'NR==2 {print $3 \" / \" $2 \" (\" $5 \" usado)\"}'")
        status["disk"] = disk or "N/A"
    except Exception as e:
        status["disk"] = f"Error: {e}"
    
    # Temperature (Raspberry Pi specific)
    try:
        temp = _run_command("vcgencmd measure_temp 2>/dev/null || sensors 2>/dev/null | grep 'temp1' | head -1 || echo 'N/A'")
        status["temperature"] = temp or "N/A"
    except Exception as e:
        status["temperature"] = f"Error: {e}"
    
    # Network
    try:
        net = _run_command("ip -s link show | grep -E '(eth|wlan)' -A 5 | head -10")
        status["network"] = net or "N/A"
    except Exception as e:
        status["network"] = f"Error: {e}"
    
    # Docker (if running)
    try:
        docker = _run_command("docker ps --format 'table {{.Names}}\\t{{.Status}}' 2>/dev/null || echo 'Docker no disponible'")
        if not docker or docker == "Docker no disponible":
            status["docker"] = "Docker no disponible"
        else:
            status["docker"] = docker
    except Exception as e:
        status["docker"] = f"Error: {e}"
    
    return status


def check_alerts(status: Dict[str, str]) -> list:
    """Check if any metric is in alert state."""
    alerts = []
    
    # Temperature alert
    temp_str = status.get("temperature", "")
    if "temp=" in temp_str:
        try:
            temp_val = float(temp_str.split("temp=")[1].split("'")[0])
            if temp_val > TEMP_ALERT_C:
                alerts.append(f"🌡️ Temperatura ALTA: {temp_val}°C (umbral: {TEMP_ALERT_C}°C)")
        except:
            pass
    
    # CPU alert
    cpu_str = status.get("cpu_percent", "")
    if "%" in cpu_str:
        try:
            cpu_val = float(cpu_str.replace("%", ""))
            if cpu_val > CPU_ALERT_PERCENT:
                alerts.append(f"🔥 CPU ALTA: {cpu_val}% (umbral: {CPU_ALERT_PERCENT}%)")
        except:
            pass
    
    # Disk alert
    disk_str = status.get("disk", "")
    if "%" in disk_str:
        try:
            disk_val = float(disk_str.split("(")[1].split("%")[0])
            if disk_val > DISK_ALERT_PERCENT:
                alerts.append(f"💾 Disco LLENO: {disk_val}% usado (umbral: {DISK_ALERT_PERCENT}%)")
        except:
            pass
    
    return alerts


def format_status_telegram(status: Dict[str, str], alerts: list = None) -> str:
    """Format status as Telegram message in Spanish."""
    lines = [
        "🖥️ *Estado del Private Cloud*",
        f"📅 `{datetime.now().strftime('%H:%M %d/%m/%Y')}`",
        "",
        f"⏱️ *Uptime:* `{status.get('uptime', 'N/A')}`",
        f"🔧 *CPU Load:* `{status.get('cpu_load', 'N/A')}`",
        f"🔥 *CPU Uso:* `{status.get('cpu_percent', 'N/A')}`",
        f"🧠 *Memoria:* `{status.get('memory', 'N/A')}`",
        f"💾 *Disco:* `{status.get('disk', 'N/A')}`",
        f"🌡️ *Temperatura:* `{status.get('temperature', 'N/A')}`",
    ]
    
    # Docker status
    docker = status.get("docker", "")
    if docker and "no disponible" not in docker.lower() and "error" not in docker.lower():
        lines.append("")
        lines.append("🐳 *Containers Docker:*")
        docker_lines = docker.strip().splitlines()
        if len(docker_lines) > 1:
            for line in docker_lines[1:]:  # Skip header
                if line.strip():
                    lines.append(f"`{line}`")
        else:
            lines.append("_No hay containers en ejecución_")
    elif "no disponible" in docker.lower():
        lines.append("")
        lines.append("🐳 *Docker:* _No disponible_")
    
    # Alerts
    if alerts:
        lines.append("")
        lines.append("⚠️ *ALERTAS:*")
        for alert in alerts:
            lines.append(alert)
    elif alerts is not None:
        lines.append("")
        lines.append("✅ *Todo normal*")
    
    return "\n".join(lines)


def get_quick_status() -> str:
    """Get quick one-line status."""
    try:
        status = get_system_status()
        alerts = check_alerts(status)
        return format_status_telegram(status, alerts)
    except Exception as e:
        return f"❌ *Error de conexion*\nNo puedo conectar al servidor.\n`{e}`"


# Natural language triggers (Spanish + English)
# Note: text is normalized (accents removed) before matching
MONITOR_TRIGGERS = [
    # Spanish - server/pi/cloud/nextcloud
    r"\b(como esta|como va|estado de|revisa|chequea|monitorea|verifica)\b.*\b(pi|server|servidor|cloud|raspberry|rpi|ubuntu|servidor|nextcloud|next cloud)\b",
    r"\b(pi|server|servidor|cloud|raspberry|rpi|ubuntu|servidor|nextcloud|next cloud)\b.*\b(como esta|como va|estado|revisa|chequea)\b",
    r"\b(estado del sistema|estado del servidor|estado de la pi|estado de la nube|estado de nextcloud)\b",
    r"\b(que tal|como andan?)\b.*\b(los servidores|el servidor|la pi|los containers|el cloud|nextcloud)\b",
    r"\b(dame|muestra)\b.*\b(estadisticas|metricas|stats)\b.*\b(servidor|pi|cloud|nextcloud)\b",
    r"\b(estado|status)\b.*\b(servidor|server|pi|cloud|raspberry|nextcloud|docker)\b",
    r"\b(servidor|server|pi|nextcloud)\b.*\b(estado|status|como esta|como andas)\b",
    r"\b(nextcloud|docker|containers)\b.*\b(estado|status|como esta|como van)\b",
    # English
    r"\b(how is|check|monitor|status of)\b.*\b(pi|server|cloud|raspberry|nextcloud)\b",
    r"\b(pi|server|cloud|raspberry|nextcloud)\b.*\b(status|health|how is)\b",
    r"\b(nextcloud|docker|containers)\b.*\b(status|health|how is)\b",
]


def _normalize_text(text: str) -> str:
    """Remove accents for better regex matching."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )


def is_monitor_request(text: str) -> bool:
    """Check if text is a monitor request using natural language."""
    text_lower = text.lower()
    text_normalized = _normalize_text(text_lower)
    for pattern in MONITOR_TRIGGERS:
        if re.search(pattern, text_lower) or re.search(pattern, text_normalized):
            return True
    return False


def send_periodic_report(telegram_bridge=None):
    """Send periodic Pi monitor report via Telegram."""
    try:
        status = get_system_status()
        alerts = check_alerts(status)
        
        # Only send if there are alerts, or it's a scheduled report
        if alerts:
            msg = format_status_telegram(status, alerts)
            msg = "⚠️ *ALERTA detectada en tu servidor*\n\n" + msg
        else:
            msg = format_status_telegram(status, [])
            msg = "📊 *Reporte periodico del servidor*\n\n" + msg
        
        # Try to send via Telegram bridge
        if telegram_bridge:
            telegram_bridge.send_notification(msg)
        else:
            # Fallback: send directly
            try:
                from integrations.telegram import send_message
                chat_id_file = Path("secrets/telegram_chat_id.txt")
                if chat_id_file.exists():
                    chat_id = chat_id_file.read_text().strip()
                    send_message(chat_id, msg, parse_mode="Markdown")
            except Exception as e:
                print(f"[PI MONITOR] Failed to send Telegram: {e}")
                
    except Exception as e:
        print(f"[PI MONITOR] Periodic report failed: {e}")


def run_periodic_monitor(telegram_bridge=None, interval_minutes=30):
    """Run periodic monitoring in background thread."""
    import time
    import threading
    
    def monitor_loop():
        print(f"[PI MONITOR] Periodic monitor started (every {interval_minutes} min)")
        while True:
            try:
                time.sleep(interval_minutes * 60)
                print(f"[{datetime.now()}] Running periodic Pi monitor...")
                send_periodic_report(telegram_bridge)
            except Exception as e:
                print(f"[PI MONITOR] Monitor loop error: {e}")
    
    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    print(get_quick_status())
