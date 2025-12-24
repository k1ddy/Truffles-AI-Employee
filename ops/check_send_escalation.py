#!/usr/bin/env python3
import json
import requests

API_KEY = 'REDACTED_JWT'

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/fFPEbTNlkBSjo66A',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()

for node in data['nodes']:
    if node['name'] == 'Send Escalation':
        print(json.dumps(node['parameters'], indent=2))
