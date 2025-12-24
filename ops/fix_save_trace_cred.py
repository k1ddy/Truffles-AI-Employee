#!/usr/bin/env python3
"""Fix Save Trace credential"""
import requests

N8N_URL = "https://n8n.truffles.kz"
API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "4vaEvzlaMrgovhNz"

# Download
print("Downloading workflow...")
r = requests.get(f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}", headers={"X-N8N-API-KEY": API_KEY})
workflow = r.json()

# Fix credential
for node in workflow["nodes"]:
    if node["name"] == "Save Trace":
        node["credentials"] = {
            "postgres": {
                "id": "SUHrbh39Ig0fBusT",
                "name": "ChatbotDB"
            }
        }
        print("Fixed Save Trace credentials")
        break

# Upload
print("Uploading...")
update_payload = {
    "nodes": workflow["nodes"],
    "connections": workflow["connections"],
    "settings": workflow.get("settings", {}),
    "name": workflow.get("name", "Multi-Agent")
}
r = requests.put(f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}", headers={"X-N8N-API-KEY": API_KEY}, json=update_payload)

if r.status_code == 200:
    print("SUCCESS!")
else:
    print(f"FAILED: {r.status_code} - {r.text}")
