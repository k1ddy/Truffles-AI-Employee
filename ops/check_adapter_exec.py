#!/usr/bin/env python3
"""Check Telegram Adapter executions"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "fFPEbTNlkBSjo66A"  # Telegram Adapter

url = f"https://n8n.truffles.kz/api/v1/executions?workflowId={WORKFLOW_ID}&limit=3"
headers = {"X-N8N-API-KEY": API_KEY}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

for ex in data.get('data', []):
    print(f"=== Execution {ex['id']} ({ex['status']}) ===")
    
    # Get details
    detail_url = f"https://n8n.truffles.kz/api/v1/executions/{ex['id']}?includeData=true"
    req2 = urllib.request.Request(detail_url, headers=headers)
    with urllib.request.urlopen(req2) as resp2:
        detail = json.loads(resp2.read().decode())
        
        result_data = detail.get('data', {}).get('resultData', {})
        run_data = result_data.get('runData', {})
        
        for node_name in ['Prepare Data', 'Get Existing Topic', 'Has Topic?', 'Create Topic', 'Get Topic ID']:
            if node_name in run_data:
                runs = run_data[node_name]
                if runs:
                    output = runs[-1].get('data', {}).get('main', [[]])
                    if output and output[0]:
                        j = output[0][0].get('json', {})
                        # Show relevant fields
                        if node_name == 'Prepare Data':
                            print(f"  {node_name}: conversation_id={j.get('conversation_id')}")
                        elif node_name == 'Get Existing Topic':
                            print(f"  {node_name}: telegram_topic_id={j.get('telegram_topic_id')}")
                        elif node_name == 'Has Topic?':
                            print(f"  {node_name}: telegram_topic_id={j.get('telegram_topic_id')}")
                        elif node_name == 'Create Topic':
                            result = j.get('result', {})
                            print(f"  {node_name}: message_thread_id={result.get('message_thread_id')}")
                        elif node_name == 'Get Topic ID':
                            print(f"  {node_name}: topic_id={j.get('topic_id')}")
    print()
