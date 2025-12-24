#!/usr/bin/env python3
import requests
import json

API_KEY = "REDACTED_JWT"

resp = requests.get(
    "https://n8n.truffles.kz/api/v1/executions/762735?includeData=true",
    headers={"X-N8N-API-KEY": API_KEY}
)
d = resp.json()

data = d.get("data", {})
result_data = data.get("resultData", {})
run_data = result_data.get("runData", {})

print("Nodes:", list(run_data.keys()))

# Check Restore Webhook Data output
if "Restore Webhook Data" in run_data:
    node = run_data["Restore Webhook Data"][0]
    items = node.get("data", {}).get("main", [[]])[0]
    print("\n=== Restore Webhook Data output ===")
    if items:
        j = items[0].get("json", {})
        print(f"body: {j.get('body')}")
        print(f"headers: {type(j.get('headers'))}")
        print(f"client_slug: {j.get('client_slug')}")
        print(f"webhookUrl: {j.get('webhookUrl')}")
