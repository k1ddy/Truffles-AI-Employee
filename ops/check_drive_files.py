#!/usr/bin/env python3
import requests

API_KEY = "REDACTED_JWT"

# Get latest Knowledge Sync execution
resp = requests.get(
    "https://n8n.truffles.kz/api/v1/executions/762651?includeData=true",
    headers={"X-N8N-API-KEY": API_KEY}
)
d = resp.json()

data = d.get("data", {})
result_data = data.get("resultData", {})
run_data = result_data.get("runData", {})

# Check Google Drive: List Files
if "Google Drive: List Files" in run_data:
    executions = run_data["Google Drive: List Files"]
    print(f"List Files executed {len(executions)} times")
    for i, ex in enumerate(executions):
        try:
            files = ex["data"]["main"][0]
            print(f"\nExecution {i+1}: {len(files)} files")
            for f in files[:10]:
                j = f.get("json", {})
                print(f"  - {j.get('name')}: {j.get('mimeType')}")
        except Exception as e:
            print(f"  Error: {e}")
else:
    print("Google Drive: List Files not found")
    print("Available:", list(run_data.keys())[:15])
