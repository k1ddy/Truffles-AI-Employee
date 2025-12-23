#!/usr/bin/env python3
"""Fix Is Deadlock connection - connect Build Context -> Is Deadlock -> RAG Search"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "4vaEvzlaMrgovhNz"

# Load workflow
with open('/tmp/ma.json', 'r') as f:
    workflow = json.load(f)

print(f"Loaded: {workflow['name']}")

connections = workflow['connections']

# Current: Build Context -> RAG Search
# New: Build Context -> Is Deadlock -> [true] Prepare Escalation Data, [false] RAG Search

# 1. Change Build Context output from RAG Search to Is Deadlock
print("\nBefore fix:")
print(f"  Build Context -> {connections.get('Build Context', {})}")
print(f"  Is Deadlock -> {connections.get('Is Deadlock', {})}")

connections['Build Context'] = {
    "main": [[{
        "node": "Is Deadlock",
        "type": "main",
        "index": 0
    }]]
}

# Is Deadlock already has correct outputs:
# - branch 0 (true) -> Prepare Escalation Data
# - branch 1 (false) -> RAG Search

print("\nAfter fix:")
print(f"  Build Context -> {connections['Build Context']}")
print(f"  Is Deadlock -> {connections.get('Is Deadlock', {})}")

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
    print(f"\nUpdated: {result['name']}")
    print("SUCCESS!")
