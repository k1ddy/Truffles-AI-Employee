#!/usr/bin/env python3
"""Remove broken nodes and fix connections"""

import json
import requests

API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4'

adapter_id = 'fFPEbTNlkBSjo66A'

resp = requests.get(
    f'https://n8n.truffles.kz/api/v1/workflows/{adapter_id}',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()

# Remove broken nodes
broken_nodes = ['Check Previous Timeout', 'Build Message']
data['nodes'] = [n for n in data['nodes'] if n['name'] not in broken_nodes]
print(f"Removed: {broken_nodes}")
print(f"Remaining nodes: {[n['name'] for n in data['nodes']]}")

# Fix connections - Prepare Data should go to Get Existing Topic
data['connections']['Prepare Data'] = {
    "main": [[{"node": "Get Existing Topic", "type": "main", "index": 0}]]
}

# Remove broken connections
for broken in broken_nodes:
    if broken in data['connections']:
        del data['connections'][broken]

print(f"Fixed: Prepare Data -> Get Existing Topic")

# Add [Решено] button
for node in data['nodes']:
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
        'name': data['name'],
        'nodes': data['nodes'],
        'connections': data['connections'],
        'settings': data.get('settings', {})
    }
)
print(f"Status: {resp.status_code}")
