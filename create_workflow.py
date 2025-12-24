#!/usr/bin/env python3
"""Create a new workflow in n8n"""
import json
import os
import sys
import urllib.request

API_KEY = os.environ.get("N8N_API_KEY")
if not API_KEY:
    print("Missing N8N_API_KEY env var", file=sys.stderr)
    sys.exit(1)

if len(sys.argv) < 2:
    print("Usage: python3 create_workflow.py <workflow.json>")
    sys.exit(1)

workflow_file = sys.argv[1]

with open(workflow_file, 'r', encoding='utf-8') as f:
    workflow = json.load(f)

# Remove read-only fields
for field in ['active', 'id', 'versionId', 'meta', 'createdAt', 'updatedAt']:
    workflow.pop(field, None)

print(f"Creating workflow: {workflow['name']}")

url = "https://n8n.truffles.kz/api/v1/workflows"
data = json.dumps(workflow).encode('utf-8')

req = urllib.request.Request(
    url,
    data=data,
    headers={
        "X-N8N-API-KEY": API_KEY,
        "Content-Type": "application/json"
    },
    method='POST'
)

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())
        print(f"Created workflow ID: {result['id']}")
        print(f"Name: {result['name']}")
        print("SUCCESS!")
except urllib.error.HTTPError as e:
    print(f"ERROR {e.code}: {e.reason}")
    error_body = e.read().decode()
    print(f"Details: {error_body}")
    sys.exit(1)
