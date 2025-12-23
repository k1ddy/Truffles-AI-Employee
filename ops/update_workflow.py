import json
import requests

workflow_id = '4vaEvzlaMrgovhNz'
api_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4'

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
