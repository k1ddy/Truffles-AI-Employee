#!/usr/bin/env python3
"""Final fix for Escalation Handler - all fixes combined"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "7jGZrdbaAAvtTnQX"

# Get current workflow
url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print(f"Loaded: {workflow['name']}")

# Fix ALL nodes
for node in workflow['nodes']:
    
    # 1. Load Status - include telegram_bot_token
    if node['name'] == 'Load Status':
        node['parameters']['query'] = """SELECT 
  c.bot_status,
  c.no_count,
  c.bot_muted_until,
  cs.telegram_chat_id,
  cs.telegram_bot_token,
  cs.silence_after_first_no_minutes,
  cs.max_retry_offers,
  cl.name as client_name,
  cl.config->>'instance_id' as instance_id
FROM conversations c
JOIN clients cl ON c.client_id = cl.id
LEFT JOIN client_settings cs ON cs.client_id = cl.id
WHERE c.id = '{{ $json.conversation_id }}';"""
        print("Fixed: Load Status")
    
    # 2. Decide Action - pass all data including telegram_bot_token
    elif node['name'] == 'Decide Action':
        node['parameters']['jsCode'] = """const input = $('Start').first().json;
const status = $json;

const botStatus = status.bot_status || 'active';
const noCount = status.no_count || 0;
const mutedUntil = status.bot_muted_until ? new Date(status.bot_muted_until) : null;
const now = new Date();

const silenceMinutes = status.silence_after_first_no_minutes || 30;
const maxRetries = status.max_retry_offers || 1;

const isMuted = botStatus === 'muted' && mutedUntil && now < mutedUntil;

let action = 'process';
let responseText = null;
let shouldMute = false;
let newNoCount = noCount;

if (isMuted) {
  action = 'silent_exit';
} else if (input.reason === 'human_request') {
  newNoCount = noCount + 1;
  if (newNoCount === 1) {
    responseText = 'Передаю ваш вопрос менеджеру — свяжется в ближайшее время.';
    shouldMute = true;
  } else {
    action = 'silent_exit';
  }
} else if (input.reason === 'frustration') {
  responseText = 'Понимаю, что ситуация неприятная. Передаю менеджеру — свяжется с вами лично.';
  shouldMute = true;
  newNoCount = noCount + 1;
} else {
  responseText = input.bot_response || 'Уточню у коллег и вернусь с ответом.';
}

return [{
  json: {
    ...input,
    current_bot_status: botStatus,
    current_no_count: noCount,
    is_muted: isMuted,
    action,
    response_text: responseText,
    should_mute: shouldMute,
    new_no_count: newNoCount,
    silence_minutes: silenceMinutes,
    telegram_chat_id: status.telegram_chat_id,
    telegram_bot_token: status.telegram_bot_token,
    client_name: status.client_name,
    instance_id: status.instance_id
  }
}];"""
        print("Fixed: Decide Action")
    
    # 3. Update Conversation - use Decide Action data
    elif node['name'] == 'Update Conversation':
        node['parameters']['query'] = """UPDATE conversations SET
  bot_status = CASE WHEN {{ $('Decide Action').first().json.should_mute }} THEN 'muted' ELSE bot_status END,
  bot_muted_until = CASE WHEN {{ $('Decide Action').first().json.should_mute }} THEN NOW() + INTERVAL '{{ $('Decide Action').first().json.silence_minutes }} minutes' ELSE bot_muted_until END,
  no_count = {{ $('Decide Action').first().json.new_no_count }}
WHERE id = '{{ $('Decide Action').first().json.conversation_id }}';"""
        print("Fixed: Update Conversation")
    
    # 4. Create Handover - use Decide Action data + trigger_type
    elif node['name'] == 'Create Handover':
        node['parameters']['query'] = """INSERT INTO handovers (
  conversation_id,
  client_id,
  user_message,
  status,
  trigger_type,
  trigger_value,
  escalation_reason
) VALUES (
  '{{ $('Decide Action').first().json.conversation_id }}',
  '{{ $('Decide Action').first().json.client_id }}',
  '{{ $('Decide Action').first().json.message.replace(/'/g, "''") }}',
  'pending',
  'intent',
  '{{ $('Decide Action').first().json.reason }}',
  '{{ $('Decide Action').first().json.reason }}'
) RETURNING id;"""
        print("Fixed: Create Handover")

# 5. Replace Send to Telegram with HTTP Request
for i, node in enumerate(workflow['nodes']):
    if node['name'] == 'Send to Telegram' and node['type'] == 'n8n-nodes-base.telegram':
        workflow['nodes'][i] = {
            "parameters": {
                "method": "POST",
                "url": "=https://api.telegram.org/bot{{ $('Decide Action').first().json.telegram_bot_token }}/sendMessage",
                "sendBody": True,
                "bodyParameters": {
                    "parameters": [
                        {"name": "chat_id", "value": "={{ $('Decide Action').first().json.telegram_chat_id }}"},
                        {"name": "text", "value": "=🚨 ЭСКАЛАЦИЯ\n\n👤 Клиент: {{ $('Decide Action').first().json.client_name }}\n📱 Телефон: {{ $('Decide Action').first().json.phone }}\n💬 Сообщение: {{ $('Decide Action').first().json.message }}\n\n📋 Причина: {{ $('Decide Action').first().json.reason }}\n🆔 Handover: {{ $('Create Handover').first().json.id }}"}
                    ]
                },
                "options": {}
            },
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": node['position'],
            "id": node['id'],
            "name": "Send to Telegram"
        }
        print("Fixed: Send to Telegram (HTTP Request)")

# 6. Replace Notify Admin with HTTP Request
for i, node in enumerate(workflow['nodes']):
    if node['name'] == 'Notify Admin' and node['type'] == 'n8n-nodes-base.telegram':
        workflow['nodes'][i] = {
            "parameters": {
                "method": "POST",
                "url": "https://api.telegram.org/bot8045341599:AAGY1vnqoebErB7Ki5iAqHusgLqf9WwA5m4/sendMessage",
                "sendBody": True,
                "bodyParameters": {
                    "parameters": [
                        {"name": "chat_id", "value": "1969855532"},
                        {"name": "text", "value": "=⚠️ Эскалация без Telegram группы!\n\nКлиент: {{ $('Decide Action').first().json.client_name }}\nНужно настроить telegram_chat_id в client_settings"}
                    ]
                },
                "options": {}
            },
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": node['position'],
            "id": node['id'],
            "name": "Notify Admin"
        }
        print("Fixed: Notify Admin (HTTP Request)")

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
    print(f"\nUpdated: {result['name']}")
    print("ALL FIXES APPLIED!")
