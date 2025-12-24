#!/usr/bin/env python3
import json
import urllib.request

API_KEY = "REDACTED_JWT"

url = f"https://n8n.truffles.kz/api/v1/executions/763955?includeData=true"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

run_data = data.get('data', {}).get('resultData', {}).get('runData', {})

print("=== PARSE CALLBACK OUTPUT ===")
if 'Parse Callback' in run_data:
    out = run_data['Parse Callback'][-1].get('data', {}).get('main', [[]])
    if out and out[0]:
        print(json.dumps(out[0][0].get('json', {}), indent=2))

print("\n=== RESOLVE HANDOVER OUTPUT ===")
if 'Resolve Handover' in run_data:
    out = run_data['Resolve Handover'][-1].get('data', {}).get('main', [[]])
    if out and out[0]:
        print(json.dumps(out[0][0].get('json', {}), indent=2))
    else:
        print("EMPTY!")

print("\n=== UNMUTE BOT INPUT ===")
if 'Unmute Bot' in run_data:
    inp = run_data['Unmute Bot'][-1].get('inputData', {}).get('main', [[]])
    if inp and inp[0]:
        print(json.dumps(inp[0][0].get('json', {}), indent=2))
