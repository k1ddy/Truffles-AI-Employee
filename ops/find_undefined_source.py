#!/usr/bin/env python3
"""Find where undefined phone comes from"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "4vaEvzlaMrgovhNz"

# Get last 5 executions
url = f"https://n8n.truffles.kz/api/v1/executions?workflowId={WORKFLOW_ID}&limit=10"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    execs = json.loads(response.read().decode()).get('data', [])

print("=== LAST 10 MULTI-AGENT EXECUTIONS ===")
for ex in execs:
    exec_id = ex['id']
    
    # Get details
    url2 = f"https://n8n.truffles.kz/api/v1/executions/{exec_id}?includeData=true"
    req2 = urllib.request.Request(url2, headers=headers)
    with urllib.request.urlopen(req2) as resp2:
        data = json.loads(resp2.read().decode())
        
        run_data = data.get('data', {}).get('resultData', {}).get('runData', {})
        
        phone = "?"
        if 'Parse Input' in run_data:
            out = run_data['Parse Input'][-1].get('data', {}).get('main', [[]])
            if out and out[0]:
                phone = out[0][0].get('json', {}).get('phone', '?')
        
        print(f"{exec_id}: phone={phone}, status={ex['status']}")
