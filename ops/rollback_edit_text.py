#!/usr/bin/env python3
"""
Rollback: 
1. Remove Edit Status Text - keep original escalation text
2. Remove Notify in Chat after [Беру] - button is enough
3. Keep only: Answer Callback → Update Buttons (change to [Решено ✅])
"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print(f"Loaded: {workflow['name']}")

# Remove Edit Status Text node
workflow['nodes'] = [n for n in workflow['nodes'] if n['name'] != 'Edit Status Text']
print("Removed: Edit Status Text")

# Fix connections for take flow:
# Take Response → Answer Callback → Update Buttons (END)
# No Notify in Chat - button change is enough
connections = workflow['connections']

connections['Answer Callback'] = {
    "main": [[{"node": "Update Buttons", "type": "main", "index": 0}]]
}
print("Fixed: Answer Callback -> Update Buttons")

# Update Buttons ends the flow (remove connection to Notify in Chat)
if 'Update Buttons' in connections:
    del connections['Update Buttons']
print("Fixed: Update Buttons ends flow (no Notify in Chat)")

# Remove Edit Status Text from connections
if 'Edit Status Text' in connections:
    del connections['Edit Status Text']

# Update workflow
update_payload = {
    "name": workflow["name"],
    "nodes": workflow["nodes"],
    "connections": connections,
    "settings": workflow.get("settings", {}),
}

url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
data = json.dumps(update_payload).encode('utf-8')

req = urllib.request.Request(
    url,
    data=data,
    headers={
        "X-N8N-API-KEY": API_KEY,
        "Content-Type": "application/json"
    },
    method='PUT'
)

with urllib.request.urlopen(req) as response:
    result = json.loads(response.read().decode())
    print(f"Updated: {result['name']}")
    print("SUCCESS!")
    print("\nТеперь после [Беру]:")
    print("- Закреп остаётся с оригинальной заявкой")
    print("- Кнопка меняется на [Решено ✅]")
    print("- Никаких лишних сообщений")
