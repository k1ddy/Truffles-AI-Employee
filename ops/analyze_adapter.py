#!/usr/bin/env python3
"""Analyze 8_Telegram_Adapter - find all node references"""

import json
import requests
import re

API_KEY = 'REDACTED_JWT'

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/fFPEbTNlkBSjo66A',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()

print("=== NODES ===")
node_names = [n['name'] for n in data['nodes']]
for name in node_names:
    print(f"  - {name}")

print("\n=== CONNECTIONS ===")
for src, conn in data['connections'].items():
    targets = []
    for outputs in conn.get('main', []):
        for t in outputs:
            targets.append(t['node'])
    print(f"  {src} -> {targets}")

print("\n=== REFERENCES TO OTHER NODES ===")
# Find all $('NodeName') references in node parameters
pattern = r"\$\(['\"]([^'\"]+)['\"]\)"

for node in data['nodes']:
    params_str = json.dumps(node.get('parameters', {}))
    refs = re.findall(pattern, params_str)
    if refs:
        print(f"\n  {node['name']}:")
        for ref in set(refs):
            exists = ref in node_names
            status = "OK" if exists else "MISSING!"
            print(f"    -> {ref} [{status}]")
