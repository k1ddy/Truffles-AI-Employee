#!/usr/bin/env python3
"""Fix RAG Search to use Build Context explicitly"""
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

for node in workflow['nodes']:
    if node['name'] == 'RAG Search':
        # Change $json to $('Build Context').first().json
        old_code = node['parameters']['jsCode']
        new_code = old_code.replace(
            "const ctx = $json;",
            "const ctx = $('Build Context').first().json;"
        )
        node['parameters']['jsCode'] = new_code
        print("Fixed: RAG Search (explicit Build Context reference)")

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
