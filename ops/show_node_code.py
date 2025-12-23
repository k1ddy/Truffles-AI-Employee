#!/usr/bin/env python3
"""Show code of Get Topic ID node"""

import json
import requests

API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4'

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
