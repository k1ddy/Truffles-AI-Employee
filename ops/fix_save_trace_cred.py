#!/usr/bin/env python3
"""Fix Save Trace credential"""
import requests

N8N_URL = "https://n8n.truffles.kz"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
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
