#!/usr/bin/env python3
"""Find executions for Truffles bot workflow"""
import requests

API_URL = 'https://n8n.truffles.kz/api/v1'
API_KEY = 'REDACTED_JWT'
BOT_WORKFLOW_ID = '4vaEvzlaMrgovhNz'

headers = {'X-N8N-API-KEY': API_KEY}

# Get executions for specific workflow
r = requests.get(f'{API_URL}/executions?workflowId={BOT_WORKFLOW_ID}&limit=20', headers=headers)
data = r.json().get('data', [])

print(f"Executions for Truffles v2 - Multi-Agent ({BOT_WORKFLOW_ID}):")
print('-' * 80)
print(f"{'ID':8} | {'Status':8} | {'Started':19}")
print('-' * 80)

for e in data:
    started = e.get('startedAt', '')[:19]
    print(f"{e['id']:8} | {e['status']:8} | {started}")

print(f"\nTotal: {len(data)}")
