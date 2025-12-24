#!/usr/bin/env python3
import json
import urllib.request

API_KEY = "REDACTED_JWT"

url = f"https://n8n.truffles.kz/api/v1/executions/763663?includeData=true"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

run_data = data.get('data', {}).get('resultData', {}).get('runData', {})

print("=== CHECK ACTIVE HANDOVER OUTPUT ===")
if 'Check Active Handover' in run_data:
    node_data = run_data['Check Active Handover'][-1]
    out = node_data.get('data', {}).get('main', [[]])
    print(f"Output branches: {len(out)}")
    for i, branch in enumerate(out):
        print(f"  Branch {i}: {len(branch)} items")
        if branch:
            print(f"    Data: {json.dumps(branch[0].get('json', {}), indent=2)}")

print("\n=== IS BOT MUTED? OUTPUT ===")
if 'Is Bot Muted?' in run_data:
    node_data = run_data['Is Bot Muted?'][-1]
    out = node_data.get('data', {}).get('main', [[]])
    for i, branch in enumerate(out):
        if branch:
            print(f"Branch {i}: {len(branch)} items - EXECUTED")
