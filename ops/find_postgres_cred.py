#!/usr/bin/env python3
"""Find Postgres credential ID from workflow"""
import requests

N8N_URL = "https://n8n.truffles.kz"
API_KEY = "REDACTED_JWT"

r = requests.get(
    f"{N8N_URL}/api/v1/workflows/4vaEvzlaMrgovhNz",
    headers={"X-N8N-API-KEY": API_KEY}
)

workflow = r.json()
for node in workflow["nodes"]:
    creds = node.get("credentials", {})
    if "postgres" in str(creds).lower():
        print(f"Node: {node['name']}")
        print(f"Credentials: {creds}")
        print()
