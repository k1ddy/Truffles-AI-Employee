#!/usr/bin/env python3
"""Check Parse Callback logic"""

import json
import requests

API_KEY = 'REDACTED_JWT'

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/HQOWuMDIBPphC86v',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()

for node in data['nodes']:
    if node['name'] == 'Parse Callback':
        print('=== Parse Callback ===')
        code = node['parameters'].get('jsCode', '')
        print(code)
        break
