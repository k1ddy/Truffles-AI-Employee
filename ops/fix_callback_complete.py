#!/usr/bin/env python3
"""Fix callback workflow completely"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

with open('/tmp/callback.json', 'r') as f:
    workflow = json.load(f)

print(f"Loaded: {workflow['name']}")

# 1. Fix Parse Callback to get message_thread_id (topic)
for node in workflow['nodes']:
    if node['name'] == 'Parse Callback':
        node['parameters']['jsCode'] = '''// Парсим callback от Telegram
const body = $json.body || $json;

// Callback query от кнопки
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
const messageId = callback.message?.message_id;
const chatId = callback.message?.chat?.id;
const topicId = callback.message?.message_thread_id;

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
        print("Fixed: Parse Callback (added topic_id)")

# 2. Fix Take Response to include topic_id and prepare for button removal
for node in workflow['nodes']:
    if node['name'] == 'Take Response':
        node['parameters']['jsCode'] = '''const input = $('Parse Callback').first().json;
const result = $json;

let text;
let success = false;

if (result.id) {
  text = `✅ ${input.manager_name} взял(а) заявку`;
  success = true;
} else {
  text = `⚠️ Заявку уже взял другой менеджер`;
}

return [{
  json: {
    ...input,
    response_text: text,
    success,
    remove_buttons: success
  }
}];'''
        print("Fixed: Take Response")

# 3. Fix Resolve Response
for node in workflow['nodes']:
    if node['name'] == 'Resolve Response':
        node['parameters']['jsCode'] = '''const input = $('Parse Callback').first().json;

return [{
  json: {
    ...input,
    response_text: '🟢 Заявка решена',
    success: true,
    remove_buttons: true
  }
}];'''
        print("Fixed: Resolve Response")

# 4. Fix Notify in Chat - add message_thread_id for topics
for node in workflow['nodes']:
    if node['name'] == 'Notify in Chat':
        node['parameters'] = {
            "method": "POST",
            "url": "=https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/sendMessage",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": '''={
  "chat_id": {{ $('Parse Callback').first().json.chat_id }},
  "message_thread_id": {{ $('Parse Callback').first().json.topic_id || 0 }},
  "reply_to_message_id": {{ $('Parse Callback').first().json.message_id }},
  "text": "{{ $json.response_text }}"
}''',
            "options": {}
        }
        print("Fixed: Notify in Chat (added message_thread_id)")

# 5. Add Remove Buttons node after Answer Callback
remove_buttons_node = {
    "parameters": {
        "method": "POST",
        "url": "=https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/editMessageReplyMarkup",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": '''={
  "chat_id": {{ $('Parse Callback').first().json.chat_id }},
  "message_id": {{ $('Parse Callback').first().json.message_id }},
  "reply_markup": {"inline_keyboard": [[{"text": "{{ $json.success ? '✅ Взято' : '⏳ Ожидает' }}", "callback_data": "noop"}]]}
}''',
        "options": {}
    },
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [1100, 200],
    "id": "cb-remove-btns-001",
    "name": "Update Buttons"
}

# Check if node exists
exists = False
for node in workflow['nodes']:
    if node['name'] == 'Update Buttons':
        exists = True
        node['parameters'] = remove_buttons_node['parameters']
        print("Updated: Update Buttons")

if not exists:
    workflow['nodes'].append(remove_buttons_node)
    print("Added: Update Buttons")

# 6. Update connections - Answer Callback -> Update Buttons -> Notify in Chat
connections = workflow['connections']

# Remove old Answer Callback -> Notify connection
if 'Answer Callback' in connections:
    connections['Answer Callback']['main'] = [[{"node": "Update Buttons", "type": "main", "index": 0}]]

# Add Update Buttons -> Notify in Chat
connections['Update Buttons'] = {
    "main": [[{"node": "Notify in Chat", "type": "main", "index": 0}]]
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
