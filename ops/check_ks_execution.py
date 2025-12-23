#!/usr/bin/env python3
import requests

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

resp = requests.get(
    "https://n8n.truffles.kz/api/v1/executions/762651?includeData=true",
    headers={"X-N8N-API-KEY": API_KEY}
)
d = resp.json()

data = d.get("data", {})
result_data = data.get("resultData", {})
run_data = result_data.get("runData", {})

# Check Get Active Clients
if "Get Active Clients" in run_data:
    try:
        clients = run_data["Get Active Clients"][0]["data"]["main"][0]
        print("Clients found:", len(clients))
        for c in clients:
            j = c.get("json", {})
            print(f"  - {j.get('name')}: folder={j.get('folder_id', 'N/A')[:20]}...")
    except Exception as e:
        print("Error:", e)
else:
    print("Get Active Clients not found in run_data")
    print("Available nodes:", list(run_data.keys())[:10])
