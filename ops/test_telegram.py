#!/usr/bin/env python3
"""Test Telegram alert"""
import requests

TELEGRAM_TOKEN = "REDACTED_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "1969855532"

url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
r = requests.post(url, data={
    "chat_id": TELEGRAM_CHAT_ID,
    "text": "✅ Health check test - система мониторинга работает"
})
print(f"Status: {r.status_code}")
print(f"Response: {r.text[:200]}")
