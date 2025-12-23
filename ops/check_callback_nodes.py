#!/usr/bin/env python3
import json

with open('/tmp/callback.json', 'r') as f:
    w = json.load(f)

print("=== NOTIFY IN CHAT NODE ===")
for n in w.get('nodes', []):
    if n['name'] == 'Notify in Chat':
        print(json.dumps(n['parameters'], indent=2, ensure_ascii=False))

print("\n=== UPDATE BUTTONS NODE ===")
for n in w.get('nodes', []):
    if n['name'] == 'Update Buttons':
        print(json.dumps(n['parameters'], indent=2, ensure_ascii=False))
