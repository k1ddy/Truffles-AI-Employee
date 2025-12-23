#!/usr/bin/env python3
import requests
import json

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

resp = requests.get(
    "https://n8n.truffles.kz/api/v1/executions/762736?includeData=true",
    headers={"X-N8N-API-KEY": API_KEY}
)
d = resp.json()

print(f"Status: {d.get('status')}")

data = d.get("data", {})
result_data = data.get("resultData", {})
run_data = result_data.get("runData", {})

print(f"Nodes: {list(run_data.keys())}")

# Check WhatsApp Adapter output
if "WhatsApp Adapter" in run_data:
    node = run_data["WhatsApp Adapter"][0]
    items = node.get("data", {}).get("main", [[]])[0]
    print(f"\nWhatsApp Adapter output: {len(items)} items")
    if items:
        j = items[0].get("json", {})
        print(f"Keys: {list(j.keys())}")
        print(f"client_slug: {j.get('client_slug')}")
    else:
        print("NO OUTPUT - message filtered out!")

# Check error
error = result_data.get("error")
if error:
    print(f"\nError: {json.dumps(error, indent=2)[:300]}")
