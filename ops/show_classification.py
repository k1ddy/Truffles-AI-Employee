#!/usr/bin/env python3
"""Show classification/routing logic from workflow"""
import json

with open('/home/zhan/truffles/workflow_main.json') as f:
    d = json.load(f)

for n in d['nodes']:
    name = n['name']
    if 'Analysis' in name or 'Switch' in name or 'Route' in name or 'Quality' in name:
        print('=' * 60)
        print(f'NODE: {name}')
        print('=' * 60)
        params = n.get('parameters', {})
        
        if 'jsCode' in params:
            print('TYPE: Code')
            print(params['jsCode'][:1500])
        
        elif 'conditions' in params:
            print('TYPE: Switch/IF')
            print(json.dumps(params['conditions'], indent=2, ensure_ascii=False)[:1500])
        
        elif 'responses' in params:
            print('TYPE: LLM')
            for r in params['responses'].get('values', []):
                if r.get('role') == 'system':
                    print(r.get('content', '')[:1500])
        
        print()
