#!/usr/bin/env python3
"""Check Telegram Callback workflow structure"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print("=== NODES ===")
for node in workflow['nodes']:
    print(f"  {node['name']} ({node['type']})")

print("\n=== CONNECTIONS ===")
for src, conns in workflow.get('connections', {}).items():
    if 'main' in conns:
        for i, branch in enumerate(conns['main']):
            targets = [c['node'] for c in branch]
            print(f"  {src} [{i}] -> {targets}")

print("\n=== PARSE MESSAGE CODE ===")
for node in workflow['nodes']:
    if node['name'] == 'Parse Message':
        code = node.get('parameters', {}).get('jsCode', '')
        print(code[:500] if code else "NO CODE")
