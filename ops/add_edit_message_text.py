#!/usr/bin/env python3
"""
Add editMessageText after [Беру] to change pinned message text to "🔄 Решает: {manager_name}"
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

# Add Edit Status Text node
edit_status_node = {
    "parameters": {
        "method": "POST",
        "url": "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/editMessageText",
        "sendBody": True,
        "bodyParameters": {
            "parameters": [
                {"name": "chat_id", "value": "={{ $('Merge Token').first().json.chat_id }}"},
                {"name": "message_id", "value": "={{ $('Merge Token').first().json.message_id }}"},
                {"name": "text", "value": "=🔄 Решает: {{ $('Merge Token').first().json.manager_name }}"},
                {"name": "reply_markup", "value": "={{ JSON.stringify({inline_keyboard: [[{text: 'Решено ✅', callback_data: 'resolve_' + $('Merge Token').first().json.handover_id}]]}) }}"}
            ]
        },
        "options": {}
    },
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [600, 100],
    "id": "cb-edit-status",
    "name": "Edit Status Text"
}

# Check if exists
exists = any(n['name'] == 'Edit Status Text' for n in workflow['nodes'])
if not exists:
    workflow['nodes'].append(edit_status_node)
    print("Added: Edit Status Text")
else:
    for i, n in enumerate(workflow['nodes']):
        if n['name'] == 'Edit Status Text':
            workflow['nodes'][i] = edit_status_node
            print("Updated: Edit Status Text")

# Update connections:
# Take Response → Answer Callback → Edit Status Text → Notify in Chat
# (Edit Status Text replaces Update Buttons for take flow - it does both text and buttons)
connections = workflow['connections']

connections['Answer Callback'] = {
    "main": [[{"node": "Edit Status Text", "type": "main", "index": 0}]]
}
print("Fixed: Answer Callback -> Edit Status Text")

connections['Edit Status Text'] = {
    "main": [[{"node": "Notify in Chat", "type": "main", "index": 0}]]
}
print("Fixed: Edit Status Text -> Notify in Chat")

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
