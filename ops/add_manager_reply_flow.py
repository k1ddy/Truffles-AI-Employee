#!/usr/bin/env python3
"""
Add manager reply flow to Telegram Callback workflow

Flow: Parse Message → Find Handover → Has Handover? → Send to WhatsApp → Save Messages → Confirm
"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

# Chatflow API token (from existing Send to WhatsApp node)
CHATFLOW_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMiIsInJvbGUiOiJ1c2VyIiwiaWF0IjoxNzQyMjA3MjAzLCJleHAiOjE4OTk4ODcyMDN9.P4JmKvKBz8anmXbxMRXTz5kuHYaFQyOSCqq4QBmgRgg"

# Download workflow
url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print(f"Loaded: {workflow['name']}")

# Define new nodes
new_nodes = [
    {
        "parameters": {
            "operation": "executeQuery",
            "query": """SELECT 
  h.id as handover_id,
  h.conversation_id,
  c.client_id,
  u.phone,
  u.phone || '@s.whatsapp.net' as remote_jid,
  cl.config->>'instance_id' as instance_id,
  cs.telegram_bot_token as bot_token
FROM conversations c
JOIN handovers h ON h.conversation_id = c.id AND h.status = 'active'
JOIN users u ON u.id = c.user_id
JOIN clients cl ON cl.id = c.client_id
JOIN client_settings cs ON cs.client_id = c.client_id
WHERE c.telegram_topic_id = {{ $('Parse Message').first().json.topic_id }};""",
            "options": {}
        },
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [200, 600],
        "id": "cb-find-handover",
        "name": "Find Handover Data",
        "credentials": {"postgres": {"id": "1", "name": "Postgres"}}
    },
    {
        "parameters": {
            "conditions": {
                "options": {"version": 2, "caseSensitive": True, "leftValue": ""},
                "combinator": "and",
                "conditions": [{
                    "id": "has-handover",
                    "leftValue": "={{ $json.handover_id }}",
                    "rightValue": "",
                    "operator": {"type": "string", "operation": "exists", "singleValue": True}
                }]
            }
        },
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [400, 600],
        "id": "cb-has-handover",
        "name": "Has Active Handover?"
    },
    {
        "parameters": {
            "method": "POST",
            "url": "https://app.chatflow.kz/api/v1/send-text",
            "sendQuery": True,
            "queryParameters": {
                "parameters": [
                    {"name": "token", "value": CHATFLOW_TOKEN},
                    {"name": "instance_id", "value": "={{ $('Find Handover Data').first().json.instance_id }}"},
                    {"name": "jid", "value": "={{ $('Find Handover Data').first().json.remote_jid }}"},
                    {"name": "msg", "value": "={{ $('Parse Message').first().json.text }}"}
                ]
            },
            "options": {}
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [600, 550],
        "id": "cb-send-whatsapp",
        "name": "Send Manager Reply to WhatsApp"
    },
    {
        "parameters": {
            "operation": "executeQuery",
            "query": """UPDATE handovers 
SET messages = COALESCE(messages, '[]'::jsonb) || 
  jsonb_build_array(jsonb_build_object(
    'from', 'manager',
    'name', '{{ $('Parse Message').first().json.manager_name }}',
    'text', '{{ $('Parse Message').first().json.text }}',
    'at', NOW()::text
  ))
WHERE id = '{{ $('Find Handover Data').first().json.handover_id }}';""",
            "options": {}
        },
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [800, 550],
        "id": "cb-save-message",
        "name": "Save Manager Message",
        "credentials": {"postgres": {"id": "1", "name": "Postgres"}}
    },
    {
        "parameters": {
            "method": "POST",
            "url": "=https://api.telegram.org/bot{{ $('Find Handover Data').first().json.bot_token }}/sendMessage",
            "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "chat_id", "value": "={{ $('Parse Message').first().json.chat_id }}"},
                    {"name": "message_thread_id", "value": "={{ $('Parse Message').first().json.topic_id }}"},
                    {"name": "text", "value": "📤 Отправлено клиенту"}
                ]
            },
            "options": {}
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1000, 550],
        "id": "cb-confirm-sent",
        "name": "Confirm Sent to Topic"
    }
]

# Add or update nodes
existing_names = {n['name'] for n in workflow['nodes']}
for new_node in new_nodes:
    if new_node['name'] in existing_names:
        # Update existing
        for i, n in enumerate(workflow['nodes']):
            if n['name'] == new_node['name']:
                workflow['nodes'][i] = new_node
                print(f"Updated: {new_node['name']}")
                break
    else:
        workflow['nodes'].append(new_node)
        print(f"Added: {new_node['name']}")

# Update connections
connections = workflow['connections']

# Parse Message -> Find Handover Data
connections['Parse Message'] = {
    "main": [[{"node": "Find Handover Data", "type": "main", "index": 0}]]
}

# Find Handover Data -> Has Active Handover?
connections['Find Handover Data'] = {
    "main": [[{"node": "Has Active Handover?", "type": "main", "index": 0}]]
}

# Has Active Handover? -> [true] Send to WhatsApp, [false] (nothing)
connections['Has Active Handover?'] = {
    "main": [
        [{"node": "Send Manager Reply to WhatsApp", "type": "main", "index": 0}],
        []  # false branch - do nothing
    ]
}

# Send to WhatsApp -> Save Message
connections['Send Manager Reply to WhatsApp'] = {
    "main": [[{"node": "Save Manager Message", "type": "main", "index": 0}]]
}

# Save Message -> Confirm
connections['Save Manager Message'] = {
    "main": [[{"node": "Confirm Sent to Topic", "type": "main", "index": 0}]]
}

print("\nUpdated connections")

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
    print(f"\nUpdated: {result['name']}")
    print("SUCCESS!")
