#!/usr/bin/env python3
"""Show STT output for execution"""
import json
import requests
import sys

# Read API key from check_execution.py
API_KEY = None
with open('/home/zhan/truffles/ops/check_execution.py') as f:
    for line in f:
        if "API_KEY = '" in line:
            API_KEY = line.split("'")[1]
            break

exec_id = sys.argv[1] if len(sys.argv) > 1 else '761381'
url = f'https://n8n.truffles.kz/api/v1/executions/{exec_id}?includeData=true'
data = requests.get(url, headers={'X-N8N-API-KEY': API_KEY}).json()
run_data = data.get('data', {}).get('resultData', {}).get('runData', {})

# Show specific node or all
node_name = sys.argv[2] if len(sys.argv) > 2 else None

if node_name:
    nodes = [node_name]
else:
    nodes = run_data.keys()  # Show all nodes

for name in nodes:
    node_data = run_data.get(name, [])
    if node_data:
        print(f'\n=== {name} ===')
        try:
            out = node_data[0].get('data', {}).get('main', [[{}]])[0][0].get('json', {})
            # Show specific fields for Audio Result
            if name == 'Audio Result':
                print(f"normalized_text: {out.get('normalized_text', 'NOT_FOUND')}")
                print(f"text: {out.get('text', 'NOT_FOUND')}")
                print(f"processing: {out.get('processing', 'NOT_FOUND')}")
                print(f"All keys: {list(out.keys())}")
            else:
                print(json.dumps(out, indent=2, ensure_ascii=False)[:3000])
        except Exception as e:
            print(f"Error: {e}")
            print(json.dumps(node_data[0], indent=2, ensure_ascii=False)[:3000])
