#!/usr/bin/env python3
import requests

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

resp = requests.get(
    "https://n8n.truffles.kz/api/v1/executions/762860?includeData=true",
    headers={"X-N8N-API-KEY": API_KEY}
)
d = resp.json()

data = d.get("data", {})
result_data = data.get("resultData", {})
run_data = result_data.get("runData", {})

if "Parse Input" in run_data:
    items = run_data["Parse Input"][0]["data"]["main"][0]
    if items:
        j = items[0]["json"]
        print(f"client_slug: {j.get('client_slug')}")
        print(f"text: {j.get('text')}")

if "RAG Search" in run_data:
    items = run_data["RAG Search"][0]["data"]["main"][0]
    if items:
        j = items[0]["json"]
        print(f"RAG client_slug: {j.get('client_slug')}")
        print(f"RAG knowledge preview: {j.get('knowledge', '')[:100]}")
