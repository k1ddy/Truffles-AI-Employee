#!/usr/bin/env python3
"""Fix Escalation Handler connection"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "7jGZrdbaAAvtTnQX"

with open('/tmp/escalation.json', 'r') as f:
    workflow = json.load(f)

print(f"Loaded: {workflow['name']}")

connections = workflow['connections']

# Remove broken "Send to Telegram" connection
if 'Send to Telegram' in connections:
    del connections['Send to Telegram']
    print("Removed: Send to Telegram (broken)")

# Add correct connection: Call Telegram Adapter -> Should Respond?
connections['Call Telegram Adapter'] = {
    "main": [[{"node": "Should Respond?", "type": "main", "index": 0}]]
}
print("Added: Call Telegram Adapter -> Should Respond?")

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
