#!/usr/bin/env python3
"""Find [Беру] execution"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

url = f"https://n8n.truffles.kz/api/v1/executions?workflowId={WORKFLOW_ID}&limit=20"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    execs = json.loads(response.read().decode()).get('data', [])

print("=== CALLBACK EXECUTIONS ===")
for ex in execs:
    exec_id = ex['id']
    url2 = f"https://n8n.truffles.kz/api/v1/executions/{exec_id}?includeData=true"
    req2 = urllib.request.Request(url2, headers=headers)
    with urllib.request.urlopen(req2) as resp2:
        data = json.loads(resp2.read().decode())
        run_data = data.get('data', {}).get('resultData', {}).get('runData', {})
        
        action = "?"
        if 'Parse Callback' in run_data:
            out = run_data['Parse Callback'][-1].get('data', {}).get('main', [[]])
            if out and out[0]:
                j = out[0][0].get('json', {})
                action = j.get('action', '?')
                cb_type = j.get('type', '?')
        
        nodes = list(run_data.keys())
        has_take = 'Take Handover' in nodes
        has_resolve = 'Resolve Handover' in nodes
        
        print(f"{exec_id}: action={action}, type={cb_type}, take={has_take}, resolve={has_resolve}, status={ex['status']}")
