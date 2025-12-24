#!/usr/bin/env python3
"""
Fix multiple issues in 9_Telegram_Callback:
1. Skip should remove buttons (not leave them)
2. Check Unpin Escalation works properly
"""

import json
import requests

API_KEY = 'REDACTED_JWT'

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/HQOWuMDIBPphC86v',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()
nodes = data['nodes']
connections = data['connections']

# 1. Add "Remove Buttons Skip" node
remove_buttons_skip = {
    "parameters": {
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
    },
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [768, 500],
    "id": "cb-remove-skip-001",
    "name": "Remove Buttons Skip"
}
nodes.append(remove_buttons_skip)
print("Added: Remove Buttons Skip")

# 2. Update Skip Response to connect to Answer Callback, then Remove Buttons Skip
# Current: Skip Response -> Answer Callback (stop)
# New: Skip Response -> Answer Callback -> Remove Buttons Skip

# Add connection from Answer Callback to Remove Buttons Skip for skip path
# But Answer Callback is shared by Take and Skip...
# We need separate Answer Callback for Skip

# Actually, let's check current flow
print("\nCurrent Skip flow:")
if 'Skip Response' in connections:
    for out in connections['Skip Response']['main']:
        print("  Skip Response ->", [o['node'] for o in out])
if 'Answer Callback' in connections:
    for out in connections['Answer Callback']['main']:
        print("  Answer Callback ->", [o['node'] for o in out])

# The issue is that Answer Callback -> Update Buttons (for Take)
# For Skip, we need Answer Callback -> Remove Buttons Skip (no update)

# Solution: Create separate Answer Callback Skip
answer_callback_skip = {
    "parameters": {
        "method": "POST",
        "url": "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/answerCallbackQuery",
        "sendBody": True,
        "bodyParameters": {
            "parameters": [
                {"name": "callback_query_id", "value": "={{ $('Parse Callback').first().json.callback_query_id }}"},
                {"name": "text", "value": "={{ $json.response_text }}"}
            ]
        },
        "options": {}
    },
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [544, 500],
    "id": "cb-answer-skip-001",
    "name": "Answer Callback Skip"
}
nodes.append(answer_callback_skip)
print("Added: Answer Callback Skip")

# 3. Update connections
# Skip Response -> Answer Callback Skip -> Remove Buttons Skip
connections['Skip Response'] = {
    "main": [[{"node": "Answer Callback Skip", "type": "main", "index": 0}]]
}
connections['Answer Callback Skip'] = {
    "main": [[{"node": "Remove Buttons Skip", "type": "main", "index": 0}]]
}
print("Updated Skip connections")

# 4. Check Unpin Escalation
print("\nChecking Unpin Escalation...")
for node in nodes:
    if node['name'] == 'Unpin Escalation':
        print("Found Unpin Escalation:")
        print(json.dumps(node['parameters'], indent=2)[:300])
        break

# Save
resp = requests.put(
    'https://n8n.truffles.kz/api/v1/workflows/HQOWuMDIBPphC86v',
    headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
    json={'name': data['name'], 'nodes': nodes, 'connections': connections, 'settings': data.get('settings', {})}
)
print(f"\nStatus: {resp.status_code}")
