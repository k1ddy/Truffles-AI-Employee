#!/usr/bin/env python3
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

url = f"https://n8n.truffles.kz/api/v1/executions/764036?includeData=true"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

error = data.get('data', {}).get('resultData', {}).get('error', {})
print("=== ERROR ===")
print(f"Message: {error.get('message', 'unknown')}")
node = error.get('node', {})
if isinstance(node, dict):
    print(f"Node: {node.get('name', 'unknown')}")
print(f"Description: {error.get('description', '')[:500]}")

run_data = data.get('data', {}).get('resultData', {}).get('runData', {})
print(f"\nExecuted: {list(run_data.keys())}")
