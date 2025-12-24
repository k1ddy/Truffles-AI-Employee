#!/usr/bin/env python3
import json
import urllib.request

API_KEY = "REDACTED_JWT"

url = f"https://n8n.truffles.kz/api/v1/executions/763966?includeData=true"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

run_data = data.get('data', {}).get('resultData', {}).get('runData', {})

print("=== LOAD STATUS OUTPUT ===")
if 'Load Status' in run_data:
    out = run_data['Load Status'][-1].get('data', {}).get('main', [[]])
    if out and out[0]:
        print(json.dumps(out[0][0].get('json', {}), indent=2))

print("\n=== DECIDE ACTION OUTPUT ===")
if 'Decide Action' in run_data:
    out = run_data['Decide Action'][-1].get('data', {}).get('main', [[]])
    if out and out[0]:
        print(json.dumps(out[0][0].get('json', {}), indent=2))

print("\n=== SHOULD PROCESS? OUTPUT ===")
if 'Should Process?' in run_data:
    out = run_data['Should Process?'][-1].get('data', {}).get('main', [[]])
    print(f"Branches: {len(out)}")
    for i, branch in enumerate(out):
        if branch:
            print(f"  Branch {i}: {len(branch)} items")
