#!/usr/bin/env python3
"""Check and fully restore 8_Telegram_Adapter from local file"""

import json
import requests

API_KEY = 'REDACTED_JWT'

# Get current state
resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows',
    headers={'X-N8N-API-KEY': API_KEY}
)
adapter_id = None
for w in resp.json()['data']:
    if '8_Telegram_Adapter' in w['name']:
        adapter_id = w['id']
        break

if not adapter_id:
    print("ERROR: 8_Telegram_Adapter not found")
    exit(1)

print(f"Found adapter: {adapter_id}")

# Get current workflow
resp = requests.get(
    f'https://n8n.truffles.kz/api/v1/workflows/{adapter_id}',
    headers={'X-N8N-API-KEY': API_KEY}
)
current = resp.json()
print(f"Current nodes: {[n['name'] for n in current['nodes']]}")

# Load the ORIGINAL workflow from local file
with open('/home/zhan/truffles/workflow/8_Telegram_Adapter.json') as f:
    original = json.load(f)

print(f"Original nodes: {[n['name'] for n in original['nodes']]}")

# Use original but add [Решено] button
for node in original['nodes']:
    if node['name'] == 'Send Escalation':
        params = node['parameters']['bodyParameters']['parameters']
        for p in params:
            if p['name'] == 'reply_markup':
                p['value'] = '={"inline_keyboard":[[{"text":"Беру ✋","callback_data":"take_{{ $json.handover_id }}"},{"text":"Решено ✅","callback_data":"resolve_{{ $json.handover_id }}"},{"text":"Не могу ❌","callback_data":"skip_{{ $json.handover_id }}"}]]}'
                print("Added [Решено] button")
        break

# Update
resp = requests.put(
    f'https://n8n.truffles.kz/api/v1/workflows/{adapter_id}',
    headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
    json={
        'name': original['name'],
        'nodes': original['nodes'],
        'connections': original['connections'],
        'settings': original.get('settings', {})
    }
)
print(f"Restore status: {resp.status_code}")

if resp.status_code == 200:
    # Verify
    resp = requests.get(
        f'https://n8n.truffles.kz/api/v1/workflows/{adapter_id}',
        headers={'X-N8N-API-KEY': API_KEY}
    )
    final = resp.json()
    print(f"Final nodes: {[n['name'] for n in final['nodes']]}")
    print(f"Connections from Prepare Data: {final['connections'].get('Prepare Data')}")
