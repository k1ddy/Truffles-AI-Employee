#!/usr/bin/env python3
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "7jGZrdbaAAvtTnQX"

url = f"https://n8n.truffles.kz/api/v1/executions?workflowId={WORKFLOW_ID}&limit=1"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    execs = json.loads(response.read().decode()).get('data', [])

if execs:
    ex = execs[0]
    print(f"Execution {ex['id']} - {ex['status']}")
    
    url2 = f"https://n8n.truffles.kz/api/v1/executions/{ex['id']}?includeData=true"
    req2 = urllib.request.Request(url2, headers=headers)
    with urllib.request.urlopen(req2) as resp2:
        data = json.loads(resp2.read().decode())
        
        error = data.get('data', {}).get('resultData', {}).get('error', {})
        if error:
            print(f"\nERROR: {error.get('message', 'unknown')}")
            node = error.get('node', {})
            if isinstance(node, dict):
                print(f"Node: {node.get('name', 'unknown')}")
        
        run_data = data.get('data', {}).get('resultData', {}).get('runData', {})
        print(f"\nExecuted nodes: {list(run_data.keys())}")
