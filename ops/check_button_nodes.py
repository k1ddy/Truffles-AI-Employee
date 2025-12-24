#!/usr/bin/env python3
"""Check Update Buttons and Remove Buttons Resolve"""
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
    if node['name'] in ['Update Buttons', 'Remove Buttons Resolve', 'Action Switch']:
        print(f"=== {node['name']} ===")
        print(json.dumps(node['parameters'], indent=2, ensure_ascii=False)[:800])
        print()
