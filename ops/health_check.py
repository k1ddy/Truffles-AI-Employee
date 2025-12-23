#!/usr/bin/env python3
"""
Health check for Truffles infrastructure.
Sends Telegram alert if any service is down.
Run via cron every 5 minutes.
"""
import json
import os
import subprocess
import requests
import sys
from datetime import datetime

# Config
TELEGRAM_TOKEN = "8045341599:AAGY1vnqoebErB7Ki5iAqHusgLqf9WwA5m4"
TELEGRAM_CHAT_ID = "1969855532"
DOCKER_NETWORK = os.environ.get("TRUFFLES_DOCKER_NETWORK", "truffles_internal-net")
QDRANT_API_KEY = os.environ.get("QDRANT__SERVICE__API_KEY") or os.environ.get("QDRANT_API_KEY") or "Iddqd777!"
BGE_PORT = int(os.environ.get("BGE_M3_PORT", "80"))
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
N8N_URL = os.environ.get("N8N_HEALTH_URL", "https://n8n.truffles.kz/")

def _get_container_ip(container_name: str) -> str | None:
    try:
        output = subprocess.check_output(["docker", "inspect", container_name], text=True)
        data = json.loads(output)[0]
        networks = data.get("NetworkSettings", {}).get("Networks", {})
        if DOCKER_NETWORK in networks:
            ip = networks[DOCKER_NETWORK].get("IPAddress")
            if ip:
                return ip
        for net in networks.values():
            ip = net.get("IPAddress")
            if ip:
                return ip
    except Exception:
        return None
    return None


def _service_url(container_name: str, port: int, path: str) -> callable:
    def _build():
        ip = _get_container_ip(container_name)
        if not ip:
            return None
        path_value = path if path.startswith("/") else f"/{path}"
        return f"http://{ip}:{port}{path_value}"

    return _build


SERVICES = [
    {
        "name": "BGE-M3",
        "url": _service_url("bge-m3", BGE_PORT, "/"),
        "timeout": 10,
        "check": lambda r: r.status_code == 200,
    },
    {
        "name": "Qdrant",
        "url": _service_url("truffles_qdrant_1", QDRANT_PORT, "/collections/truffles_knowledge"),
        "timeout": 10,
        "headers": {"api-key": QDRANT_API_KEY},
        "check": lambda r: r.status_code == 200,
    },
    {
        "name": "n8n",
        "url": lambda: N8N_URL,
        "timeout": 10,
        "check": lambda r: r.status_code in {200, 301, 302, 401, 403},
    },
]

def send_telegram(message):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Failed to send Telegram: {e}")

def check_service(service):
    """Check single service, return (ok, error_message)"""
    try:
        url = service["url"]() if callable(service["url"]) else service["url"]
        if not url:
            return False, "Container IP not found"
        r = requests.get(
            url,
            timeout=service.get("timeout", 10),
            headers=service.get("headers", {})
        )
        if service["check"](r):
            return True, None
        else:
            return False, f"Unexpected response: {r.status_code}"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, "Connection refused"
    except Exception as e:
        return False, str(e)

def main():
    errors = []
    
    for service in SERVICES:
        ok, error = check_service(service)
        if not ok:
            errors.append(f"❌ <b>{service['name']}</b>: {error}")
            print(f"FAIL: {service['name']} - {error}")
        else:
            print(f"OK: {service['name']}")
    
    if errors:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        message = f"🚨 <b>ALERT</b> [{timestamp}]\n\n" + "\n".join(errors)
        send_telegram(message)
        sys.exit(1)
    else:
        print("All services OK")
        sys.exit(0)

if __name__ == "__main__":
    main()
