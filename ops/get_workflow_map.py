#!/usr/bin/env python3
"""Generate workflow map documentation"""

import json
import requests

API_KEY = 'REDACTED_JWT'

# Get all workflows
resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows',
    headers={'X-N8N-API-KEY': API_KEY}
)
workflows = resp.json()['data']

output = []
output.append('# WORKFLOW_MAP.md')
output.append('')
output.append('Карта всех workflows в n8n.')
output.append('')
output.append('## Список workflows')
output.append('')
output.append('| ID | Название | Статус | Триггер |')
output.append('|----|----------|--------|---------|')

for w in sorted(workflows, key=lambda x: x['name']):
    status = '🟢 active' if w['active'] else '⚪ inactive'
    output.append(f"| {w['id'][:8]}... | {w['name']} | {status} | - |")

output.append('')
output.append('## Детали ключевых workflows')
output.append('')

# Get details for key workflows
key_workflows = [
    ('4vaEvzlaMrgovhNz', '6_Multi-Agent'),
    ('HQOWuMDIBPphC86v', '9_Telegram_Callback'),
    ('7jGZrdbaP3K1HMbT', '7_Escalation_Handler'),
    ('ZRcuYYCv1o9B0MyY', '10_Handover_Monitor'),
]

for wf_id, wf_name in key_workflows:
    resp = requests.get(
        f'https://n8n.truffles.kz/api/v1/workflows/{wf_id}',
        headers={'X-N8N-API-KEY': API_KEY}
    )
    data = resp.json()
    
    output.append(f'### {wf_name}')
    output.append('')
    output.append(f'**ID:** `{wf_id}`')
    output.append('')
    output.append('**Ноды:**')
    
    nodes = data.get('nodes', [])
    for node in sorted(nodes, key=lambda x: x.get('position', [0,0])[0]):
        node_type = node['type'].split('.')[-1]
        output.append(f"- {node['name']} ({node_type})")
    
    output.append('')
    
    # Show connections
    output.append('**Flow:**')
    connections = data.get('connections', {})
    for src, conn in connections.items():
        targets = []
        for outputs in conn.get('main', []):
            for t in outputs:
                targets.append(t['node'])
        if targets:
            output.append(f"- {src} → {', '.join(targets)}")
    
    output.append('')
    output.append('---')
    output.append('')

print('\n'.join(output))
