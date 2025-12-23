#!/usr/bin/env python3
"""Fix Notify in Chat - use correct reference for response_text"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

# Download current workflow
url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print(f"Loaded: {workflow['name']}")

# Fix Notify in Chat - correct reference path
for node in workflow['nodes']:
    if node['name'] == 'Notify in Chat':
        node['parameters'] = {
            "method": "POST",
            "url": "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/sendMessage",
            "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "chat_id", "value": "={{ $('Merge Token').first().json.chat_id }}"},
                    {"name": "message_thread_id", "value": "={{ $('Merge Token').first().json.topic_id }}"},
                    {"name": "text", "value": "={{ $('Take Response').first().json.response_text }}"}
                ]
            },
            "options": {}
        }
        print("Fixed: Notify in Chat (correct text reference)")

# Also need to ensure connection passes response_text
# Update Buttons -> Notify in Chat, but Update Buttons doesn't have response_text
# Need to check flow and fix data passing

# Actually, let me check the connections
connections = workflow.get('connections', {})
print("\nConnections to Notify in Chat:")
for src, conns in connections.items():
    if 'main' in conns:
        for branch in conns['main']:
            for c in branch:
                if c.get('node') == 'Notify in Chat':
                    print(f"  {src} -> Notify in Chat")

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
