#!/usr/bin/env python3
"""Check Merge Token full output"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"

url = f"https://n8n.truffles.kz/api/v1/executions/763573"
headers = {"X-N8N-API-KEY": API_KEY}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

result_data = data.get('data', {}).get('resultData', {})
run_data = result_data.get('runData', {})

print("=== MERGE TOKEN ===")
if 'Merge Token' in run_data:
    runs = run_data['Merge Token']
    if runs:
        output = runs[-1].get('data', {}).get('main', [[]])
        if output and output[0]:
            print(json.dumps(output[0][0].get('json', {}), indent=2, ensure_ascii=False))

print("\n=== TAKE RESPONSE ===")
if 'Take Response' in run_data:
    runs = run_data['Take Response']
    if runs:
        output = runs[-1].get('data', {}).get('main', [[]])
        if output and output[0]:
            print(json.dumps(output[0][0].get('json', {}), indent=2, ensure_ascii=False))
