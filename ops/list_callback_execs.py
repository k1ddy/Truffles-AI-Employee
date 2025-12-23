#!/usr/bin/env python3
"""List callback executions with action"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

url = f"https://n8n.truffles.kz/api/v1/executions?workflowId={WORKFLOW_ID}&limit=10"
headers = {"X-N8N-API-KEY": API_KEY}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

for ex in data.get('data', []):
    detail_url = f"https://n8n.truffles.kz/api/v1/executions/{ex['id']}"
    req2 = urllib.request.Request(detail_url, headers=headers)
    with urllib.request.urlopen(req2) as resp2:
        detail = json.loads(resp2.read().decode())
        
        result_data = detail.get('data', {}).get('resultData', {})
        run_data = result_data.get('runData', {})
        
        action = "?"
        handover_id = "?"
        
        if 'Parse Callback' in run_data:
            runs = run_data['Parse Callback']
            if runs:
                output = runs[-1].get('data', {}).get('main', [[]])
                if output and output[0]:
                    j = output[0][0].get('json', {})
                    action = j.get('action', '?')
                    handover_id = j.get('handover_id', '?')[:20]
        
        print(f"{ex['id']} | {ex['status']} | action={action} | handover={handover_id}")
