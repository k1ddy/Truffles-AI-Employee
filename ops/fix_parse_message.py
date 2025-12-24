#!/usr/bin/env python3
"""Fix Parse Message to handle webhook format correctly"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

# Download workflow
url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print(f"Loaded: {workflow['name']}")

# Fix Parse Message
for node in workflow['nodes']:
    if node['name'] == 'Parse Message':
        node['parameters']['jsCode'] = '''// Обработка обычных сообщений (ответы менеджера в топике)
// Input: данные из Merge Token (который получил body от webhook)
const body = $('Merge Token').first().json;

// Проверяем что это message (не callback)
const msg = body.message;
if (!msg || !msg.text) return [];

// Проверяем что это в топике (forum thread)
const topicId = msg.message_thread_id;
if (!topicId) return []; // Не в топике - игнорируем

// Проверяем что это не бот сам себе
const from = msg.from;
if (from.is_bot) return [];

const text = msg.text;
const managerName = from.first_name + (from.last_name ? ' ' + from.last_name : '');
const managerId = from.id.toString();
const chatId = msg.chat.id;

return [{
  json: {
    type: 'manager_reply',
    topic_id: topicId,
    text,
    manager_name: managerName,
    manager_id: managerId,
    chat_id: chatId
  }
}];'''
        print("Fixed: Parse Message")

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
