#!/usr/bin/env python3
"""Get latest execution"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "HQOWuMDIBPphC86v"

url = f"https://n8n.truffles.kz/api/v1/executions?workflowId={WORKFLOW_ID}&limit=1"
headers = {"X-N8N-API-KEY": API_KEY}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

e = data['data'][0]
print(f"Latest: {e['id']} - {e['status']}")

# Now get details
import subprocess
subprocess.run(['python3', '/home/zhan/truffles/ops/get_exec_detail.py', e['id']])
