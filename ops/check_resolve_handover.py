#!/usr/bin/env python3
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

for node in workflow['nodes']:
    if node['name'] in ['Resolve Handover', 'Unmute Bot', 'Take Handover']:
        print(f"=== {node['name']} ===")
        query = node.get('parameters', {}).get('query', '')
        print(query)
        print()
