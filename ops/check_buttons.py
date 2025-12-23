#!/usr/bin/env python3
"""Check what buttons are created during escalation"""

import json
import requests

API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4'

# Check 8_Telegram_Adapter for button markup
resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/fFPEbTNlHBU92e4p',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()

print('=== 8_Telegram_Adapter nodes with buttons ===')
for node in data.get('nodes', []):
    params = node.get('parameters', {})
    params_str = json.dumps(params)
    if 'inline_keyboard' in params_str or 'callback_data' in params_str:
        print(f"\nNode: {node.get('name')}")
        print(params_str[:500])
