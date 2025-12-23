#!/usr/bin/env python3
"""Get execution error details"""
import json
import urllib.request
import sys

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
EXEC_ID = sys.argv[1] if len(sys.argv) > 1 else "763373"

url = f"https://n8n.truffles.kz/api/v1/executions/{EXEC_ID}"
headers = {"X-N8N-API-KEY": API_KEY}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

result_data = data.get('data', {}).get('resultData', {})

# Print error
error = result_data.get('error', {})
if error:
    print("=== ERROR ===")
    print(json.dumps(error, indent=2, ensure_ascii=False))

# Print run data
run_data = result_data.get('runData', {})
print("\n=== NODES EXECUTED ===")
for node_name, runs in run_data.items():
    if runs:
        last = runs[-1]
        status = "OK" if not last.get('error') else "ERROR"
        print(f"{node_name}: {status}")
        
        # Show output
        output = last.get('data', {}).get('main', [[]])
        if output and output[0]:
            first_item = output[0][0].get('json', {})
            print(f"  Output: {json.dumps(first_item, ensure_ascii=False)[:300]}")
        
        # Show error if any
        if last.get('error'):
            print(f"  Error: {last['error'].get('message', 'Unknown')}")
