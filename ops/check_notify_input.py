#!/usr/bin/env python3
import json

with open('/tmp/exec_data.json', 'r') as f:
    data = json.load(f)

result_data = data.get('data', {}).get('resultData', {})
run_data = result_data.get('runData', {})

print("=== MERGE TOKEN OUTPUT ===")
if 'Merge Token' in run_data:
    runs = run_data['Merge Token']
    if runs:
        output = runs[-1].get('data', {}).get('main', [[]])
        if output and output[0]:
            print(json.dumps(output[0][0].get('json', {}), indent=2, ensure_ascii=False))

print("\n=== TAKE RESPONSE OUTPUT ===")
if 'Take Response' in run_data:
    runs = run_data['Take Response']
    if runs:
        output = runs[-1].get('data', {}).get('main', [[]])
        if output and output[0]:
            print(json.dumps(output[0][0].get('json', {}), indent=2, ensure_ascii=False))

print("\n=== NOTIFY IN CHAT INPUT ===")
if 'Notify in Chat' in run_data:
    runs = run_data['Notify in Chat']
    if runs:
        input_data = runs[-1].get('inputData', {}).get('main', [[]])
        if input_data and input_data[0]:
            print(json.dumps(input_data[0][0].get('json', {}), indent=2, ensure_ascii=False))
        
        # Check error
        error = runs[-1].get('error', {})
        if error:
            print(f"\nERROR: {error}")
