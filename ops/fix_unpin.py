#!/usr/bin/env python3
"""
Fix Unpin Escalation - use telegram_message_id from handover, not from callback
"""

import json
import requests

API_KEY = 'REDACTED_JWT'

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/HQOWuMDIBPphC86v',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()
nodes = data['nodes']
connections = data['connections']

# 1. Update Resolve Handover to return telegram_message_id
for node in nodes:
    if node['name'] == 'Resolve Handover':
        old_query = node['parameters'].get('query', '')
        # Current: RETURNING id, conversation_id
        # New: RETURNING id, conversation_id, telegram_message_id
        if 'telegram_message_id' not in old_query:
            new_query = old_query.replace(
                'RETURNING id, conversation_id',
                'RETURNING id, conversation_id, telegram_message_id'
            )
            # If no RETURNING clause, add it
            if 'RETURNING' not in old_query:
                new_query = old_query.rstrip(';') + ' RETURNING id, conversation_id, telegram_message_id;'
            node['parameters']['query'] = new_query
            print("Updated Resolve Handover to return telegram_message_id")
            print(f"Query: {new_query[:200]}...")
        break

# 2. Update Unpin Escalation to use telegram_message_id from Resolve Handover
for node in nodes:
    if node['name'] == 'Unpin Escalation':
        params = node['parameters']['bodyParameters']['parameters']
        for p in params:
            if p['name'] == 'message_id':
                # Change from callback message_id to handover telegram_message_id
                p['value'] = "={{ $('Resolve Handover').first().json.telegram_message_id }}"
                print("Updated Unpin Escalation to use telegram_message_id from Resolve Handover")
                break
        break

# Save
resp = requests.put(
    'https://n8n.truffles.kz/api/v1/workflows/HQOWuMDIBPphC86v',
    headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
    json={'name': data['name'], 'nodes': nodes, 'connections': connections, 'settings': data.get('settings', {})}
)
print(f"Status: {resp.status_code}")

if resp.status_code != 200:
    print(resp.text[:300])
