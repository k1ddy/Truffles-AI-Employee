#!/usr/bin/env python3
import json
w = json.load(open('/tmp/callback.json'))
print('Active:', w.get('active'))
print('Nodes:', [n['name'] for n in w.get('nodes',[])])

# Check credentials
for n in w.get('nodes', []):
    creds = n.get('credentials', {})
    if creds:
        print(f"  {n['name']} credentials: {creds}")
