#!/usr/bin/env python3
import requests
import json

API_KEY = "REDACTED_JWT"

resp = requests.get(
    "https://n8n.truffles.kz/api/v1/executions/762736?includeData=true",
    headers={"X-N8N-API-KEY": API_KEY}
)
d = resp.json()

data = d.get("data", {})
result_data = data.get("resultData", {})
run_data = result_data.get("runData", {})

# Check Start node (input)
if "Start" in run_data:
    node = run_data["Start"][0]
    items = node.get("data", {}).get("main", [[]])[0]
    print("=== Input to ChannelAdapter ===")
    if items:
        j = items[0].get("json", {})
        print(json.dumps(j, indent=2, ensure_ascii=False)[:1000])
