#!/usr/bin/env python3
"""Fix MessageBuffer key to include client_slug"""
import json
import urllib.request

WORKFLOW_ID = "3QqFRxapNa29jODD"
API_KEY = "REDACTED_JWT"

# 1. Get current workflow
url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print(f"Got workflow: {workflow['name']}")

# 2. Find and fix "Prepare Keys" node
OLD_CODE = '''// Подготовить данные для буфера
const input = $json;

const bufferKey = `chat:${input.session_id}`;
const timerKey = `timer:${input.session_id}`;'''

NEW_CODE = '''// Подготовить данные для буфера
const input = $json;

// ВАЖНО: ключ включает client_slug чтобы разделять буферы разных клиентов
const bufferKey = `chat:${input.client_slug}:${input.session_id}`;
const timerKey = `timer:${input.client_slug}:${input.session_id}`;'''

found = False
for node in workflow['nodes']:
    if node['name'] == 'Prepare Keys':
        old_js = node['parameters']['jsCode']
        if 'client_slug' not in old_js:
            node['parameters']['jsCode'] = old_js.replace(
                'const bufferKey = `chat:${input.session_id}`;',
                '// ВАЖНО: ключ включает client_slug чтобы разделять буферы разных клиентов\nconst bufferKey = `chat:${input.client_slug}:${input.session_id}`;'
            ).replace(
                'const timerKey = `timer:${input.session_id}`;',
                'const timerKey = `timer:${input.client_slug}:${input.session_id}`;'
            )
            found = True
            print("Fixed Prepare Keys node")
        else:
            print("Already fixed!")
            exit(0)

if not found:
    print("ERROR: Prepare Keys node not found!")
    exit(1)

# 3. Update workflow - send only required fields
update_url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"

# Remove read-only fields
update_payload = {
    "name": workflow["name"],
    "nodes": workflow["nodes"],
    "connections": workflow["connections"],
    "settings": workflow.get("settings", {}),
}

update_data = json.dumps(update_payload).encode('utf-8')

req = urllib.request.Request(
    update_url, 
    data=update_data,
    headers={
        "X-N8N-API-KEY": API_KEY,
        "Content-Type": "application/json"
    },
    method='PUT'
)

with urllib.request.urlopen(req) as response:
    result = json.loads(response.read().decode())
    print(f"Updated workflow: {result['name']}")
    print("SUCCESS!")
