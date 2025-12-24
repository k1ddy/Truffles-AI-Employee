#!/usr/bin/env python3
"""Show code of Get Topic ID node"""

import json
import requests

API_KEY = 'REDACTED_JWT'

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/fFPEbTNlkBSjo66A',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()

print("=== Get Topic ID ===")
for node in data['nodes']:
    if node['name'] == 'Get Topic ID':
        print(json.dumps(node['parameters'], indent=2))

print("\n=== Prepare Data (for comparison) ===")
for node in data['nodes']:
    if node['name'] == 'Prepare Data':
        print(json.dumps(node['parameters'], indent=2))
