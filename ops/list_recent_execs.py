#!/usr/bin/env python3
"""List recent executions"""
import requests

N8N_URL = "https://n8n.truffles.kz"
API_KEY = "REDACTED_JWT"

r = requests.get(
    f"{N8N_URL}/api/v1/executions?workflowId=4vaEvzlaMrgovhNz&limit=5",
    headers={"X-N8N-API-KEY": API_KEY}
)

data = r.json()
if data.get("data"):
    for ex in data["data"]:
        print(f"ID: {ex['id']:<8} Status: {ex['status']:<10} Started: {ex['startedAt']}")
