#!/usr/bin/env python3
import json
import urllib.request

API_KEY = "REDACTED_JWT"

url = f"https://n8n.truffles.kz/api/v1/executions/763813?includeData=true"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

run_data = data.get('data', {}).get('resultData', {}).get('runData', {})

print("=== PARSE INPUT OUTPUT ===")
if 'Parse Input' in run_data:
    out = run_data['Parse Input'][-1].get('data', {}).get('main', [[]])
    if out and out[0]:
        print(json.dumps(out[0][0].get('json', {}), indent=2, ensure_ascii=False))

print("\n=== UPSERT USER OUTPUT ===")
if 'Upsert User' in run_data:
    out = run_data['Upsert User'][-1].get('data', {}).get('main', [[]])
    if out and out[0]:
        print(json.dumps(out[0][0].get('json', {}), indent=2, ensure_ascii=False))
