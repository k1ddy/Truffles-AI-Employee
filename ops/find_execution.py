#!/usr/bin/env python3
"""Найти execution по тексту сообщения или времени"""
import requests
import sys

API_KEY = 'REDACTED_JWT'
BASE_URL = 'https://n8n.truffles.kz/api/v1'
BOT_WORKFLOW = '4vaEvzlaMrgovhNz'

def search_executions(search_text=None, limit=10):
    r = requests.get(f'{BASE_URL}/executions?workflowId={BOT_WORKFLOW}&limit={limit}',
                     headers={'X-N8N-API-KEY': API_KEY})
    executions = r.json().get('data', [])
    
    for exc in executions:
        exc_id = exc['id']
        detail = requests.get(f'{BASE_URL}/executions/{exc_id}?includeData=true',
                              headers={'X-N8N-API-KEY': API_KEY}).json()
        
        run_data = detail.get('data', {}).get('resultData', {}).get('runData', {})
        
        msg = ''
        for node_name in ['Parse Input', 'Webhook v2']:
            if node_name in run_data:
                for run in run_data[node_name]:
                    data = run.get('data', {}).get('main', [[]])
                    if data and data[0]:
                        item = data[0][0].get('json', {})
                        msg = item.get('text', item.get('message', ''))[:100]
                        break
        
        if search_text and search_text.lower() not in msg.lower():
            continue
            
        print(f"{exc_id}: {exc['startedAt'][:19]} - {msg}")

if __name__ == '__main__':
    search = sys.argv[1] if len(sys.argv) > 1 else None
    search_executions(search)
