#!/usr/bin/env python3
"""Protect Upsert User from creating users with undefined/empty phone"""
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

# Fix Upsert User - add validation for phone
for node in workflow['nodes']:
    if node['name'] == 'Upsert User':
        # Add WHERE clause to prevent undefined phones
        node['parameters']['query'] = """WITH client AS (
  SELECT id FROM clients WHERE name = '{{ $('Parse Input').first().json.client_slug }}'
),
input_check AS (
  -- Validate phone is not undefined/empty
  SELECT 
    CASE 
      WHEN '{{ $json.phone }}' IN ('undefined', 'unknown', '', 'null') THEN NULL
      ELSE '{{ $json.phone }}'
    END as phone,
    '{{ $json.remoteJid }}' as remote_jid,
    '{{ $json.senderName }}' as sender_name
),
upserted_user AS (
  INSERT INTO users (client_id, phone, remote_jid, name, last_active_at)
  SELECT
    (SELECT id FROM client),
    (SELECT phone FROM input_check),
    (SELECT remote_jid FROM input_check),
    (SELECT sender_name FROM input_check),
    NOW()
  WHERE (SELECT phone FROM input_check) IS NOT NULL
  ON CONFLICT (client_id, phone) DO UPDATE SET
    last_active_at = NOW(),
    name = COALESCE(NULLIF((SELECT sender_name FROM input_check), ''), users.name)
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
    AND (SELECT id FROM upserted_user) IS NOT NULL
  RETURNING id
)
SELECT
  (SELECT id FROM upserted_user) AS user_id,
  COALESCE(
    (SELECT id FROM existing_conv),
    (SELECT id FROM new_conv)
  ) AS conversation_id,
  (SELECT id FROM client) AS client_id;"""
        print("Fixed: Upsert User (protected from undefined phone)")

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
