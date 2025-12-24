#!/usr/bin/env python3
"""Fix Parse Callback to always output chat_id at top level"""
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

# Fix Parse Callback to always output chat_id at top level
for node in workflow['nodes']:
    if node['name'] == 'Parse Callback':
        node['parameters']['jsCode'] = '''// Парсим update от Telegram (callback или message)
const body = $json.body || $json;

// CALLBACK (кнопка нажата)
const callback = body.callback_query;
if (callback) {
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
  }];
}

// MESSAGE (обычное сообщение в топике)
const msg = body.message;
if (msg) {
  const chatId = msg.chat?.id;
  const topicId = msg.message_thread_id;
  const text = msg.text || '';
  const from = msg.from || {};
  
  return [{
    json: {
      type: 'message',
      chat_id: chatId,
      topic_id: topicId,
      message_id: msg.message_id,
      text: text,
      from_id: from.id,
      from_name: from.first_name + (from.last_name ? ' ' + from.last_name : ''),
      is_bot: from.is_bot || false,
      message: msg  // полный объект для Parse Message
    }
  }];
}

return [];'''
        print("Fixed: Parse Callback (chat_id at top level)")

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
