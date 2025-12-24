#!/usr/bin/env python3
"""Check last execution for errors"""
import requests

N8N_URL = "https://n8n.truffles.kz"
API_KEY = "REDACTED_JWT"

r = requests.get(
    f"{N8N_URL}/api/v1/executions?workflowId=4vaEvzlaMrgovhNz&limit=1&includeData=true",
    headers={"X-N8N-API-KEY": API_KEY}
)

data = r.json()
if data.get("data"):
    ex = data["data"][0]
    print(f"ID: {ex['id']}")
    print(f"Status: {ex['status']}")
    print(f"Started: {ex['startedAt']}")
    
    # Check for Save Trace node
    run_data = ex.get("data", {}).get("resultData", {}).get("runData", {})
    
    if "Save Trace" in run_data:
        st = run_data["Save Trace"][0]
        if st.get("error"):
            print(f"\n❌ Save Trace ERROR: {st['error']}")
        else:
            print(f"\n✅ Save Trace: OK")
    else:
        print(f"\n⚠️ Save Trace node not found in execution")
        print(f"Available nodes: {list(run_data.keys())[:10]}")
