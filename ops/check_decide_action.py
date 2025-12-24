#!/usr/bin/env python3
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "7jGZrdbaAAvtTnQX"

url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

for node in workflow['nodes']:
    if node['name'] == 'Decide Action':
        print("=== DECIDE ACTION CODE ===")
        code = node.get('parameters', {}).get('jsCode', '')
        print(code)
