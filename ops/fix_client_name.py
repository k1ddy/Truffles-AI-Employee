#!/usr/bin/env python3
"""
1. Add client name to Forward to Topic
2. Add client name to Check Active Handover SQL
"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "4vaEvzlaMrgovhNz"

url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print(f"Loaded: {workflow['name']}")

for node in workflow['nodes']:
    # Fix Check Active Handover - add user name
    if node['name'] == 'Check Active Handover':
        node['parameters']['query'] = """SELECT 
  h.id as handover_id,
  h.conversation_id as handover_conversation_id,
  c.telegram_topic_id,
  cs.telegram_chat_id,
  cs.telegram_bot_token,
  COALESCE(u.name, u.phone, 'Клиент') as client_name
FROM conversations c
LEFT JOIN handovers h ON h.conversation_id = c.id AND h.status = 'active'
LEFT JOIN client_settings cs ON cs.client_id = c.client_id
LEFT JOIN users u ON u.id = c.user_id
WHERE c.id = '{{ $('Build Context').first().json.conversation_id }}'
LIMIT 1;"""
        print("Fixed: Check Active Handover (added client_name)")
    
    # Fix Forward to Topic - use client name
    if node['name'] == 'Forward to Topic':
        node['parameters']['bodyParameters']['parameters'][2]['value'] = \
            "=💬 {{ $('Check Active Handover').first().json.client_name }}: {{ $('Build Context').first().json.message }}"
        print("Fixed: Forward to Topic (use client_name)")

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
