#!/usr/bin/env python3
"""Fix Parse Callback to handle UUID with underscores"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

# Load workflow
with open('/tmp/callback.json', 'r') as f:
    workflow = json.load(f)

print(f"Loaded: {workflow['name']}")

# Fix Parse Callback node
for node in workflow['nodes']:
    if node['name'] == 'Parse Callback':
        node['parameters']['jsCode'] = '''// Парсим callback от Telegram
const body = $json.body || $json;

// Callback query от кнопки
const callback = body.callback_query;
if (!callback) {
  // Это обычное сообщение, не callback
  return [{ json: { type: 'message', data: body.message } }];
}

const data = callback.data; // 'take_uuid' или 'skip_uuid' или 'resolve_uuid'

// Split only on first underscore to preserve UUID
const firstUnderscore = data.indexOf('_');
const action = data.substring(0, firstUnderscore);
const handoverId = data.substring(firstUnderscore + 1);

const from = callback.from;
const managerName = from.first_name + (from.last_name ? ' ' + from.last_name : '');
const managerId = from.id.toString();
const messageId = callback.message?.message_id;
const chatId = callback.message?.chat?.id;

return [{
  json: {
    type: 'callback',
    action,
    handover_id: handoverId,
    manager_id: managerId,
    manager_name: managerName,
    callback_query_id: callback.id,
    message_id: messageId,
    chat_id: chatId
  }
}];'''
        print("Fixed: Parse Callback")

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
