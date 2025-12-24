#!/usr/bin/env python3
"""Update Escalation Handler to use Telegram Adapter"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "7jGZrdbaAAvtTnQX"
TELEGRAM_ADAPTER_ID = "fFPEbTNlkBSjo66A"

# Get current workflow
url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print(f"Loaded: {workflow['name']}")

# 1. Update Load Status to also get user_id
for node in workflow['nodes']:
    if node['name'] == 'Load Status':
        node['parameters']['query'] = """SELECT 
  c.bot_status,
  c.no_count,
  c.bot_muted_until,
  c.user_id,
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
        print("Updated: Load Status (added user_id)")

# 2. Update Decide Action to pass user_id
for node in workflow['nodes']:
    if node['name'] == 'Decide Action':
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
        print("Updated: Decide Action (added user_id)")

# 3. Replace Send to Telegram with Call Telegram Adapter
for i, node in enumerate(workflow['nodes']):
    if node['name'] == 'Send to Telegram':
        workflow['nodes'][i] = {
            "parameters": {
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
                        "user_id": "={{ $('Decide Action').first().json.user_id }}"
                    }
                },
                "options": {}
            },
            "type": "n8n-nodes-base.executeWorkflow",
            "typeVersion": 1.2,
            "position": node['position'],
            "id": node['id'],
            "name": "Call Telegram Adapter"
        }
        print("Replaced: Send to Telegram -> Call Telegram Adapter")

# Update connection names
connections = workflow['connections']
for source in list(connections.keys()):
    if 'main' in connections[source]:
        for branch in connections[source]['main']:
            for conn in branch:
                if conn.get('node') == 'Send to Telegram':
                    conn['node'] = 'Call Telegram Adapter'

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
