#!/usr/bin/env python3
"""Analyze workflow structure"""
import json

with open('/tmp/multi_agent_current.json', 'r') as f:
    wf = json.load(f)

print(f"Workflow: {wf['name']}")
print(f"Total nodes: {len(wf['nodes'])}")
print()

# Find Call Escalation Handler
for node in wf['nodes']:
    if 'Escalation' in node['name'] or 'escalation' in node['name'].lower():
        print(f"=== {node['name']} ===")
        print(f"Type: {node['type']}")
        print(f"ID: {node['id']}")
        if 'parameters' in node:
            params = node['parameters']
            print(f"Parameters:")
            for k, v in params.items():
                print(f"  {k}: {json.dumps(v, indent=4)[:500]}")
        print()

# Find what connects TO Call Escalation Handler
print("=== CONNECTIONS TO Escalation Handler ===")
connections = wf.get('connections', {})
for source, conns in connections.items():
    if 'main' in conns:
        for branch_idx, branch in enumerate(conns['main']):
            for conn in branch:
                if 'Escalation' in conn.get('node', ''):
                    print(f"{source} [branch {branch_idx}] -> {conn['node']}")

print()
print("=== CONNECTIONS FROM Escalation Handler ===")
for source, conns in connections.items():
    if 'Escalation' in source:
        print(f"{source} -> {conns}")

print()
print("=== Build Context node ===")
for node in wf['nodes']:
    if node['name'] == 'Build Context':
        print(f"jsCode preview:")
        code = node['parameters'].get('jsCode', '')
        print(code[:1500])
        
print()
print("=== Check Escalation node ===")
for node in wf['nodes']:
    if node['name'] == 'Check Escalation':
        print(f"Type: {node['type']}")
        print(f"Parameters: {json.dumps(node['parameters'], indent=2)[:800]}")
