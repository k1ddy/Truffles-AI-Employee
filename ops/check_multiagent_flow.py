#!/usr/bin/env python3
"""Check Multi-Agent workflow structure"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "4vaEvzlaMrgovhNz"

url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

print("=== KEY CONNECTIONS ===")
connections = workflow.get('connections', {})

# Find path from start to response generation
key_nodes = ['Start', 'Parse Input', 'Build Context', 'Is Deadlock', 'Prepare Escalation Data', 'Call Escalation Handler']
for node in key_nodes:
    if node in connections:
        targets = []
        for branch in connections[node].get('main', []):
            targets.extend([c['node'] for c in branch])
        print(f"{node} -> {targets}")

print("\n=== IS DEADLOCK CONNECTIONS ===")
if 'Is Deadlock' in connections:
    for i, branch in enumerate(connections['Is Deadlock']['main']):
        targets = [c['node'] for c in branch]
        print(f"  Branch {i}: {targets}")
