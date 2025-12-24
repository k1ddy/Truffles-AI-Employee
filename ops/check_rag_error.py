#!/usr/bin/env python3
import json
import urllib.request

API_KEY = "REDACTED_JWT"

url = f"https://n8n.truffles.kz/api/v1/executions/763670?includeData=true"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

run_data = data.get('data', {}).get('resultData', {}).get('runData', {})

print("=== RAG SEARCH ERROR ===")
if 'RAG Search' in run_data:
    node_data = run_data['RAG Search'][-1]
    error = node_data.get('error', {})
    if error:
        print(json.dumps(error, indent=2, ensure_ascii=False, default=str)[:2000])
