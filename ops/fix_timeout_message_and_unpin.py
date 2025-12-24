#!/usr/bin/env python3
"""
1. Fix timeout message to be more helpful
2. Fix unpin on auto-close to use telegram_message_id from handover
"""

import json
import requests

API_KEY = 'REDACTED_JWT'

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/ZRcuYYCv1o9B0MyY',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()
nodes = data['nodes']
connections = data['connections']

print("=== Fixing 10_Handover_Monitor ===")

# 1. Update Notify Client message
for node in nodes:
    if node['name'] == 'Notify Client':
        params = node['parameters'].get('queryParameters', {}).get('parameters', [])
        for p in params:
            if p['name'] == 'text':
                old_text = p['value']
                new_text = "К сожалению, менеджеры сейчас недоступны. Напишите 'менеджер' чтобы создать новую заявку, или задайте вопрос — я постараюсь помочь."
                p['value'] = new_text
                print(f"Updated Notify Client message")
                print(f"  Old: {old_text}")
                print(f"  New: {new_text}")
        break

# 2. Fix Unpin Auto-close to use telegram_message_id from Load Active Handovers
for node in nodes:
    if node['name'] == 'Unpin Auto-close':
        params = node['parameters']['bodyParameters']['parameters']
        for p in params:
            if p['name'] == 'message_id':
                old_val = p['value']
                # Use telegram_message_id from the handover data
                p['value'] = "={{ $json.telegram_message_id }}"
                print(f"Updated Unpin Auto-close message_id")
                print(f"  Old: {old_val}")
                print(f"  New: {{ $json.telegram_message_id }}")
        break

# 3. Verify Load Active Handovers includes telegram_message_id
for node in nodes:
    if node['name'] == 'Load Active Handovers':
        query = node['parameters'].get('query', '')
        if 'telegram_message_id' in query:
            print("✓ Load Active Handovers already includes telegram_message_id")
        else:
            print("⚠ Need to add telegram_message_id to Load Active Handovers")
        break

# Save
resp = requests.put(
    'https://n8n.truffles.kz/api/v1/workflows/ZRcuYYCv1o9B0MyY',
    headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
    json={'name': data['name'], 'nodes': nodes, 'connections': connections, 'settings': data.get('settings', {})}
)
print(f"\nStatus: {resp.status_code}")
