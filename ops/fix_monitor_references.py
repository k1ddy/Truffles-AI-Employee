#!/usr/bin/env python3
"""
Fix 10_Handover_Monitor - use correct data references after HTTP requests
"""

import json
import requests

API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4'

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/ZRcuYYCv1o9B0MyY',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()
nodes = data['nodes']

print("=== Fixing 10_Handover_Monitor references ===")

# Fix all nodes that use $json after HTTP requests
# They should reference $('Decide Action').first().json instead

fixes = {
    'Mark Reminder 1 Sent': {
        'old': "{{ $json.handover_id }}",
        'new': "{{ $('Decide Action').first().json.handover_id }}"
    },
    'Mark Reminder 2 Sent': {
        'old': "{{ $json.handover_id }}",
        'new': "{{ $('Decide Action').first().json.handover_id }}"
    },
    'Close Handover': {
        'old': "{{ $json.handover_id }}",
        'new': "{{ $('Decide Action').first().json.handover_id }}"
    },
    'Unmute Bot': {
        'old': "{{ $json.conversation_id }}",
        'new': "{{ $('Decide Action').first().json.conversation_id }}"
    },
    'Save to History': {
        'old': "{{ $json.",
        'new': "{{ $('Decide Action').first().json."
    },
    'Notify Client': {
        'old': "{{ $json.",
        'new': "{{ $('Decide Action').first().json."
    },
    'Notify Topic': {
        'old': "{{ $json.",
        'new': "{{ $('Decide Action').first().json."
    },
    'Unpin Auto-close': {
        'old': "{{ $json.",
        'new': "{{ $('Decide Action').first().json."
    }
}

for node in nodes:
    if node['name'] in fixes:
        fix = fixes[node['name']]
        
        # Fix query if exists
        if 'query' in node['parameters']:
            old_query = node['parameters']['query']
            new_query = old_query.replace(fix['old'], fix['new'])
            if new_query != old_query:
                node['parameters']['query'] = new_query
                print(f"  Fixed: {node['name']} (query)")
        
        # Fix queryParameters if exists (for HTTP requests)
        if 'queryParameters' in node['parameters']:
            params = node['parameters']['queryParameters'].get('parameters', [])
            for p in params:
                if fix['old'] in str(p.get('value', '')):
                    p['value'] = p['value'].replace(fix['old'], fix['new'])
                    print(f"  Fixed: {node['name']} (queryParameters)")
        
        # Fix bodyParameters if exists
        if 'bodyParameters' in node['parameters']:
            params = node['parameters']['bodyParameters'].get('parameters', [])
            for p in params:
                if fix['old'] in str(p.get('value', '')):
                    p['value'] = p['value'].replace(fix['old'], fix['new'])
                    print(f"  Fixed: {node['name']} (bodyParameters)")
        
        # Fix url if exists
        if 'url' in node['parameters']:
            old_url = node['parameters']['url']
            new_url = old_url.replace(fix['old'], fix['new'])
            if new_url != old_url:
                node['parameters']['url'] = new_url
                print(f"  Fixed: {node['name']} (url)")

# Save
resp = requests.put(
    'https://n8n.truffles.kz/api/v1/workflows/ZRcuYYCv1o9B0MyY',
    headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
    json={'name': data['name'], 'nodes': nodes, 'connections': data['connections'], 'settings': data.get('settings', {})}
)
print(f"\nStatus: {resp.status_code}")
