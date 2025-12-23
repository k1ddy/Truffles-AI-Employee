#!/usr/bin/env python3
"""Dump execution data"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

url = f"https://n8n.truffles.kz/api/v1/executions/763573"
headers = {"X-N8N-API-KEY": API_KEY}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

result_data = data.get('data', {}).get('resultData', {})
run_data = result_data.get('runData', {})

# List all nodes
print("=== ALL NODES ===")
for node_name in run_data.keys():
    print(f"  {node_name}")

# Check Parse Callback full
print("\n=== PARSE CALLBACK FULL ===")
if 'Parse Callback' in run_data:
    runs = run_data['Parse Callback']
    if runs:
        output = runs[-1].get('data', {}).get('main', [[]])
        if output and output[0]:
            full_json = output[0][0].get('json', {})
            print(json.dumps(full_json, indent=2, ensure_ascii=False))
            print(f"\ntopic_id value: {full_json.get('topic_id')}")
            print(f"topic_id type: {type(full_json.get('topic_id'))}")
