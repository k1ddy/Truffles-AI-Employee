#!/usr/bin/env python3
import requests

API_KEY = "REDACTED_JWT"

resp = requests.get(
    "https://n8n.truffles.kz/api/v1/workflows/656fmXR6GPZrJbxm",
    headers={"X-N8N-API-KEY": API_KEY}
)
d = resp.json()
print("Name:", d.get("name"))
print("Active:", d.get("active"))
print("Updated:", d.get("updatedAt"))
