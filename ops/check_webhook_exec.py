#!/usr/bin/env python3
import requests
import json

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

resp = requests.get(
    "https://n8n.truffles.kz/api/v1/executions/762723?includeData=true",
    headers={"X-N8N-API-KEY": API_KEY}
)
d = resp.json()

data = d.get("data", {})
result_data = data.get("resultData", {})
run_data = result_data.get("runData", {})

# Find Webhook node (might have different name)
for node_name in run_data.keys():
    if "Webhook" in node_name or "webhook" in node_name.lower():
        print(f"=== {node_name} ===")
        node = run_data[node_name][0]
        items = node.get("data", {}).get("main", [[]])[0]
        if items:
            j = items[0].get("json", {})
            print(f"params: {j.get('params')}")
            print(f"webhookUrl: {j.get('webhookUrl')}")
            print(f"All keys: {list(j.keys())[:10]}")

# Check Restore Webhook Data
if "Restore Webhook Data" in run_data:
    print("\n=== Restore Webhook Data ===")
    node = run_data["Restore Webhook Data"][0]
    items = node.get("data", {}).get("main", [[]])[0]
    if items:
        j = items[0].get("json", {})
        print(f"client_slug: {j.get('client_slug')}")
        print(f"webhookUrl: {j.get('webhookUrl')}")
