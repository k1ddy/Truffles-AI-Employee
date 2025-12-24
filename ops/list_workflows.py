#!/usr/bin/env python3
import json
import urllib.request

API_KEY = "REDACTED_JWT"

req = urllib.request.Request(
    "https://n8n.truffles.kz/api/v1/workflows",
    headers={"X-N8N-API-KEY": API_KEY}
)

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

for w in data.get("data", []):
    status = "ACTIVE" if w["active"] else "inactive"
    name = w["name"][:55]
    print(f"{w['id']} | {name:55} | {status}")
