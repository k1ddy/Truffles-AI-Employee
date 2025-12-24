#!/usr/bin/env python3
"""Откат изменений - вернуть $('Webhook').item.json"""
import requests
import json

API_KEY = "REDACTED_JWT"

# Download current
print("Downloading...")
resp = requests.get(
    "https://n8n.truffles.kz/api/v1/workflows/656fmXR6GPZrJbxm",
    headers={"X-N8N-API-KEY": API_KEY}
)
workflow = resp.json()

# Find Restore Webhook Data and fix ALL assignments
for node in workflow.get("nodes", []):
    if node.get("name") == "Restore Webhook Data":
        assignments = node["parameters"]["assignments"]["assignments"]
        for a in assignments:
            name = a.get("name")
            if name == "headers":
                a["value"] = "={{ $('Webhook').item.json.headers }}"
            elif name == "body":
                a["value"] = "={{ $('Webhook').item.json.body }}"
            elif name == "query":
                a["value"] = "={{ $('Webhook').item.json.query }}"
            elif name == "params":
                a["value"] = "={{ $('Webhook').item.json.params }}"
            elif name == "webhookUrl":
                a["value"] = "={{ $('Webhook').item.json.webhookUrl }}"
            elif name == "executionMode":
                a["value"] = "={{ $('Webhook').item.json.executionMode }}"
            elif name == "client_slug":
                a["value"] = "={{ $('Webhook').item.json.params?.client || 'truffles' }}"
            print(f"  {name}: {a['value'][:50]}...")

# Upload
allowed = ["name", "nodes", "connections", "settings", "staticData"]
clean = {k: v for k, v in workflow.items() if k in allowed}

resp = requests.put(
    "https://n8n.truffles.kz/api/v1/workflows/656fmXR6GPZrJbxm",
    headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"},
    json=clean
)
print(f"\nUpload: {resp.status_code}")
