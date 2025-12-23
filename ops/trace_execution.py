#!/usr/bin/env python3
"""
Trace n8n execution - показывает данные каждой ноды
Usage: python3 trace_execution.py [execution_id]
"""
import sys
import json
import requests

API_URL = 'https://n8n.truffles.kz/api/v1'
API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY0MTkzNjI5fQ.I06M9VWLgBkZKCk14CqahwM3ntuvUn_VcA9XzEHQV0Q'

IMPORTANT_NODES = [
    'Parse Input',
    'Agent: Analysis',
    'Parse Analysis', 
    'Qdrant Vector Store',
    'Build Context',
    'Agent: Generation',
    'Extract Response',
    'Agent: Quality Check',
    'Parse Quality',
    'Quality Decision'
]

def get_execution(exec_id):
    headers = {'X-N8N-API-KEY': API_KEY}
    r = requests.get(f'{API_URL}/executions/{exec_id}?includeData=true', headers=headers)
    return r.json()

def get_last_executions(limit=5):
    headers = {'X-N8N-API-KEY': API_KEY}
    r = requests.get(f'{API_URL}/executions?limit={limit}', headers=headers)
    return r.json().get('data', [])

def truncate(s, max_len=500):
    s = str(s)
    return s[:max_len] + '...' if len(s) > max_len else s

def trace(exec_id):
    data = get_execution(exec_id)
    
    print('=' * 70)
    print(f"EXECUTION: {data.get('id')}")
    print(f"STATUS: {data.get('status')}")
    print(f"WORKFLOW: {data.get('workflowData', {}).get('name', '?')}")
    print(f"STARTED: {data.get('startedAt')}")
    print('=' * 70)
    
    run_data = data.get('data', {}).get('resultData', {}).get('runData', {})
    
    if not run_data:
        print('No run data')
        return
    
    for node_name in IMPORTANT_NODES:
        if node_name not in run_data:
            continue
            
        print(f'\n>>> {node_name}')
        print('-' * 50)
        
        node_runs = run_data[node_name]
        for run in node_runs:
            if run.get('error'):
                print(f"ERROR: {run['error'].get('message', '?')}")
            
            output = run.get('data', {}).get('main', [[]])
            if output and output[0]:
                for i, item in enumerate(output[0][:3]):  # max 3 items
                    json_data = item.get('json', {})
                    
                    if node_name == 'Parse Input':
                        print(f"message: {truncate(json_data.get('message', ''), 200)}")
                        print(f"phone: {json_data.get('phone', '')}")
                    
                    elif node_name == 'Agent: Analysis':
                        print(f"output: {truncate(json_data.get('output', ''), 400)}")
                    
                    elif node_name == 'Parse Analysis':
                        analysis = json_data.get('analysis', {})
                        print(f"message_type: {analysis.get('message_type')}")
                        print(f"intent: {analysis.get('intent')}")
                        print(f"emotion: {analysis.get('emotion')}")
                        print(f"response_style: {analysis.get('response_style')}")
                        print(f"is_relevant: {analysis.get('is_relevant')}")
                    
                    elif node_name == 'Qdrant Vector Store':
                        doc = json_data.get('document', {})
                        score = json_data.get('score', 'N/A')
                        content = doc.get('pageContent', json_data.get('pageContent', ''))
                        print(f"[{i+1}] score: {score}")
                        print(f"    content: {truncate(content, 150)}")
                    
                    elif node_name == 'Build Context':
                        print(f"knowledge: {truncate(json_data.get('knowledge', ''), 400)}")
                    
                    elif node_name == 'Agent: Generation':
                        print(f"output: {truncate(json_data.get('output', ''), 400)}")
                    
                    elif node_name == 'Extract Response':
                        print(f"response: {truncate(json_data.get('response', ''), 400)}")
                    
                    elif node_name == 'Agent: Quality Check':
                        print(f"output: {truncate(json_data.get('output', ''), 400)}")
                    
                    elif node_name == 'Parse Quality':
                        print(f"decision: {json_data.get('decision')}")
                        print(f"score: {json_data.get('score')}")
                        print(f"issues: {json_data.get('issues')}")
                    
                    elif node_name == 'Quality Decision':
                        print(f"data: {truncate(json_data, 200)}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Last 5 executions:')
        print('-' * 60)
        for e in get_last_executions(5):
            wf = e.get('workflowData', {}).get('name', '?')
            print(f"  {e['id']} | {e['status']:8} | {wf}")
        print('-' * 60)
        print('\nUsage: python3 trace_execution.py <execution_id>')
    else:
        trace(sys.argv[1])
