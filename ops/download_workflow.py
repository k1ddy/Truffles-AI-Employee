#!/usr/bin/env python3
import requests
import json
import sys

API_KEY = None
with open('/home/zhan/truffles/ops/check_execution.py') as f:
    for line in f:
        if "API_KEY = '" in line:
            API_KEY = line.split("'")[1]
            break

workflow_id = sys.argv[1] if len(sys.argv) > 1 else '4vaEvzlaMrgovhNz'
url = f'https://n8n.truffles.kz/api/v1/workflows/{workflow_id}'
headers = {'X-N8N-API-KEY': API_KEY}
response = requests.get(url, headers=headers)

output = sys.argv[2] if len(sys.argv) > 2 else '/tmp/current_workflow.json'
with open(output, 'w') as f:
    json.dump(response.json(), f, indent=2)
print(f'Saved to {output}')
