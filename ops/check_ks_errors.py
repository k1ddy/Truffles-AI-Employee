#!/usr/bin/env python3
import requests
import json

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

resp = requests.get(
    "https://n8n.truffles.kz/api/v1/executions/762651?includeData=true",
    headers={"X-N8N-API-KEY": API_KEY}
)
d = resp.json()

data = d.get("data", {})
result_data = data.get("resultData", {})
run_data = result_data.get("runData", {})

# Check Prepare Docs List output
if "Prepare Docs List" in run_data:
    executions = run_data["Prepare Docs List"]
    print(f"Prepare Docs List executed {len(executions)} times")
    for i, ex in enumerate(executions):
        try:
            docs = ex["data"]["main"][0]
            print(f"\nExecution {i+1}: {len(docs)} docs")
            for doc in docs[:5]:
                j = doc.get("json", {})
                print(f"  - client={j.get('client_slug')}, doc={j.get('doc_name')}, status={j.get('status', 'ok')}")
        except Exception as e:
            print(f"  Error: {e}")

# Check for errors
error_data = result_data.get("error")
if error_data:
    print("\n=== ERRORS ===")
    print(json.dumps(error_data, indent=2)[:500])

# Check last executed node
last_node = result_data.get("lastNodeExecuted")
print(f"\nLast node executed: {last_node}")
