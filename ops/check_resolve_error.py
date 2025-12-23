#!/usr/bin/env python3
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

url = f"https://n8n.truffles.kz/api/v1/executions/763955?includeData=true"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

error = data.get('data', {}).get('resultData', {}).get('error', {})
print("=== ERROR ===")
print(json.dumps(error, indent=2, ensure_ascii=False, default=str)[:1500])

run_data = data.get('data', {}).get('resultData', {}).get('runData', {})
print("\n=== EXECUTED NODES ===")
print(list(run_data.keys()))
