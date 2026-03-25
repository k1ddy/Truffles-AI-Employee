#!/usr/bin/env python3
import json

with open('/tmp/callback.json', 'r') as f:
    w = json.load(f)

for n in w.get('nodes', []):
    if n['name'] == 'Update Buttons':
        print("=== UPDATE BUTTONS ===")
        print(json.dumps(n.get('parameters', {}), indent=2, ensure_ascii=False))
