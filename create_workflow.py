#!/usr/bin/env python3
"""Create a new workflow in n8n"""
import json
import sys
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

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
