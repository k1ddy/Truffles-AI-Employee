#!/usr/bin/env python3
"""
Add client message forwarding to topic when handover is active
"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "4vaEvzlaMrgovhNz"

url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print(f"Loaded: {workflow['name']}")

# New nodes to add
new_nodes = [
    {
        "parameters": {
            "operation": "executeQuery",
            "query": """SELECT 
  h.id as handover_id,
  h.conversation_id,
  c.telegram_topic_id,
  cs.telegram_chat_id,
  cs.telegram_bot_token
FROM conversations c
JOIN handovers h ON h.conversation_id = c.id AND h.status = 'active'
JOIN client_settings cs ON cs.client_id = c.client_id
WHERE c.id = '{{ $('Build Context').first().json.conversation_id }}';""",
            "options": {}
        },
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [1200, 300],
        "id": "ma-check-handover",
        "name": "Check Active Handover",
        "credentials": {"postgres": {"id": "SUHrbh39Ig0fBusT", "name": "ChatbotDB"}}
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
        "position": [1400, 300],
        "id": "ma-has-handover",
        "name": "Handover Active?"
    },
    {
        "parameters": {
            "method": "POST",
            "url": "=https://api.telegram.org/bot{{ $('Check Active Handover').first().json.telegram_bot_token }}/sendMessage",
            "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "chat_id", "value": "={{ $('Check Active Handover').first().json.telegram_chat_id }}"},
                    {"name": "message_thread_id", "value": "={{ $('Check Active Handover').first().json.telegram_topic_id }}"},
                    {"name": "text", "value": "=💬 Клиент: {{ $('Build Context').first().json.message }}"}
                ]
            },
            "options": {}
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1600, 250],
        "id": "ma-forward-topic",
        "name": "Forward to Topic"
    },
    {
        "parameters": {
            "operation": "executeQuery",
            "query": """UPDATE handovers 
SET messages = COALESCE(messages, '[]'::jsonb) || 
  jsonb_build_array(jsonb_build_object(
    'from', 'client',
    'text', '{{ $('Build Context').first().json.message }}',
    'at', NOW()::text
  ))
WHERE id = '{{ $('Check Active Handover').first().json.handover_id }}';""",
            "options": {}
        },
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [1800, 250],
        "id": "ma-save-client-msg",
        "name": "Save Client Message",
        "credentials": {"postgres": {"id": "SUHrbh39Ig0fBusT", "name": "ChatbotDB"}}
    },
    {
        "parameters": {},
        "type": "n8n-nodes-base.noOp",
        "typeVersion": 1,
        "position": [2000, 250],
        "id": "ma-exit-handover",
        "name": "Exit (Handover Active)"
    }
]

# Add nodes
existing_names = {n['name'] for n in workflow['nodes']}
for new_node in new_nodes:
    if new_node['name'] not in existing_names:
        workflow['nodes'].append(new_node)
        print(f"Added: {new_node['name']}")
    else:
        for i, n in enumerate(workflow['nodes']):
            if n['name'] == new_node['name']:
                workflow['nodes'][i] = new_node
                print(f"Updated: {new_node['name']}")
                break

# Update connections
connections = workflow['connections']

# Build Context -> Check Active Handover (instead of Is Deadlock)
connections['Build Context'] = {
    "main": [[{"node": "Check Active Handover", "type": "main", "index": 0}]]
}

# Check Active Handover -> Handover Active?
connections['Check Active Handover'] = {
    "main": [[{"node": "Handover Active?", "type": "main", "index": 0}]]
}

# Handover Active? -> [true] Forward to Topic, [false] Is Deadlock
connections['Handover Active?'] = {
    "main": [
        [{"node": "Forward to Topic", "type": "main", "index": 0}],
        [{"node": "Is Deadlock", "type": "main", "index": 0}]
    ]
}

# Forward to Topic -> Save Client Message
connections['Forward to Topic'] = {
    "main": [[{"node": "Save Client Message", "type": "main", "index": 0}]]
}

# Save Client Message -> Exit
connections['Save Client Message'] = {
    "main": [[{"node": "Exit (Handover Active)", "type": "main", "index": 0}]]
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
