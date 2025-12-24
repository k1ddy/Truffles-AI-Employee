#!/usr/bin/env python3
"""Debug execution structure"""
import requests
import json
import sys

N8N_URL = "https://n8n.truffles.kz"
API_KEY = "REDACTED_JWT"

exec_id = sys.argv[1] if len(sys.argv) > 1 else "762418"

r = requests.get(
    f"{N8N_URL}/api/v1/executions/{exec_id}?includeData=true",
    headers={"X-N8N-API-KEY": API_KEY}
)

data = r.json()
print("Top-level keys:", list(data.keys()))

if "data" in data:
    print("\ndata keys:", list(data["data"].keys()))
    if "resultData" in data["data"]:
        print("resultData keys:", list(data["data"]["resultData"].keys()))
        if "runData" in data["data"]["resultData"]:
            run_data = data["data"]["resultData"]["runData"]
            print("\nNodes in runData:", list(run_data.keys()))
            
            # Check each node
            for node_name in run_data.keys():
                node_data = run_data[node_name]
                if node_data and len(node_data) > 0:
                    first = node_data[0]
                    if first.get("data"):
                        main = first["data"].get("main", [[]])
                        if main and main[0]:
                            item = main[0][0] if main[0] else {}
                            json_data = item.get("json", {})
                            print(f"\n--- {node_name} ---")
                            print(f"Keys: {list(json_data.keys())[:10]}")
                            # Print some values
                            for k in ["message", "response", "knowledge", "rag_scores", "phone"]:
                                if k in json_data:
                                    val = json_data[k]
                                    if isinstance(val, str) and len(val) > 100:
                                        val = val[:100] + "..."
                                    print(f"  {k}: {val}")
