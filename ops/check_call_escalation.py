#!/usr/bin/env python3
"""Check Call Escalation Handler node configuration"""
import json

with open('/tmp/ma.json', 'r') as f:
    wf = json.load(f)

for node in wf['nodes']:
    if 'Escalation' in node['name']:
        print(f"=== {node['name']} ===")
        print(f"Type: {node['type']}")
        print(f"Parameters: {json.dumps(node['parameters'], indent=2)}")
        print()
