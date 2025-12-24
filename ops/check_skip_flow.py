#!/usr/bin/env python3
"""Check skip flow in detail"""

import json
import requests

API_KEY = 'REDACTED_JWT'

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/HQOWuMDIBPphC86v',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()

# Find Skip Response node
for node in data['nodes']:
    if node['name'] == 'Skip Response':
        print('=== Skip Response ===')
        print(json.dumps(node['parameters'], indent=2))
        break

# Check what comes after Skip Response
connections = data['connections']
print('\n=== Skip Response connections ===')
if 'Skip Response' in connections:
    for i, outputs in enumerate(connections['Skip Response']['main']):
        targets = [o['node'] for o in outputs] if outputs else ['(none)']
        print(f'Output {i}: {targets}')
else:
    print('No connections from Skip Response!')

# Check Answer Callback
print('\n=== Answer Callback (used by Take/Skip) ===')
for node in data['nodes']:
    if node['name'] == 'Answer Callback':
        print(json.dumps(node['parameters'], indent=2)[:500])
        break
