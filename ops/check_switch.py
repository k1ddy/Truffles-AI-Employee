#!/usr/bin/env python3
import requests

API_KEY = "REDACTED_JWT"

resp = requests.get(
    "https://n8n.truffles.kz/api/v1/executions/762651?includeData=true",
    headers={"X-N8N-API-KEY": API_KEY}
)
d = resp.json()

data = d.get("data", {})
result_data = data.get("resultData", {})
run_data = result_data.get("runData", {})

# Check Switch outputs
if "Switch" in run_data:
    executions = run_data["Switch"]
    print(f"Switch executed {len(executions)} times")
    for i, ex in enumerate(executions):
        try:
            main = ex.get("data", {}).get("main", [])
            # Check which output was used
            for out_idx, out_items in enumerate(main):
                if out_items:
                    j = out_items[0].get("json", {})
                    print(f"  Run {i+1}: output {out_idx}, client={j.get('client_slug')}, mime={j.get('mimeType')}")
        except Exception as e:
            print(f"  Run {i+1} error: {e}")

# Check Loop Docs 
print("\n\nLoop Docs inputs:")
if "Loop Docs" in run_data:
    executions = run_data["Loop Docs"]
    for i, ex in enumerate(executions):
        try:
            main = ex.get("data", {}).get("main", [])
            for out_idx, out_items in enumerate(main):
                if out_items:
                    j = out_items[0].get("json", {})
                    client = j.get("client_slug", "?")
                    doc = j.get("doc_name", j.get("doc_id", "?"))
                    print(f"  Run {i+1} output {out_idx}: client={client}, doc={doc[:20] if doc else '?'}")
        except Exception as e:
            print(f"  Run {i+1} error: {e}")
