#!/usr/bin/env python3
"""Get detailed execution info"""
import json
import urllib.request
import sys

API_KEY = "REDACTED_JWT"
EXEC_ID = sys.argv[1] if len(sys.argv) > 1 else "763395"

url = f"https://n8n.truffles.kz/api/v1/executions/{EXEC_ID}?includeData=true"
headers = {"X-N8N-API-KEY": API_KEY}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

print(f"Execution {EXEC_ID}")
print(f"Status: {data.get('status')}")
print(f"Mode: {data.get('mode')}")

exec_data = data.get('data', {})
result_data = exec_data.get('resultData', {})

# Error
if result_data.get('error'):
    print(f"\n=== ERROR ===")
    err = result_data['error']
    print(f"Message: {err.get('message')}")
    print(f"Node: {err.get('node', {}).get('name') if isinstance(err.get('node'), dict) else err.get('node')}")

# Run data
run_data = result_data.get('runData', {})
print(f"\n=== NODES ({len(run_data)}) ===")
for node_name, runs in run_data.items():
    if runs:
        last = runs[-1]
        print(f"\n{node_name}:")
        
        # Input
        input_data = last.get('inputData', {}).get('main', [[]])
        if input_data and input_data[0]:
            print(f"  Input: {json.dumps(input_data[0][0].get('json', {}), ensure_ascii=False)[:200]}")
        
        # Output  
        output = last.get('data', {}).get('main', [[]])
        if output and output[0]:
            print(f"  Output: {json.dumps(output[0][0].get('json', {}), ensure_ascii=False)[:200]}")
        
        # Error
        if last.get('error'):
            print(f"  ERROR: {last['error'].get('message', str(last['error']))[:200]}")
