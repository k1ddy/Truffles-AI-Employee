#!/usr/bin/env python3
import json

with open('/tmp/exec_data.json', 'r') as f:
    data = json.load(f)

result_data = data.get('data', {}).get('resultData', {})
run_data = result_data.get('runData', {})

print("=== ALL NODES ===")
for node_name in run_data.keys():
    print(f"  {node_name}")

print("\n=== PARSE CALLBACK ===")
if 'Parse Callback' in run_data:
    runs = run_data['Parse Callback']
    if runs:
        output = runs[-1].get('data', {}).get('main', [[]])
        if output and output[0]:
            full_json = output[0][0].get('json', {})
            print(json.dumps(full_json, indent=2, ensure_ascii=False))
