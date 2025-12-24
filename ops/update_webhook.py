#!/usr/bin/env python3
import requests
import json

API_KEY = "REDACTED_JWT"

with open("/home/zhan/truffles/ops/1_Webhook_656fmXR6GPZrJbxm.json") as f:
    workflow = json.load(f)

allowed = ["name", "nodes", "connections", "settings", "staticData"]
clean = {k: v for k, v in workflow.items() if k in allowed}

resp = requests.put(
    "https://n8n.truffles.kz/api/v1/workflows/656fmXR6GPZrJbxm",
    headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"},
    json=clean
)

print(f"Status: {resp.status_code}")
if resp.status_code != 200:
    print(f"Error: {resp.text[:300]}")
else:
    print("Updated successfully!")
