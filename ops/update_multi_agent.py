#!/usr/bin/env python3
"""Update Multi-Agent to use Escalation Handler"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "4vaEvzlaMrgovhNz"
ESCALATION_HANDLER_ID = "7jGZrdbaAAvtTnQX"

# Load current workflow
with open('/tmp/multi_agent.json', 'r') as f:
    workflow = json.load(f)

print(f"Loaded: {workflow['name']}")
print(f"Nodes: {len(workflow['nodes'])}")

# Find nodes by name
def find_node(name):
    for n in workflow['nodes']:
        if n['name'] == name:
            return n
    return None

# 1. Add "Check Bot Muted" node after Parse Input
check_muted_node = {
    "parameters": {
        "operation": "executeQuery",
        "query": """SELECT 
  c.bot_status,
  c.bot_muted_until,
  CASE 
    WHEN c.bot_status = 'muted' AND c.bot_muted_until > NOW() THEN true
    ELSE false
  END as is_muted
FROM conversations c
JOIN users u ON c.user_id = u.id
WHERE u.phone = '{{ $('Parse Input').first().json.phone }}'
  AND c.status = 'active'
ORDER BY c.last_message_at DESC
LIMIT 1;""",
        "options": {}
    },
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.6,
    "position": [-4144, 560],
    "id": "check-muted-001",
    "name": "Check Bot Muted",
    "credentials": {
        "postgres": {
            "id": "SUHrbh39Ig0fBusT",
            "name": "ChatbotDB"
        }
    }
}

# 2. Add "Is Bot Muted?" switch
is_muted_node = {
    "parameters": {
        "conditions": {
            "options": {
                "caseSensitive": True,
                "leftValue": "",
                "typeValidation": "strict",
                "version": 2
            },
            "conditions": [
                {
                    "id": "muted-check",
                    "leftValue": "={{ $json.is_muted }}",
                    "rightValue": "",
                    "operator": {
                        "type": "boolean",
                        "operation": "true",
                        "singleValue": True
                    }
                }
            ],
            "combinator": "and"
        },
        "options": {}
    },
    "type": "n8n-nodes-base.if",
    "typeVersion": 2.2,
    "position": [-3920, 560],
    "id": "is-muted-001",
    "name": "Is Bot Muted?"
}

# 3. Add "Silent Exit" for muted
silent_exit_node = {
    "parameters": {
        "jsCode": "// Бот замьючен - выходим молча, не отвечаем\nreturn [];"
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [-3696, 640],
    "id": "silent-exit-muted-001",
    "name": "Silent Exit (Muted)"
}

# 4. Add "Call Escalation Handler" node
call_escalation_node = {
    "parameters": {
        "workflowId": {
            "__rl": True,
            "value": ESCALATION_HANDLER_ID,
            "mode": "id"
        },
        "workflowInputs": {
            "mappingMode": "defineBelow",
            "value": {
                "conversation_id": "={{ $('Build Context').first().json.conversation_id }}",
                "client_id": "={{ $('Build Context').first().json.client_id }}",
                "phone": "={{ $('Build Context').first().json.phone }}",
                "remoteJid": "={{ $('Build Context').first().json.remoteJid }}",
                "message": "={{ $('Build Context').first().json.message }}",
                "reason": "={{ $('Build Context').first().json.deadlockReason || 'escalation' }}",
                "bot_response": "={{ $json.output?.response || '' }}"
            }
        },
        "options": {}
    },
    "type": "n8n-nodes-base.executeWorkflow",
    "typeVersion": 1.2,
    "position": [-752, 400],
    "id": "call-escalation-001",
    "name": "Call Escalation Handler"
}

# Add new nodes
workflow['nodes'].append(check_muted_node)
workflow['nodes'].append(is_muted_node)
workflow['nodes'].append(silent_exit_node)
workflow['nodes'].append(call_escalation_node)

# Update connections
connections = workflow['connections']

# Parse Input -> Check Bot Muted (parallel with Intent Router)
if 'Parse Input' in connections:
    connections['Parse Input']['main'][0].append({
        "node": "Check Bot Muted",
        "type": "main",
        "index": 0
    })

# Check Bot Muted -> Is Bot Muted?
connections['Check Bot Muted'] = {
    "main": [[{
        "node": "Is Bot Muted?",
        "type": "main",
        "index": 0
    }]]
}

# Is Bot Muted? -> Silent Exit (true) or continue (false - no action needed, parallel check)
connections['Is Bot Muted?'] = {
    "main": [
        [{
            "node": "Silent Exit (Muted)",
            "type": "main",
            "index": 0
        }],
        []  # false branch - do nothing, main flow continues via Intent Router
    ]
}

# Update Is Deadlock to call Escalation Handler
if 'Is Deadlock' in connections:
    # True branch -> Call Escalation Handler instead of Deadlock Response
    connections['Is Deadlock']['main'][0] = [{
        "node": "Call Escalation Handler",
        "type": "main",
        "index": 0
    }]

# Update Check Escalation to call Escalation Handler
# True branch (needs_escalation) -> Call Escalation Handler
if 'Check Escalation' in connections:
    # Replace Me2 with Call Escalation Handler
    for i, conn_list in enumerate(connections['Check Escalation']['main']):
        for j, conn in enumerate(conn_list):
            if conn.get('node') == 'Me2':
                connections['Check Escalation']['main'][i][j] = {
                    "node": "Call Escalation Handler",
                    "type": "main",
                    "index": 0
                }

# Call Escalation Handler -> Prepare Response (to save message and send)
connections['Call Escalation Handler'] = {
    "main": [[{
        "node": "Prepare Response",
        "type": "main",
        "index": 0
    }]]
}

print(f"Updated nodes: {len(workflow['nodes'])}")

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

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())
        print(f"Updated: {result['name']}")
        print("SUCCESS!")
except urllib.error.HTTPError as e:
    print(f"ERROR {e.code}: {e.reason}")
    error_body = e.read().decode()
    print(f"Details: {error_body[:500]}")
