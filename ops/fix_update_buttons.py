#!/usr/bin/env python3
"""Fix Update Buttons - correct reference and button text"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

with open('/tmp/callback.json', 'r') as f:
    workflow = json.load(f)

print(f"Loaded: {workflow['name']}")

# Fix Update Buttons
for node in workflow['nodes']:
    if node['name'] == 'Update Buttons':
        # После [Беру] → кнопка [Решено ✅]
        # После [Решено] → кнопка [Готово]
        node['parameters'] = {
            "method": "POST",
            "url": "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/editMessageReplyMarkup",
            "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "chat_id", "value": "={{ $('Merge Token').first().json.chat_id }}"},
                    {"name": "message_id", "value": "={{ $('Merge Token').first().json.message_id }}"},
                    {"name": "reply_markup", "value": "={{ JSON.stringify({inline_keyboard: [[{text: 'Решено ✅', callback_data: 'resolve_' + $('Merge Token').first().json.handover_id}]]}) }}"}
                ]
            },
            "options": {}
        }
        print("Fixed: Update Buttons (shows [Решено ✅])")

# Update workflow
update_payload = {
    "name": workflow["name"],
    "nodes": workflow["nodes"],
    "connections": workflow["connections"],
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
