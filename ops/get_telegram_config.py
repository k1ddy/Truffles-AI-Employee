#!/usr/bin/env python3
"""Get Telegram config from workflow"""
import requests

N8N_URL = "https://n8n.truffles.kz"
API_KEY = "REDACTED_JWT"

r = requests.get(
    f"{N8N_URL}/api/v1/workflows/4vaEvzlaMrgovhNz",
    headers={"X-N8N-API-KEY": API_KEY}
)

workflow = r.json()
for node in workflow["nodes"]:
    if "telegram" in node["type"].lower():
        print(f"Node: {node['name']}")
        print(f"Chat ID: {node['parameters'].get('chatId', 'N/A')}")
        print(f"Credentials: {node.get('credentials', {})}")
        break
