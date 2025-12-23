#!/usr/bin/env python3
import json

with open('/tmp/ks_check.json') as f:
    d = json.load(f)

for n in d.get('nodes', []):
    if 'query' in n.get('parameters', {}):
        print(f"Node: {n.get('name')}")
        print(f"Query: {n['parameters']['query'][:300]}")
        print("---")
