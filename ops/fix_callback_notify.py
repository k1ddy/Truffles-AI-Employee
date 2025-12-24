#!/usr/bin/env python3
"""Fix callback workflow - Notify in Chat topic_id issue"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

# Download current workflow
url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print(f"Loaded: {workflow['name']}")

# Fix Parse Callback to get message_thread_id properly
for node in workflow['nodes']:
    if node['name'] == 'Parse Callback':
        node['parameters']['jsCode'] = '''// Парсим callback от Telegram
const body = $json.body || $json;

const callback = body.callback_query;
if (!callback) {
  return [{ json: { type: 'message', data: body.message } }];
}

const data = callback.data;
const firstUnderscore = data.indexOf('_');
const action = data.substring(0, firstUnderscore);
const handoverId = data.substring(firstUnderscore + 1);

const from = callback.from;
const managerName = from.first_name + (from.last_name ? ' ' + from.last_name : '');
const managerId = from.id.toString();
const message = callback.message;
const messageId = message?.message_id;
const chatId = message?.chat?.id;
// message_thread_id это topic_id в Forum группе
const topicId = message?.message_thread_id;

return [{
  json: {
    type: 'callback',
    action,
    handover_id: handoverId,
    manager_id: managerId,
    manager_name: managerName,
    callback_query_id: callback.id,
    message_id: messageId,
    chat_id: chatId,
    topic_id: topicId
  }
}];'''
        print("Fixed: Parse Callback (proper topic_id)")

# Fix Notify in Chat - handle null topic_id gracefully
for node in workflow['nodes']:
    if node['name'] == 'Notify in Chat':
        # Use bodyParameters instead of jsonBody to avoid JSON issues
        node['parameters'] = {
            "method": "POST",
            "url": "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/sendMessage",
            "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "chat_id", "value": "={{ $('Merge Token').first().json.chat_id }}"},
                    {"name": "message_thread_id", "value": "={{ $('Merge Token').first().json.topic_id }}"},
                    {"name": "text", "value": "={{ $json.response_text }}"}
                ]
            },
            "options": {}
        }
        print("Fixed: Notify in Chat (bodyParameters)")

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
