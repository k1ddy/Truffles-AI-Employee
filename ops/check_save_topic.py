#!/usr/bin/env python3
"""Check Save Topic ID execution"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

# Check execution 763584
url = f"https://n8n.truffles.kz/api/v1/executions/763584?includeData=true"
headers = {"X-N8N-API-KEY": API_KEY}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

result_data = data.get('data', {}).get('resultData', {})
run_data = result_data.get('runData', {})

print("=== ALL NODES ===")
for node_name in run_data.keys():
    print(f"  {node_name}")

print("\n=== SAVE TOPIC ID ===")
if 'Save Topic ID' in run_data:
    runs = run_data['Save Topic ID']
    if runs:
        print(f"Executed: YES")
        output = runs[-1].get('data', {}).get('main', [[]])
        if output and output[0]:
            print(f"Output: {json.dumps(output[0][0].get('json', {}), indent=2)}")
        error = runs[-1].get('error')
        if error:
            print(f"Error: {error}")
else:
    print("NOT EXECUTED - Check Has Topic? branch")

print("\n=== HAS TOPIC? ===")
if 'Has Topic?' in run_data:
    runs = run_data['Has Topic?']
    if runs:
        output = runs[-1].get('data', {}).get('main', [[]])
        if output:
            for i, branch in enumerate(output):
                if branch:
                    print(f"Branch {i}: {len(branch)} items")
