import json
import requests

workflow_id = '4vaEvzlaMrgovhNz'
api_key = 'REDACTED_JWT'

with open(f'/home/zhan/truffles/workflow/6_Multi-Agent_{workflow_id}.json') as f:
    data = json.load(f)

# Keep only fields n8n API accepts
payload = {
    'name': data.get('name', '6_Multi-Agent'),
    'nodes': data.get('nodes', []),
    'connections': data.get('connections', {}),
    'settings': data.get('settings', {}),
}

resp = requests.put(
    f'https://n8n.truffles.kz/api/v1/workflows/{workflow_id}',
    headers={'X-N8N-API-KEY': api_key, 'Content-Type': 'application/json'},
    json=payload
)
print(f'Status: {resp.status_code}')
print(resp.text[:300] if resp.text else 'No response')
