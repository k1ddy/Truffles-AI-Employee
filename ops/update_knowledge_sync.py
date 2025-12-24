#!/usr/bin/env python3
"""Update Knowledge Sync workflow via API"""
import json
import requests

WORKFLOW_ID = "zTbaCLWLJN6vPMk4"
API_KEY = "REDACTED_JWT"
N8N_URL = "https://n8n.truffles.kz"

with open("/home/zhan/truffles/ops/Knowledge Sync.json") as f:
    workflow = json.load(f)

# Keep only allowed fields (remove pinData as it may cause issues)
allowed = ["name", "nodes", "connections", "settings", "staticData"]
clean = {k: v for k, v in workflow.items() if k in allowed}
# Debug: print what fields we're sending
print(f"Sending fields: {list(clean.keys())}")

resp = requests.put(
    f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
    headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"},
    json=clean
)

print(f"Status: {resp.status_code}")
print(resp.text[:500] if resp.text else "No response")
