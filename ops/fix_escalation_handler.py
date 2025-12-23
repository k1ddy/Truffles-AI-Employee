#!/usr/bin/env python3
"""Fix Escalation Handler - all fixes in one"""
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

# Fix all nodes
for node in workflow['nodes']:
    
    if node['name'] == 'Update Conversation':
        node['parameters']['query'] = """UPDATE conversations SET
  bot_status = CASE WHEN {{ $('Decide Action').first().json.should_mute }} THEN 'muted' ELSE bot_status END,
  bot_muted_until = CASE WHEN {{ $('Decide Action').first().json.should_mute }} THEN NOW() + INTERVAL '{{ $('Decide Action').first().json.silence_minutes }} minutes' ELSE bot_muted_until END,
  no_count = {{ $('Decide Action').first().json.new_no_count }}
WHERE id = '{{ $('Decide Action').first().json.conversation_id }}';"""
        print("Fixed: Update Conversation")
        
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
    
    elif node['name'] == 'Notify Admin':
        # Remove parse_mode to avoid entity parsing errors with special characters
        if 'additionalFields' in node['parameters']:
            node['parameters']['additionalFields'].pop('parse_mode', None)
        print("Fixed: Notify Admin (removed parse_mode)")
    
    elif node['name'] == 'Send to Telegram':
        # Remove parse_mode to avoid entity parsing errors
        if 'additionalFields' in node['parameters']:
            node['parameters']['additionalFields'].pop('parse_mode', None)
        print("Fixed: Send to Telegram (removed parse_mode)")

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
