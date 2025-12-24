#!/usr/bin/env python3
"""Check Prepare Response and Build Context"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"

url = f"https://n8n.truffles.kz/api/v1/workflows/4vaEvzlaMrgovhNz"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

for node in workflow['nodes']:
    if node['name'] in ['Prepare Response', 'Build Context']:
        print(f"=== {node['name']} ===")
        code = node.get('parameters', {}).get('jsCode', '')
        print(code[:1500] if code else "NO CODE")
        print()
