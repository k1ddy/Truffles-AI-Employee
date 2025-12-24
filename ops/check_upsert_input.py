#!/usr/bin/env python3
"""Check what Upsert User receives as input"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "4vaEvzlaMrgovhNz"

# Get last execution
url = f"https://n8n.truffles.kz/api/v1/executions?workflowId={WORKFLOW_ID}&limit=1&status=success"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    execs = json.loads(response.read().decode()).get('data', [])

if execs:
    exec_id = execs[0]['id']
    print(f"Execution: {exec_id}")
    
    url2 = f"https://n8n.truffles.kz/api/v1/executions/{exec_id}?includeData=true"
    req2 = urllib.request.Request(url2, headers=headers)
    with urllib.request.urlopen(req2) as resp2:
        data = json.loads(resp2.read().decode())
        
        run_data = data.get('data', {}).get('resultData', {}).get('runData', {})
        
        print("\n=== UPSERT USER INPUT ===")
        if 'Upsert User' in run_data:
            input_data = run_data['Upsert User'][-1].get('inputData', {}).get('main', [[]])
            if input_data and input_data[0]:
                print(json.dumps(input_data[0][0].get('json', {}), indent=2, ensure_ascii=False))
        
        print("\n=== UPSERT USER OUTPUT ===")
        if 'Upsert User' in run_data:
            out = run_data['Upsert User'][-1].get('data', {}).get('main', [[]])
            if out and out[0]:
                print(json.dumps(out[0][0].get('json', {}), indent=2, ensure_ascii=False))

# Check workflow connections to Upsert User
print("\n=== WHAT CONNECTS TO UPSERT USER ===")
url = f"https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

connections = workflow.get('connections', {})
for src, conns in connections.items():
    if 'main' in conns:
        for branch in conns['main']:
            for c in branch:
                if c.get('node') == 'Upsert User':
                    print(f"  {src} -> Upsert User")
