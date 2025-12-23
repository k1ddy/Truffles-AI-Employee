#!/usr/bin/env python3
import requests
import json

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

# Download current workflow
print("Downloading current workflow...")
resp = requests.get(
    "https://n8n.truffles.kz/api/v1/workflows/656fmXR6GPZrJbxm",
    headers={"X-N8N-API-KEY": API_KEY}
)
workflow = resp.json()

# Find and fix Restore Webhook Data node
fixed = False
for node in workflow.get("nodes", []):
    if node.get("name") == "Restore Webhook Data":
        params = node.get("parameters", {})
        assignments = params.get("assignments", {}).get("assignments", [])
        for a in assignments:
            if a.get("name") == "client_slug":
                old_value = a.get("value")
                new_value = "={{ $json.params?.client || 'truffles' }}"
                if old_value != new_value:
                    print(f"Old value: {old_value}")
                    print(f"New value: {new_value}")
                    a["value"] = new_value
                    fixed = True
                else:
                    print("Already fixed!")

if fixed:
    # Upload fixed workflow
    allowed = ["name", "nodes", "connections", "settings", "staticData"]
    clean = {k: v for k, v in workflow.items() if k in allowed}
    
    resp = requests.put(
        "https://n8n.truffles.kz/api/v1/workflows/656fmXR6GPZrJbxm",
        headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"},
        json=clean
    )
    print(f"Upload status: {resp.status_code}")
else:
    print("No changes needed")
