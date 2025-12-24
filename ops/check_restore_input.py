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

# Check Respond to Webhook1 (input to Restore Webhook Data)
if "Respond to Webhook1" in run_data:
    node = run_data["Respond to Webhook1"][0]
    items = node.get("data", {}).get("main", [[]])[0]
    print("=== Respond to Webhook1 output ===")
    if items:
        j = items[0].get("json", {})
        print(f"Keys: {list(j.keys())}")

# Check Webhook node output
if "Webhook" in run_data:
    node = run_data["Webhook"][0]
    items = node.get("data", {}).get("main", [[]])[0]
    print("\n=== Webhook output ===")
    if items:
        j = items[0].get("json", {})
        print(f"Keys: {list(j.keys())}")
        print(f"body present: {j.get('body') is not None}")
        print(f"params: {j.get('params')}")
