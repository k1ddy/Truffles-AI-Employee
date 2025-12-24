#!/usr/bin/env python3
import requests
import json

API_KEY = "REDACTED_JWT"

for exec_id in ["762728", "762718"]:
    print(f"\n=== Execution {exec_id} ===")
    resp = requests.get(
        f"https://n8n.truffles.kz/api/v1/executions/{exec_id}?includeData=true",
        headers={"X-N8N-API-KEY": API_KEY}
    )
    d = resp.json()
    
    print(f"Status: {d.get('status')}")
    print(f"Workflow: {d.get('workflowId')}")
    
    data = d.get("data", {})
    result_data = data.get("resultData", {})
    
    # Check for errors
    error = result_data.get("error")
    if error:
        print(f"ERROR: {json.dumps(error, indent=2)[:500]}")
    
    # Check last node
    last_node = result_data.get("lastNodeExecuted")
    print(f"Last node: {last_node}")
    
    # Check run data for key nodes
    run_data = result_data.get("runData", {})
    print(f"Nodes executed: {list(run_data.keys())[:10]}")
