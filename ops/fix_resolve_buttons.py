#!/usr/bin/env python3
"""Fix Resolve flow - remove buttons after resolve"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

# Download workflow
url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print(f"Loaded: {workflow['name']}")

# Add "Remove Buttons" node for resolve flow
remove_buttons_node = {
    "parameters": {
        "method": "POST",
        "url": "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/editMessageReplyMarkup",
        "sendBody": True,
        "bodyParameters": {
            "parameters": [
                {"name": "chat_id", "value": "={{ $('Merge Token').first().json.chat_id }}"},
                {"name": "message_id", "value": "={{ $('Merge Token').first().json.message_id }}"},
                {"name": "reply_markup", "value": "={{ JSON.stringify({inline_keyboard: [[{text: '✅ Решено', callback_data: 'done'}]]}) }}"}
            ]
        },
        "options": {}
    },
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [544, 400],
    "id": "cb-remove-btns-resolve",
    "name": "Remove Buttons Resolve"
}

# Check if exists
exists = False
for i, node in enumerate(workflow['nodes']):
    if node['name'] == 'Remove Buttons Resolve':
        workflow['nodes'][i] = remove_buttons_node
        exists = True
        print("Updated: Remove Buttons Resolve")

if not exists:
    workflow['nodes'].append(remove_buttons_node)
    print("Added: Remove Buttons Resolve")

# Update connections: Resolve Response -> Remove Buttons Resolve -> Answer Callback (for resolve)
# Current: Resolve Response -> Answer Callback
# New: Resolve Response -> Remove Buttons Resolve -> then continue

connections = workflow['connections']

# Find and update Resolve Response connection
if 'Resolve Response' in connections:
    connections['Resolve Response']['main'] = [[{"node": "Remove Buttons Resolve", "type": "main", "index": 0}]]
    print("Updated: Resolve Response -> Remove Buttons Resolve")

# Add Remove Buttons Resolve -> Answer Callback
connections['Remove Buttons Resolve'] = {
    "main": [[{"node": "Answer Callback", "type": "main", "index": 0}]]
}
print("Added: Remove Buttons Resolve -> Answer Callback")

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
