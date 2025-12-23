#!/usr/bin/env python3
"""Check n8n execution details"""
import json
import sys

if len(sys.argv) < 2:
    print("Usage: python3 check_execution.py <execution_id>")
    sys.exit(1)

exec_id = sys.argv[1]

import urllib.request

# Need to add includeData=true to get runData
url = f"https://n8n.truffles.kz/api/v1/executions/{exec_id}?includeData=true"
headers = {
    "X-N8N-API-KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

print(f"Execution ID: {exec_id}")
print(f"Status: {data.get('status')}")
print(f"Mode: {data.get('mode')}")
print(f"Workflow: {data.get('workflowId')}")
print(f"Started: {data.get('startedAt')}")
print(f"Finished: {data.get('stoppedAt')}")

# Check if there's error
if data.get('status') == 'error':
    print(f"\nERROR!")
    
# Check data output
if 'data' in data and 'resultData' in data['data']:
    result = data['data']['resultData']
    if 'lastNodeExecuted' in result:
        print(f"\nLast node: {result['lastNodeExecuted']}")
    if 'error' in result:
        print(f"Error: {result['error']}")
    
    # Show run data for key nodes
    run_data = result.get('runData', {})
    print(f"\nNodes executed ({len(run_data)}): {list(run_data.keys())}")
    
    # Check specific nodes for data
    for node_name in ['Start', 'Parse Input', 'Classify Intent', 'Build Context', 'Is Deadlock', 'Deadlock Response', 'Prepare Escalation Data', 'Generate Response', 'Check Escalation', 'Load Status', 'Decide Action']:
        if node_name in run_data:
            node_data = run_data[node_name]
            if node_data and len(node_data) > 0:
                first_run = node_data[0]
                if 'data' in first_run and 'main' in first_run['data']:
                    main_data = first_run['data']['main']
                    if main_data and len(main_data) > 0 and len(main_data[0]) > 0:
                        output = main_data[0][0].get('json', {})
                        print(f"\n[{node_name}] output: {str(output)[:200]}")
