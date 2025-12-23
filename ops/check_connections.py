#!/usr/bin/env python3
"""Check workflow connections"""
import json

with open('/tmp/ma.json', 'r') as f:
    wf = json.load(f)

print("=== KEY CONNECTIONS ===\n")

connections = wf.get('connections', {})

# Check specific nodes
key_nodes = ['Build Context', 'Is Deadlock', 'RAG Search', 'Skip Classifier?', 'Classify Intent', 'Is On Topic']

for node in key_nodes:
    if node in connections:
        print(f"{node} ->")
        for i, branch in enumerate(connections[node]['main']):
            targets = [c.get('node') for c in branch]
            print(f"  branch {i}: {targets}")
        print()
    else:
        print(f"{node} -> (no outgoing connections)\n")

print("\n=== WHAT CONNECTS TO Is Deadlock ===")
for src, conns in connections.items():
    if 'main' in conns:
        for branch in conns['main']:
            for c in branch:
                if c.get('node') == 'Is Deadlock':
                    print(f"{src} -> Is Deadlock")
