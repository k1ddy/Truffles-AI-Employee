#!/usr/bin/env python3
import requests
import json

API_KEY = "REDACTED_JWT"

print("Downloading workflow...")
resp = requests.get(
    "https://n8n.truffles.kz/api/v1/workflows/4vaEvzlaMrgovhNz",
    headers={"X-N8N-API-KEY": API_KEY}
)
workflow = resp.json()

# Найти все Send ноды и обновить instance_id
updated = []
for node in workflow["nodes"]:
    name = node.get("name", "")
    if "Send" in name or name == "Me":
        params = node.get("parameters", {})
        query_params = params.get("queryParameters", {}).get("parameters", [])
        for p in query_params:
            if p.get("name") == "instance_id":
                old_val = p.get("value", "")[:50]
                # Используем instance_id из Prepare Response (для основного flow)
                # или из Load Prompt (для off-topic)
                if "Off-Topic" in name:
                    p["value"] = "={{ $('Load Prompt').first().json.instance_id }}"
                else:
                    p["value"] = "={{ $('Prepare Response').first().json.instance_id }}"
                updated.append(name)
                print(f"Updated {name}: {old_val}... -> dynamic")

print(f"\nTotal updated: {len(updated)}")

# Upload
allowed = ["name", "nodes", "connections", "settings", "staticData"]
clean = {k: v for k, v in workflow.items() if k in allowed}

resp = requests.put(
    "https://n8n.truffles.kz/api/v1/workflows/4vaEvzlaMrgovhNz",
    headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"},
    json=clean
)
print(f"Upload status: {resp.status_code}")
