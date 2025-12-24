#!/usr/bin/env python3
"""Fix Parse Message for new Parse Callback structure"""
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

# Fix Parse Message
for node in workflow['nodes']:
    if node['name'] == 'Parse Message':
        node['parameters']['jsCode'] = '''// Обработка сообщений менеджера в топике
// Input: Merge Token (который смержил Parse Callback + Bot Token)
const input = $('Merge Token').first().json;

// Проверяем что это message (не callback)
if (input.type !== 'message') return [];

// Проверяем что есть текст и топик
const topicId = input.topic_id;
const text = input.text;
if (!topicId || !text) return [];

// Проверяем что это не бот
if (input.is_bot) return [];

return [{
  json: {
    type: 'manager_reply',
    topic_id: topicId,
    text: text,
    manager_name: input.from_name,
    manager_id: String(input.from_id),
    chat_id: input.chat_id
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
