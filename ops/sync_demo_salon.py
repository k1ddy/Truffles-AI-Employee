#!/usr/bin/env python3
"""Manual sync for demo_salon - workaround for nested loop bug"""
import requests
import hashlib
import json

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

# Google Drive files for demo_salon (from check output)
DEMO_SALON_FILES = [
    {"id": "1abc123", "name": "rules.md"},
    {"id": "2def456", "name": "objections.md"}, 
    {"id": "3ghi789", "name": "faq.md"},
    {"id": "4jkl012", "name": "services.md"},
]

CLIENT_SLUG = "demo_salon"

# This is a workaround. The real fix requires restructuring the workflow.
# For now, I'll trigger the workflow with modified data.

print("This script needs the actual Google Drive file IDs.")
print("Let me get them from the execution data...")

# Get file IDs from last execution
resp = requests.get(
    "https://n8n.truffles.kz/api/v1/executions/762651?includeData=true",
    headers={"X-N8N-API-KEY": API_KEY}
)
d = resp.json()
data = d.get("data", {})
result_data = data.get("resultData", {})
run_data = result_data.get("runData", {})

# Get demo_salon files from Prepare Docs List
if "Prepare Docs List" in run_data:
    for ex in run_data["Prepare Docs List"]:
        items = ex.get("data", {}).get("main", [[]])[0]
        for item in items:
            j = item.get("json", {})
            if j.get("client_slug") == "demo_salon":
                print(f"Found: {j.get('doc_name')} - ID: {j.get('doc_id')}")
