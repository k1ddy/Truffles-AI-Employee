#!/usr/bin/env python3
"""Fix Save Channel Refs to get message_id from Send Escalation"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
ADAPTER_ID = "fFPEbTNlkBSjo66A"

url = f"https://n8n.truffles.kz/api/v1/workflows/{ADAPTER_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print(f"Loaded: {workflow['name']}")

# Fix Save Channel Refs - explicit reference to Send Escalation
for node in workflow['nodes']:
    if node['name'] == 'Save Channel Refs':
        node['parameters']['query'] = """UPDATE handovers 
SET channel = 'telegram', 
    channel_ref = '{{ $('Get Topic ID').first().json.topic_id }}', 
    telegram_message_id = {{ $('Send Escalation').first().json.result.message_id }}
WHERE id = '{{ $('Prepare Data').first().json.handover_id }}';"""
        print("Fixed: Save Channel Refs (explicit Send Escalation reference)")

# Update workflow
update_payload = {
    "name": workflow["name"],
    "nodes": workflow["nodes"],
    "connections": workflow["connections"],
    "settings": workflow.get("settings", {}),
}

url = f"https://n8n.truffles.kz/api/v1/workflows/{ADAPTER_ID}"
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
