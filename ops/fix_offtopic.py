#!/usr/bin/env python3
"""Fix Send Off-Topic to not use Load Prompt reference"""

import json
import requests

API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4'

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/4vaEvzlaMrgovhNz',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()

# Find Send Off-Topic and fix it
for node in data['nodes']:
    if node['name'] == 'Send Off-Topic':
        params = node['parameters']['queryParameters']['parameters']
        for p in params:
            if p['name'] == 'instance_id':
                # Use Start node data instead of Load Prompt
                p['value'] = "={{ $('Start').first().json.instance_id }}"
                print('Fixed instance_id')
            if p['name'] == 'number':
                # Use Build Off-Topic Response data
                p['value'] = "={{ $json.phone }}"
                print('Fixed number')
        break

resp = requests.put(
    'https://n8n.truffles.kz/api/v1/workflows/4vaEvzlaMrgovhNz',
    headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
    json={'name': data['name'], 'nodes': data['nodes'], 'connections': data['connections'], 'settings': data.get('settings', {})}
)
print('Status:', resp.status_code)
