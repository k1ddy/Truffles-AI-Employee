#!/usr/bin/env python3
"""
Fix resolve flow - it should NOT go through Update Buttons and Notify in Chat
Those are for take flow only.

Current wrong flow:
  Remove Buttons Resolve → Unpin → Answer Callback → Update Buttons → Notify in Chat

Correct flow:
  Take: Take Response → Answer Callback → Update Buttons → Notify in Chat
  Resolve: Remove Buttons Resolve → Unpin → Answer Callback (END)
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

# Add separate Answer Callback for Resolve (Answer Callback Resolve)
answer_resolve_node = {
    "parameters": {
        "method": "POST",
        "url": "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/answerCallbackQuery",
        "sendBody": True,
        "bodyParameters": {
            "parameters": [
                {"name": "callback_query_id", "value": "={{ $('Merge Token').first().json.callback_query_id }}"},
                {"name": "text", "value": "Заявка закрыта"}
            ]
        },
        "options": {}
    },
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [900, 450],
    "id": "cb-answer-resolve",
    "name": "Answer Callback Resolve"
}

# Check if exists
exists = any(n['name'] == 'Answer Callback Resolve' for n in workflow['nodes'])
if not exists:
    workflow['nodes'].append(answer_resolve_node)
    print("Added: Answer Callback Resolve")

# Fix connections
connections = workflow['connections']

# Unpin Escalation → Answer Callback Resolve (not Answer Callback)
connections['Unpin Escalation'] = {
    "main": [[{"node": "Answer Callback Resolve", "type": "main", "index": 0}]]
}
print("Fixed: Unpin Escalation -> Answer Callback Resolve")

# Answer Callback Resolve ends flow (no further connections needed)
# Remove it from going to Update Buttons
if 'Answer Callback Resolve' in connections:
    del connections['Answer Callback Resolve']

# Make sure Answer Callback (for take) goes to Update Buttons
connections['Answer Callback'] = {
    "main": [[{"node": "Update Buttons", "type": "main", "index": 0}]]
}
print("Fixed: Answer Callback -> Update Buttons (take only)")

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
