#!/usr/bin/env python3
"""Build complete data flow map for all workflows"""

import json
import requests
import re

API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4'

# Get all workflows first
resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows',
    headers={'X-N8N-API-KEY': API_KEY}
)
all_wf = {w['name']: w['id'] for w in resp.json()['data']}

# Target workflows
TARGETS = ['7_Escalation_Handler', '8_Telegram_Adapter', '9_Telegram_Callback', '10_Handover_Monitor']

pattern = r"\$\(['\"]([^'\"]+)['\"]\)"

all_problems = []

for wf_name in TARGETS:
    # Find workflow ID
    wf_id = None
    for name, id in all_wf.items():
        if wf_name in name:
            wf_id = id
            break
    
    if not wf_id:
        print(f"\n{wf_name}: NOT FOUND")
        continue
    
    print(f"\n{'='*60}")
    print(f"WORKFLOW: {wf_name} ({wf_id})")
    print('='*60)
    
    resp = requests.get(
        f'https://n8n.truffles.kz/api/v1/workflows/{wf_id}',
        headers={'X-N8N-API-KEY': API_KEY}
    )
    data = resp.json()
    
    if 'nodes' not in data:
        print(f"  ERROR: {data}")
        continue
    
    node_names = set(n['name'] for n in data['nodes'])
    
    # Connections
    print("\nFLOW:")
    for src, conn in data['connections'].items():
        targets = []
        for outputs in conn.get('main', []):
            for t in outputs:
                targets.append(t['node'])
        if targets:
            print(f"  {src} -> {targets}")
    
    # Find broken references
    print("\nREFERENCES:")
    has_refs = False
    for node in data['nodes']:
        params_str = json.dumps(node.get('parameters', {}))
        refs = re.findall(pattern, params_str)
        if refs:
            for ref in set(refs):
                exists = ref in node_names
                if not exists:
                    has_refs = True
                    print(f"  BROKEN: {node['name']} -> {ref}")
                    all_problems.append({
                        'workflow': wf_name,
                        'node': node['name'],
                        'missing_ref': ref
                    })
    if not has_refs:
        print("  (no broken references)")

print(f"\n{'='*60}")
print("SUMMARY OF PROBLEMS")
print('='*60)
if all_problems:
    for p in all_problems:
        print(f"  [{p['workflow']}] {p['node']} -> {p['missing_ref']} (MISSING)")
else:
    print("  No broken references found")
