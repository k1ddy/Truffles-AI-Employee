#!/usr/bin/env python3
"""Fix Send Manager Reply to WhatsApp - use GET not POST"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

# Get working token from Multi-Agent
url = f"https://n8n.truffles.kz/api/v1/workflows/4vaEvzlaMrgovhNz"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    ma_workflow = json.loads(response.read().decode())

chatflow_token = None
for node in ma_workflow['nodes']:
    if node['name'] == 'Send to WhatsApp':
        params = node['parameters'].get('queryParameters', {}).get('parameters', [])
        for p in params:
            if p['name'] == 'token':
                chatflow_token = p['value']
                break

print(f"Chatflow token: {chatflow_token[:20]}..." if chatflow_token else "Token not found!")

# Update callback workflow
url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print(f"Loaded: {workflow['name']}")

for node in workflow['nodes']:
    if node['name'] == 'Send Manager Reply to WhatsApp':
        # Remove method (defaults to GET) and use correct token
        node['parameters'] = {
            "url": "https://app.chatflow.kz/api/v1/send-text",
            "sendQuery": True,
            "queryParameters": {
                "parameters": [
                    {"name": "token", "value": chatflow_token},
                    {"name": "instance_id", "value": "={{ $('Find Handover Data').first().json.instance_id }}"},
                    {"name": "jid", "value": "={{ $('Find Handover Data').first().json.remote_jid }}"},
                    {"name": "msg", "value": "={{ $('Parse Message').first().json.text }}"}
                ]
            },
            "options": {}
        }
        print("Fixed: Send Manager Reply to WhatsApp (GET method)")

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
