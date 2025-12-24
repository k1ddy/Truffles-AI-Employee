#!/usr/bin/env python3
"""Check callback workflow executions"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

url = f"https://n8n.truffles.kz/api/v1/executions?workflowId={WORKFLOW_ID}&limit=5"
headers = {"X-N8N-API-KEY": API_KEY}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

print("=== CALLBACK EXECUTIONS ===\n")
for ex in data.get('data', []):
    print(f"ID: {ex['id']}")
    print(f"Status: {ex['status']}")
    print(f"Started: {ex.get('startedAt', 'N/A')}")
    
    # Get execution details
    detail_url = f"https://n8n.truffles.kz/api/v1/executions/{ex['id']}"
    req2 = urllib.request.Request(detail_url, headers=headers)
    try:
        with urllib.request.urlopen(req2) as resp2:
            detail = json.loads(resp2.read().decode())
            
            # Check nodes
            result_data = detail.get('data', {}).get('resultData', {})
            run_data = result_data.get('runData', {})
            
            for node_name, node_runs in run_data.items():
                if node_runs:
                    last_run = node_runs[-1]
                    output = last_run.get('data', {}).get('main', [[]])
                    if output and output[0]:
                        print(f"  {node_name}: {json.dumps(output[0][0].get('json', {}), ensure_ascii=False)[:200]}")
                    
                    # Check for errors
                    if last_run.get('error'):
                        print(f"  {node_name} ERROR: {last_run['error']}")
    except Exception as e:
        print(f"  Error getting details: {e}")
    
    print()
