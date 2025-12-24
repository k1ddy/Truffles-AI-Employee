#!/usr/bin/env python3
import json
import urllib.request

API_KEY = "REDACTED_JWT"

url = f"https://n8n.truffles.kz/api/v1/executions/763670?includeData=true"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

run_data = data.get('data', {}).get('resultData', {}).get('runData', {})

print("=== RAG SEARCH INPUT ===")
if 'RAG Search' in run_data:
    node_data = run_data['RAG Search'][-1]
    input_data = node_data.get('inputData', {}).get('main', [[]])
    if input_data and input_data[0]:
        print(json.dumps(input_data[0][0].get('json', {}), indent=2, ensure_ascii=False)[:500])

print("\n=== IS DEADLOCK OUTPUT ===")
if 'Is Deadlock' in run_data:
    node_data = run_data['Is Deadlock'][-1]
    out = node_data.get('data', {}).get('main', [[]])
    for i, branch in enumerate(out):
        if branch:
            print(f"Branch {i}: {json.dumps(branch[0].get('json', {}), indent=2, ensure_ascii=False)[:300]}")
