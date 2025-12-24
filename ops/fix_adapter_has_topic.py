#!/usr/bin/env python3
"""Fix Has Topic? node to handle string topic_id"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "fFPEbTNlkBSjo66A"

with open('/tmp/adapter.json', 'r') as f:
    workflow = json.load(f)

print(f"Loaded: {workflow['name']}")

# Fix Has Topic? to check if value exists (not empty string or null)
for node in workflow['nodes']:
    if node['name'] == 'Has Topic?':
        node['parameters'] = {
            "conditions": {
                "options": {
                    "caseSensitive": True,
                    "leftValue": "",
                    "typeValidation": "loose",
                    "version": 2
                },
                "conditions": [
                    {
                        "id": "has-topic",
                        "leftValue": "={{ $json.telegram_topic_id }}",
                        "rightValue": "",
                        "operator": {
                            "type": "string",
                            "operation": "notEmpty"
                        }
                    }
                ],
                "combinator": "and"
            },
            "options": {}
        }
        print("Fixed: Has Topic? (string check)")

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
