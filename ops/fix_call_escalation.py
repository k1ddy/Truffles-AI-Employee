#!/usr/bin/env python3
"""Fix Call Escalation Handler - add prep node and use autoMapInputData"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "4vaEvzlaMrgovhNz"

# Get current workflow
with open('/tmp/ma.json', 'r') as f:
    workflow = json.load(f)

print(f"Loaded: {workflow['name']}")

# 1. Add "Prepare Escalation Data" node
prep_node = {
    "parameters": {
        "jsCode": """// Собираем данные для Escalation Handler
const ctx = $('Build Context').first().json;
const genResponse = $json.output || {};

return [{
  json: {
    conversation_id: ctx.conversation_id,
    client_id: ctx.client_id,
    phone: ctx.phone,
    remoteJid: ctx.remoteJid,
    message: ctx.message,
    reason: ctx.deadlockReason || 'escalation',
    bot_response: genResponse.response || ''
  }
}];"""
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [-850, 400],
    "id": "prep-escalation-001",
    "name": "Prepare Escalation Data"
}

# 2. Update Call Escalation Handler to use autoMapInputData
call_node_found = False
for node in workflow['nodes']:
    if node['name'] == 'Call Escalation Handler':
        node['parameters']['workflowInputs'] = {
            "mappingMode": "autoMapInputData",
            "value": {}
        }
        call_node_found = True
        print("Updated: Call Escalation Handler (autoMapInputData)")

# Add prep node
workflow['nodes'].append(prep_node)
print("Added: Prepare Escalation Data node")

# 3. Update connections
connections = workflow['connections']

# Find what connects to Call Escalation Handler and insert prep node
# Currently: Check Escalation -> Call Escalation Handler
# New: Check Escalation -> Prepare Escalation Data -> Call Escalation Handler

# Also: Is Deadlock -> Call Escalation Handler
# New: Is Deadlock -> Prepare Escalation Data -> Call Escalation Handler

# Update Check Escalation connections
if 'Check Escalation' in connections:
    for i, branch in enumerate(connections['Check Escalation']['main']):
        for j, conn in enumerate(branch):
            if conn.get('node') == 'Call Escalation Handler':
                connections['Check Escalation']['main'][i][j] = {
                    "node": "Prepare Escalation Data",
                    "type": "main",
                    "index": 0
                }
                print("Updated: Check Escalation -> Prepare Escalation Data")

# Update Is Deadlock connections
if 'Is Deadlock' in connections:
    for i, branch in enumerate(connections['Is Deadlock']['main']):
        for j, conn in enumerate(branch):
            if conn.get('node') == 'Call Escalation Handler':
                connections['Is Deadlock']['main'][i][j] = {
                    "node": "Prepare Escalation Data",
                    "type": "main",
                    "index": 0
                }
                print("Updated: Is Deadlock -> Prepare Escalation Data")

# Add Prepare Escalation Data -> Call Escalation Handler
connections['Prepare Escalation Data'] = {
    "main": [[{
        "node": "Call Escalation Handler",
        "type": "main",
        "index": 0
    }]]
}
print("Added: Prepare Escalation Data -> Call Escalation Handler")

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
