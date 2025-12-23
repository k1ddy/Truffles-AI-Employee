#!/usr/bin/env python3
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

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
