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

# Nodes to check
nodes = ["Log Success", "Log No Changes", "Log Error", "Upsert to Qdrant", "Check Hash Changed", "Get Previous Hash"]

for node_name in nodes:
    if node_name in run_data:
        executions = run_data[node_name]
        print(f"\n{node_name}: {len(executions)} executions")
        for i, ex in enumerate(executions[:3]):
            try:
                items = ex["data"]["main"][0]
                print(f"  Run {i+1}: {len(items)} items")
                if items and i < 2:
                    j = items[0].get("json", {})
                    slug = j.get("client_slug", j.get("client_id", "?"))
                    print(f"    First item: client={slug}")
            except Exception as e:
                print(f"  Run {i+1} error: {e}")
    else:
        print(f"\n{node_name}: NOT FOUND")
