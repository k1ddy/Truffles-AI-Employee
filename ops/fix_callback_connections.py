#!/usr/bin/env python3
"""Fix Action Switch connections for answered and snooze"""

import json
import requests

API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4'

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/HQOWuMDIBPphC86v',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()

# Fix Action Switch connections
# Current: [0]=take, [1]=resolve, [2]=skip, [3]=return, [4]=answered, [5]=snooze
# But connections are wrong for [4] and [5]

connections = data['connections']
main = connections['Action Switch']['main']

# Ensure we have enough outputs
while len(main) < 7:
    main.append([])

# Fix connections:
# [4] answered → Answered Response
# [5] snooze → Snooze Handover
main[4] = [{"node": "Answered Response", "type": "main", "index": 0}]
main[5] = [{"node": "Snooze Handover", "type": "main", "index": 0}]

# Remove extra output [6] if it exists (was Snooze Handover)
if len(main) > 6:
    main.pop(6)

print('Fixed Action Switch connections:')
for i, outputs in enumerate(main):
    targets = [o['node'] for o in outputs] if outputs else ['(none)']
    print(f'  Output [{i}]: {targets}')

resp = requests.put(
    'https://n8n.truffles.kz/api/v1/workflows/HQOWuMDIBPphC86v',
    headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
    json={'name': data['name'], 'nodes': data['nodes'], 'connections': connections, 'settings': data.get('settings', {})}
)
print(f'\nStatus: {resp.status_code}')
