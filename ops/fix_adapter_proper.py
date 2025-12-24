#!/usr/bin/env python3
"""
Proper fix for Telegram Adapter:
- Get conversation_id directly (not via handover)
- Search topic by conversation_id
- Save topic to conversation
"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "fFPEbTNlkBSjo66A"

with open('/tmp/adapter.json', 'r') as f:
    workflow = json.load(f)

print(f"Loaded: {workflow['name']}")

# Fix Get Existing Topic - search by conversation_id directly
for node in workflow['nodes']:
    if node['name'] == 'Get Existing Topic':
        node['parameters']['query'] = """SELECT telegram_topic_id 
FROM conversations 
WHERE id = '{{ $json.conversation_id }}';"""
        print("Fixed: Get Existing Topic (by conversation_id)")

# Fix Save Topic ID - save to conversation directly  
for node in workflow['nodes']:
    if node['name'] == 'Save Topic ID':
        node['parameters']['query'] = """UPDATE conversations 
SET telegram_topic_id = {{ $json.result.message_thread_id }} 
WHERE id = '{{ $('Prepare Data').first().json.conversation_id }}';"""
        print("Fixed: Save Topic ID (to conversation)")

# Fix Prepare Data to expect conversation_id
for node in workflow['nodes']:
    if node['name'] == 'Prepare Data':
        node['parameters']['jsCode'] = """// Получаем данные от Escalation Handler
const input = $json;

// Формируем данные для Telegram
const chatId = input.telegram_chat_id;
const botToken = input.telegram_bot_token;
const phone = input.phone;
const clientName = input.client_name || 'Клиент';
const businessName = input.business_name || input.client_slug || '';
const message = input.message;
const handoverId = input.handover_id;
const conversationId = input.conversation_id;

// Название топика
const topicName = `${phone} ${clientName} [${businessName}]`;

return [{
  json: {
    ...input,
    chat_id: chatId,
    bot_token: botToken,
    topic_name: topicName,
    phone,
    client_name: clientName,
    business_name: businessName,
    message,
    handover_id: handoverId,
    conversation_id: conversationId
  }
}];"""
        print("Fixed: Prepare Data (expects conversation_id)")

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
