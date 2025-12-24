#!/usr/bin/env python3
"""Check callback workflow structure"""

import json
import requests

API_KEY = 'REDACTED_JWT'

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/HQOWuMDIBPphC86v',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()

# Check Action Switch rules
for node in data['nodes']:
    if node['name'] == 'Action Switch':
        rules = node['parameters']['rules']['values']
        print('Action Switch rules:')
        for i, rule in enumerate(rules):
            conditions = rule.get('conditions', {}).get('conditions', [])
            for cond in conditions:
                rv = cond.get('rightValue', '?')
                print(f'  [{i}] {rv}')
        break

# Check if answered nodes exist
print('\nNodes with "answered":')
for node in data['nodes']:
    if 'answered' in node['name'].lower():
        print(f'  {node["name"]}')

# Check connections from Action Switch
print('\nAction Switch connections:')
conns = data['connections'].get('Action Switch', {}).get('main', [])
for i, outputs in enumerate(conns):
    targets = [o['node'] for o in outputs] if outputs else ['(none)']
    print(f'  Output [{i}]: {targets}')
