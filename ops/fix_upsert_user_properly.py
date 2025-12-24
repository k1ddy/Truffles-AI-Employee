#!/usr/bin/env python3
"""
FIX UPSERT USER - use explicit Parse Input reference instead of $json
This is the ROOT CAUSE of undefined users!
"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "4vaEvzlaMrgovhNz"

url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print(f"Loaded: {workflow['name']}")

# Fix Upsert User - ALL references must be explicit to Parse Input
for node in workflow['nodes']:
    if node['name'] == 'Upsert User':
        # Replace ALL $json with $('Parse Input').first().json
        node['parameters']['query'] = """WITH client AS (
  SELECT id FROM clients WHERE name = '{{ $('Parse Input').first().json.client_slug }}'
),
upserted_user AS (
  INSERT INTO users (client_id, phone, remote_jid, name, last_active_at)
  SELECT
    (SELECT id FROM client),
    '{{ $('Parse Input').first().json.phone }}',
    '{{ $('Parse Input').first().json.remoteJid }}',
    '{{ $('Parse Input').first().json.senderName }}',
    NOW()
  ON CONFLICT (client_id, phone) DO UPDATE SET
    last_active_at = NOW(),
    name = COALESCE(NULLIF('{{ $('Parse Input').first().json.senderName }}', ''), users.name)
  RETURNING id
),
existing_conv AS (
  SELECT id FROM conversations
  WHERE user_id = (SELECT id FROM upserted_user)
    AND status = 'active'
  ORDER BY last_message_at DESC
  LIMIT 1
),
new_conv AS (
  INSERT INTO conversations (client_id, user_id, channel, status, last_message_at)
  SELECT
    (SELECT id FROM client),
    (SELECT id FROM upserted_user),
    'whatsapp',
    'active',
    NOW()
  WHERE NOT EXISTS (SELECT 1 FROM existing_conv)
  RETURNING id
)
SELECT
  (SELECT id FROM upserted_user) AS user_id,
  COALESCE(
    (SELECT id FROM existing_conv),
    (SELECT id FROM new_conv)
  ) AS conversation_id,
  (SELECT id FROM client) AS client_id;"""
        print("FIXED: Upsert User - now uses explicit $('Parse Input').first().json")

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
    print("SUCCESS - ROOT CAUSE FIXED!")
