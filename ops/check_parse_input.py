#!/usr/bin/env python3
"""Check Parse Input and data flow"""
import json
import urllib.request
import subprocess

API_KEY = "REDACTED_JWT"

url = f"https://n8n.truffles.kz/api/v1/workflows/4vaEvzlaMrgovhNz"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

for node in workflow['nodes']:
    if node['name'] == 'Parse Input':
        print("=== PARSE INPUT ===")
        code = node.get('parameters', {}).get('jsCode', '')
        print(code[:2000])

# Check actual execution to see what instance_id value is
print("\n=== LATEST MULTI-AGENT EXECUTION ===")
url = f"https://n8n.truffles.kz/api/v1/executions?workflowId=4vaEvzlaMrgovhNz&limit=1"
req = urllib.request.Request(url, headers={"X-N8N-API-KEY": API_KEY})
with urllib.request.urlopen(req) as response:
    execs = json.loads(response.read().decode()).get('data', [])
    if execs:
        exec_id = execs[0]['id']
        # Get execution details
        url2 = f"https://n8n.truffles.kz/api/v1/executions/{exec_id}?includeData=true"
        req2 = urllib.request.Request(url2, headers={"X-N8N-API-KEY": API_KEY})
        with urllib.request.urlopen(req2) as resp2:
            data = json.loads(resp2.read().decode())
            run_data = data.get('data', {}).get('resultData', {}).get('runData', {})
            
            if 'Parse Input' in run_data:
                out = run_data['Parse Input'][-1].get('data', {}).get('main', [[]])
                if out and out[0]:
                    j = out[0][0].get('json', {})
                    print(f"client_slug: {j.get('client_slug')}")
                    print(f"instance_id: {j.get('instance_id')}")
                    print(f"remoteJid: {j.get('remoteJid')}")
            
            if 'Prepare Response' in run_data:
                out = run_data['Prepare Response'][-1].get('data', {}).get('main', [[]])
                if out and out[0]:
                    j = out[0][0].get('json', {})
                    print(f"\nPrepare Response instance_id: {j.get('instance_id')}")
