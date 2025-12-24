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

# Check all nodes
print("All executed nodes:")
for node_name in sorted(run_data.keys()):
    count = len(run_data[node_name])
    print(f"  {node_name}: {count}")

# Look for anything with demo_salon
print("\n\nSearching for demo_salon in all outputs...")
for node_name, executions in run_data.items():
    for ex in executions:
        try:
            items = ex.get("data", {}).get("main", [[]])[0]
            for item in items:
                j = item.get("json", {})
                if "demo_salon" in str(j):
                    print(f"Found in {node_name}: {list(j.keys())[:5]}")
                    break
        except:
            pass
