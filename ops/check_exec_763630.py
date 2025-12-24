#!/usr/bin/env python3
import json
import urllib.request

API_KEY = "REDACTED_JWT"

url = f"https://n8n.truffles.kz/api/v1/executions/763630?includeData=true"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

run_data = data.get('data', {}).get('resultData', {}).get('runData', {})

print("=== EXECUTED NODES ===")
for name in run_data.keys():
    print(f"  {name}")

print("\n=== GET BOT TOKEN OUTPUT ===")
if 'Get Bot Token' in run_data:
    out = run_data['Get Bot Token'][-1].get('data', {}).get('main', [[]])
    if out and out[0]:
        print(json.dumps(out[0][0].get('json', {}), indent=2))
    else:
        print("EMPTY OUTPUT!")

print("\n=== PARSE CALLBACK OUTPUT ===")
if 'Parse Callback' in run_data:
    out = run_data['Parse Callback'][-1].get('data', {}).get('main', [[]])
    if out and out[0]:
        j = out[0][0].get('json', {})
        print(f"type: {j.get('type')}")
        print(f"data keys: {list(j.get('data', {}).keys()) if j.get('data') else 'no data'}")
