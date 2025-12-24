#!/usr/bin/env python3
"""Fix adapter to use conversations.telegram_topic_id"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "fFPEbTNlkBSjo66A"

# Download current workflow
url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print(f"Loaded: {workflow['name']}")

# 1. Fix Get Existing Topic to use conversations via handover
for node in workflow['nodes']:
    if node['name'] == 'Get Existing Topic':
        node['parameters']['query'] = """SELECT c.telegram_topic_id 
FROM conversations c
JOIN handovers h ON h.conversation_id = c.id
WHERE h.id = '{{ $json.handover_id }}';"""
        print("Fixed: Get Existing Topic (from conversations)")

# 2. Fix Save Topic ID to update conversations
for node in workflow['nodes']:
    if node['name'] == 'Save Topic ID':
        node['parameters']['query'] = """UPDATE conversations 
SET telegram_topic_id = {{ $json.result.message_thread_id }} 
WHERE id = (SELECT conversation_id FROM handovers WHERE id = '{{ $('Prepare Data').first().json.handover_id }}');"""
        print("Fixed: Save Topic ID (to conversations)")

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
