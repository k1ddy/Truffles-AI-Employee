#!/usr/bin/env python3
"""Fix escalation: proper mute + clean response text"""

import json
import requests

API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4'

# Get 7_Escalation_Handler
resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows',
    headers={'X-N8N-API-KEY': API_KEY}
)
wf_id = None
for w in resp.json()['data']:
    if '7_Escalation' in w['name']:
        wf_id = w['id']
        break

print(f"Found: {wf_id}")

resp = requests.get(
    f'https://n8n.truffles.kz/api/v1/workflows/{wf_id}',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()

# Fix Decide Action - clean response texts
for node in data['nodes']:
    if node['name'] == 'Decide Action':
        node['parameters']['jsCode'] = """const input = $('Start').first().json;
const status = $json;

const botStatus = status.bot_status || 'active';
const noCount = status.no_count || 0;
const mutedUntil = status.bot_muted_until ? new Date(status.bot_muted_until) : null;
const now = new Date();

const silenceMinutes = status.silence_after_first_no_minutes || 120;

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
    responseText = 'Секунду, переключаю на менеджера.';
    shouldMute = true;
  } else {
    action = 'silent_exit';
  }
} else if (input.reason === 'frustration') {
  responseText = 'Сейчас позову менеджера.';
  shouldMute = true;
  newNoCount = noCount + 1;
} else {
  responseText = 'Уточню и вернусь с ответом.';
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
        print("Fixed Decide Action - clean responses")
        break

# Update
resp = requests.put(
    f'https://n8n.truffles.kz/api/v1/workflows/{wf_id}',
    headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
    json={
        'name': data['name'],
        'nodes': data['nodes'],
        'connections': data['connections'],
        'settings': data.get('settings', {})
    }
)
print(f"Status: {resp.status_code}")
