#!/usr/bin/env python3
"""
Fix handover-related queries:
1. Check Active Handover - find pending AND active handovers
2. Take Handover - accept pending AND bot_handling
"""

import json
import requests

API_KEY = 'REDACTED_JWT'

def fix_multi_agent():
    print('=== Fixing 6_Multi-Agent ===')
    resp = requests.get(
        'https://n8n.truffles.kz/api/v1/workflows/4vaEvzlaMrgovhNz',
        headers={'X-N8N-API-KEY': API_KEY}
    )
    data = resp.json()
    
    for node in data['nodes']:
        if node['name'] == 'Check Active Handover':
            old_query = node['parameters']['query']
            # Change: h.status = 'active' -> h.status IN ('pending', 'active')
            new_query = old_query.replace(
                "h.status = 'active'",
                "h.status IN ('pending', 'active')"
            )
            if new_query != old_query:
                node['parameters']['query'] = new_query
                print('  Fixed Check Active Handover')
            else:
                print('  Check Active Handover already fixed or different format')
            break
    
    resp = requests.put(
        'https://n8n.truffles.kz/api/v1/workflows/4vaEvzlaMrgovhNz',
        headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
        json={
            'name': data['name'],
            'nodes': data['nodes'],
            'connections': data['connections'],
            'settings': data.get('settings', {})
        }
    )
    print(f'  Status: {resp.status_code}')

def fix_callback():
    print('=== Fixing 9_Telegram_Callback ===')
    resp = requests.get(
        'https://n8n.truffles.kz/api/v1/workflows/HQOWuMDIBPphC86v',
        headers={'X-N8N-API-KEY': API_KEY}
    )
    data = resp.json()
    
    for node in data['nodes']:
        if node['name'] == 'Take Handover':
            old_query = node['parameters']['query']
            # Change: status = 'pending' -> status IN ('pending', 'bot_handling')
            new_query = old_query.replace(
                "status = 'pending'",
                "status IN ('pending', 'bot_handling')"
            )
            if new_query != old_query:
                node['parameters']['query'] = new_query
                print('  Fixed Take Handover')
            else:
                print('  Take Handover already fixed or different format')
            break
    
    resp = requests.put(
        'https://n8n.truffles.kz/api/v1/workflows/HQOWuMDIBPphC86v',
        headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
        json={
            'name': data['name'],
            'nodes': data['nodes'],
            'connections': data['connections'],
            'settings': data.get('settings', {})
        }
    )
    print(f'  Status: {resp.status_code}')

if __name__ == '__main__':
    fix_multi_agent()
    fix_callback()
    print('=== Done ===')
