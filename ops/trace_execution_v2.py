#!/usr/bin/env python3
"""
Trace n8n execution - показывает данные каждой ноды
Usage: python3 trace_execution.py [execution_id]
"""
import sys
import json
import requests

API_URL = 'https://n8n.truffles.kz/api/v1'
API_KEY = 'REDACTED_JWT'

def get_execution(exec_id):
    headers = {'X-N8N-API-KEY': API_KEY}
    # Try with includeData parameter
    r = requests.get(f'{API_URL}/executions/{exec_id}?includeData=true', headers=headers)
    data = r.json()
    
    print("=== RAW RESPONSE KEYS ===")
    print(f"Top-level keys: {list(data.keys())}")
    
    if 'data' in data:
        print(f"data keys: {list(data['data'].keys()) if isinstance(data['data'], dict) else type(data['data'])}")
        if isinstance(data['data'], dict) and 'resultData' in data['data']:
            print(f"resultData keys: {list(data['data']['resultData'].keys())}")
            if 'runData' in data['data']['resultData']:
                run_data = data['data']['resultData']['runData']
                print(f"runData nodes: {list(run_data.keys())}")
    
    return data

def trace(exec_id):
    data = get_execution(exec_id)
    
    print('\n' + '=' * 70)
    print(f"EXECUTION: {data.get('id')}")
    print(f"STATUS: {data.get('status')}")
    print(f"MODE: {data.get('mode')}")
    print(f"STARTED: {data.get('startedAt')}")
    print(f"FINISHED: {data.get('stoppedAt')}")
    print('=' * 70)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 trace_execution_v2.py <execution_id>')
    else:
        trace(sys.argv[1])
