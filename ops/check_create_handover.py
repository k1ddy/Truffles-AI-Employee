#!/usr/bin/env python3
import json
with open('/tmp/esc.json', 'r') as f:
    wf = json.load(f)
for node in wf['nodes']:
    if node['name'] == 'Create Handover':
        print(f"Query:\n{node['parameters']['query']}")
