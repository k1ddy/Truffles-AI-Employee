#!/usr/bin/env python3
"""Check Unpin Escalation configuration"""

import json
import requests

API_KEY = 'REDACTED_JWT'

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/HQOWuMDIBPphC86v',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()

print("=== Unpin Escalation node ===")
for node in data['nodes']:
    if node['name'] == 'Unpin Escalation':
        print(json.dumps(node['parameters'], indent=2, ensure_ascii=False))
        break

print("\n=== Resolve flow connections ===")
connections = data['connections']
flow = ['Resolve Handover', 'Unmute Bot', 'Save Resolved to History', 'Resolve Response', 'Remove Buttons Resolve', 'Unpin Escalation', 'Answer Callback Resolve']
for node_name in flow:
    if node_name in connections:
        targets = []
        for outputs in connections[node_name]['main']:
            for t in outputs:
                targets.append(t['node'])
        print(f"{node_name} -> {targets}")

print("\n=== Parse Callback data (what's available) ===")
for node in data['nodes']:
    if node['name'] == 'Parse Callback':
        code = node['parameters'].get('jsCode', '')
        # Find what fields are returned for callback
        if 'return' in code:
            start = code.find('return')
            end = code.find('];', start)
            print(code[start:end+2])
        break
