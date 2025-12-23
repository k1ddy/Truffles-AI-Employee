#!/usr/bin/env python3
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "4vaEvzlaMrgovhNz"

url = f"https://n8n.truffles.kz/api/v1/executions?workflowId={WORKFLOW_ID}&limit=1"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    execs = json.loads(response.read().decode()).get('data', [])

if execs:
    ex = execs[0]
    print(f"Execution {ex['id']} - {ex['status']}")
    
    # Get details
    url2 = f"https://n8n.truffles.kz/api/v1/executions/{ex['id']}?includeData=true"
    req2 = urllib.request.Request(url2, headers=headers)
    with urllib.request.urlopen(req2) as resp2:
        data = json.loads(resp2.read().decode())
        
        # Check error
        error = data.get('data', {}).get('resultData', {}).get('error', {})
        if error:
            print(f"\nERROR: {error.get('message', 'unknown')}")
            node = error.get('node', {})
            if isinstance(node, dict):
                print(f"Node: {node.get('name', 'unknown')}")
        
        run_data = data.get('data', {}).get('resultData', {}).get('runData', {})
        print(f"\nExecuted nodes: {list(run_data.keys())}")
        
        # Check specific nodes
        for node_name in ['Build Context', 'Check Active Handover', 'Handover Active?']:
            if node_name in run_data:
                out = run_data[node_name][-1].get('data', {}).get('main', [[]])
                if out and out[0]:
                    print(f"\n{node_name}: {json.dumps(out[0][0].get('json', {}), indent=2)[:200]}")
else:
    print("No executions found")
