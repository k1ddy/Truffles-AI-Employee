#!/usr/bin/env python3
"""Fix the single broken reference in Get Topic ID"""

import json
import requests

API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4'

# Get current workflow
resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/fFPEbTNlkBSjo66A',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()

# Find and fix Get Topic ID
for node in data['nodes']:
    if node['name'] == 'Get Topic ID':
        old_code = node['parameters']['jsCode']
        new_code = old_code.replace("$('Build Message')", "$('Prepare Data')")
        node['parameters']['jsCode'] = new_code
        print("BEFORE:")
        print(old_code[:200])
        print("\nAFTER:")
        print(new_code[:200])
        break

# Update workflow
resp = requests.put(
    'https://n8n.truffles.kz/api/v1/workflows/fFPEbTNlkBSjo66A',
    headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
    json={
        'name': data['name'],
        'nodes': data['nodes'],
        'connections': data['connections'],
        'settings': data.get('settings', {})
    }
)
print(f"\nStatus: {resp.status_code}")
