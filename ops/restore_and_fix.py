#!/usr/bin/env python3
"""Restore 8_Telegram_Adapter from backup and add only [Решено] button"""

import json
import requests

API_KEY = 'REDACTED_JWT'

# Load backup
with open('/home/zhan/truffles/ops/backup_8_Adapter.json') as f:
    data = json.load(f)

print(f"Loaded backup: {data['name']}")
print(f"Nodes: {len(data['nodes'])}")

# Only change: add [Решено] button to Send Escalation
for node in data['nodes']:
    if node['name'] == 'Send Escalation':
        params = node['parameters']['bodyParameters']['parameters']
        for p in params:
            if p['name'] == 'reply_markup':
                # Add [Решено] button
                p['value'] = '={"inline_keyboard":[[{"text":"Беру ✋","callback_data":"take_{{ $json.handover_id }}"},{"text":"Решено ✅","callback_data":"resolve_{{ $json.handover_id }}"},{"text":"Не могу ❌","callback_data":"skip_{{ $json.handover_id }}"}]]}'
                print("Added [Решено] button")
        break

# Update workflow
resp = requests.put(
    f"https://n8n.truffles.kz/api/v1/workflows/{data['id']}",
    headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
    json={
        'name': data['name'],
        'nodes': data['nodes'],
        'connections': data['connections'],
        'settings': data.get('settings', {})
    }
)
print(f"Status: {resp.status_code}")
