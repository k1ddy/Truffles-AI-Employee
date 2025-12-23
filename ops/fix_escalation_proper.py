#!/usr/bin/env python3
"""
Proper fix for Escalation Handler:
- Pass conversation_id to adapter
- Use FIXED response text (no LLM)
"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "7jGZrdbaAAvtTnQX"
TELEGRAM_ADAPTER_ID = "fFPEbTNlkBSjo66A"

with open('/tmp/escalation.json', 'r') as f:
    workflow = json.load(f)

print(f"Loaded: {workflow['name']}")

# Fix Decide Action - use FIXED text, no LLM variations
for node in workflow['nodes']:
    if node['name'] == 'Decide Action':
        node['parameters']['jsCode'] = """const input = $('Start').first().json;
const status = $json;

const botStatus = status.bot_status || 'active';
const noCount = status.no_count || 0;
const mutedUntil = status.bot_muted_until ? new Date(status.bot_muted_until) : null;
const now = new Date();

const silenceMinutes = status.silence_after_first_no_minutes || 30;

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
    // ФИКСИРОВАННЫЙ текст, без вариаций
    responseText = 'Передаю ваш вопрос менеджеру — свяжется в ближайшее время.';
    shouldMute = true;
  } else {
    action = 'silent_exit';
  }
} else if (input.reason === 'frustration') {
  responseText = 'Понимаю, передаю менеджеру — свяжется с вами лично.';
  shouldMute = true;
  newNoCount = noCount + 1;
} else {
  // Для других случаев - тоже фиксированный текст
  responseText = 'Уточню у коллег и вернусь с ответом.';
}

return [{
  json: {
    ...input,
    conversation_id: input.conversation_id,
    user_id: status.user_id,
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
        print("Fixed: Decide Action (fixed text, no LLM)")

# Fix Call Telegram Adapter - pass conversation_id
for node in workflow['nodes']:
    if node['name'] == 'Call Telegram Adapter':
        node['parameters'] = {
            "workflowId": {
                "__rl": True,
                "value": TELEGRAM_ADAPTER_ID,
                "mode": "id"
            },
            "workflowInputs": {
                "mappingMode": "defineBelow",
                "value": {
                    "telegram_chat_id": "={{ $('Decide Action').first().json.telegram_chat_id }}",
                    "telegram_bot_token": "={{ $('Decide Action').first().json.telegram_bot_token }}",
                    "phone": "={{ $('Decide Action').first().json.phone }}",
                    "client_name": "={{ $('Decide Action').first().json.client_name }}",
                    "client_slug": "={{ $('Start').first().json.client_slug }}",
                    "business_name": "={{ $('Decide Action').first().json.client_name }}",
                    "message": "={{ $('Decide Action').first().json.message }}",
                    "handover_id": "={{ $('Create Handover').first().json.id }}",
                    "conversation_id": "={{ $('Decide Action').first().json.conversation_id }}"
                }
            },
            "options": {}
        }
        print("Fixed: Call Telegram Adapter (passes conversation_id)")

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
