#!/usr/bin/env python3
import json

with open('/tmp/adapter.json', 'r') as f:
    w = json.load(f)

for n in w.get('nodes', []):
    if n['name'] in ['Get Existing Topic', 'Save Topic ID']:
        print(f"=== {n['name']} ===")
        query = n.get('parameters', {}).get('query', '')
        print(query)
        print()
