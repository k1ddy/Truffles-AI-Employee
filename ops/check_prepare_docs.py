#!/usr/bin/env python3
import requests
import json

API_KEY = "REDACTED_JWT"

resp = requests.get(
    "https://n8n.truffles.kz/api/v1/executions/762651?includeData=true",
    headers={"X-N8N-API-KEY": API_KEY}
)
d = resp.json()

data = d.get("data", {})
result_data = data.get("resultData", {})
run_data = result_data.get("runData", {})

# Check Prepare Docs List in detail
if "Prepare Docs List" in run_data:
    executions = run_data["Prepare Docs List"]
    print(f"Prepare Docs List executed {len(executions)} times\n")
    for i, ex in enumerate(executions):
        print(f"=== Execution {i+1} ===")
        try:
            # Check input source
            source = ex.get("source", [])
            print(f"Source: {source}")
            
            # Check output
            main = ex.get("data", {}).get("main", [[]])
            items = main[0] if main else []
            print(f"Output items: {len(items)}")
            
            for item in items[:2]:
                j = item.get("json", {})
                print(f"  client={j.get('client_slug')}, doc={j.get('doc_name')}, mime={j.get('mimeType')}")
        except Exception as e:
            print(f"Error: {e}")
        print()
