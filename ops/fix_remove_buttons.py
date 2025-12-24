#!/usr/bin/env python3
"""Fix Remove Buttons Resolve - completely remove buttons"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print(f"Loaded: {workflow['name']}")

for node in workflow['nodes']:
    # Fix Remove Buttons Resolve - empty inline_keyboard removes buttons
    if node['name'] == 'Remove Buttons Resolve':
        node['parameters'] = {
            "method": "POST",
            "url": "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/editMessageReplyMarkup",
            "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "chat_id", "value": "={{ $('Merge Token').first().json.chat_id }}"},
                    {"name": "message_id", "value": "={{ $('Merge Token').first().json.message_id }}"},
                    {"name": "reply_markup", "value": "={{ JSON.stringify({inline_keyboard: []}) }}"}
                ]
            },
            "options": {}
        }
        print("Fixed: Remove Buttons Resolve (empty inline_keyboard)")

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
