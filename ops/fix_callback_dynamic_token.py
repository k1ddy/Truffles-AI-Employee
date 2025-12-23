#!/usr/bin/env python3
"""Fix callback workflow to use dynamic tokens from DB"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

# Download current workflow
url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print(f"Loaded: {workflow['name']}")

# 1. Add "Get Bot Token" node after Parse Callback
get_token_node = {
    "parameters": {
        "operation": "executeQuery",
        "query": "SELECT telegram_bot_token FROM client_settings WHERE telegram_chat_id = '{{ $json.chat_id }}';",
        "options": {}
    },
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.6,
    "position": [-464, 300],
    "id": "cb-get-token-001",
    "name": "Get Bot Token",
    "credentials": {
        "postgres": {
            "id": "SUHrbh39Ig0fBusT",
            "name": "ChatbotDB"
        }
    }
}

# Check if node exists
exists = False
for i, node in enumerate(workflow['nodes']):
    if node['name'] == 'Get Bot Token':
        workflow['nodes'][i] = get_token_node
        exists = True
        print("Updated: Get Bot Token")
        
if not exists:
    workflow['nodes'].append(get_token_node)
    print("Added: Get Bot Token")

# 2. Add "Merge Token" node to combine token with parsed data
merge_token_node = {
    "parameters": {
        "jsCode": """const parsed = $('Parse Callback').first().json;
const tokenResult = $('Get Bot Token').first().json;

return [{
  json: {
    ...parsed,
    bot_token: tokenResult.telegram_bot_token
  }
}];"""
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [-240, 300],
    "id": "cb-merge-token-001",
    "name": "Merge Token"
}

exists = False
for i, node in enumerate(workflow['nodes']):
    if node['name'] == 'Merge Token':
        workflow['nodes'][i] = merge_token_node
        exists = True
        print("Updated: Merge Token")
        
if not exists:
    workflow['nodes'].append(merge_token_node)
    print("Added: Merge Token")

# 3. Update Is Callback to use Merge Token output
# 4. Update Answer Callback to use dynamic token
for node in workflow['nodes']:
    if node['name'] == 'Answer Callback':
        node['parameters']['url'] = "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/answerCallbackQuery"
        print("Updated: Answer Callback (dynamic token)")
        
    if node['name'] == 'Update Buttons':
        node['parameters']['url'] = "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/editMessageReplyMarkup"
        print("Updated: Update Buttons (dynamic token)")
        
    if node['name'] == 'Notify in Chat':
        node['parameters']['url'] = "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/sendMessage"
        print("Updated: Notify in Chat (dynamic token)")

# 5. Update connections
connections = workflow['connections']

# Parse Callback -> Get Bot Token -> Merge Token -> Is Callback?
connections['Parse Callback'] = {
    "main": [[{"node": "Get Bot Token", "type": "main", "index": 0}]]
}
connections['Get Bot Token'] = {
    "main": [[{"node": "Merge Token", "type": "main", "index": 0}]]
}
connections['Merge Token'] = {
    "main": [[{"node": "Is Callback?", "type": "main", "index": 0}]]
}

print("Updated connections")

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
