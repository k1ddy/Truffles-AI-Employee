#!/usr/bin/env python3
"""
Health check for Truffles infrastructure.
Sends Telegram alert if any service is down.
Run via cron every 5 minutes.
"""
import requests
import sys
from datetime import datetime

# Config
TELEGRAM_TOKEN = "8045341599:AAGY1vnqoebErB7Ki5iAqHusgLqf9WwA5m4"
TELEGRAM_CHAT_ID = "1969855532"

SERVICES = [
    {
        "name": "BGE-M3",
        "url": "http://172.24.0.8:80/info",
        "timeout": 10,
        "check": lambda r: r.status_code == 200 and "bge-m3" in r.text.lower()
    },
    {
        "name": "Qdrant",
        "url": "http://172.24.0.3:6333/collections/truffles_knowledge",
        "timeout": 10,
        "headers": {"api-key": "Iddqd777!"},
        "check": lambda r: r.status_code == 200
    },
    {
        "name": "n8n",
        "url": "https://n8n.truffles.kz/healthz",
        "timeout": 10,
        "check": lambda r: r.status_code == 200
    }
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
        r = requests.get(
            service["url"],
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
