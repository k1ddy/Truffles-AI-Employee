#!/usr/bin/env python3
"""
Fix Skip flow and add statistics:
1. Skip - don't remove buttons, log who skipped, show message
2. Resolve - save resolved_by_name
3. Auto-close - add unpin
"""

import json
import requests

API_KEY = 'REDACTED_JWT'

# ==================== 9_Telegram_Callback ====================
print("=== Fixing 9_Telegram_Callback ===")

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/HQOWuMDIBPphC86v',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()
nodes = data['nodes']
connections = data['connections']

# 1. Replace Skip Response with Skip Handover (logs skip, keeps buttons)
for i, node in enumerate(nodes):
    if node['name'] == 'Skip Response':
        nodes[i] = {
            "parameters": {
                "operation": "executeQuery",
                "query": """UPDATE handovers 
SET skipped_by = COALESCE(skipped_by, '[]'::jsonb) || jsonb_build_object(
  'manager_id', '{{ $('Parse Callback').first().json.manager_id }}',
  'manager_name', '{{ $('Parse Callback').first().json.manager_name }}',
  'skipped_at', NOW()
)::jsonb
WHERE id = '{{ $('Parse Callback').first().json.handover_id }}'
RETURNING id;""",
                "options": {}
            },
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.6,
            "position": node['position'],
            "id": node['id'],
            "name": "Log Skip",
            "credentials": {
                "postgres": {
                    "id": "SUHrbh39Ig0fBusT",
                    "name": "ChatbotDB"
                }
            }
        }
        print("  Replaced Skip Response with Log Skip")
        break

# 2. Add Skip Notify node (shows who skipped, keeps buttons)
skip_notify = {
    "parameters": {
        "method": "POST",
        "url": "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/sendMessage",
        "sendBody": True,
        "bodyParameters": {
            "parameters": [
                {"name": "chat_id", "value": "={{ $('Merge Token').first().json.chat_id }}"},
                {"name": "message_thread_id", "value": "={{ $('Merge Token').first().json.topic_id }}"},
                {"name": "text", "value": "=❌ {{ $('Parse Callback').first().json.manager_name }} пропустил заявку"}
            ]
        },
        "options": {}
    },
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [544, 500],
    "id": "cb-skip-notify-001",
    "name": "Skip Notify"
}

# Check if already exists
exists = any(n['name'] == 'Skip Notify' for n in nodes)
if not exists:
    nodes.append(skip_notify)
    print("  Added Skip Notify")

# 3. Add Answer Callback Skip (simple answer, no button changes)
answer_skip = {
    "parameters": {
        "method": "POST",
        "url": "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/answerCallbackQuery",
        "sendBody": True,
        "bodyParameters": {
            "parameters": [
                {"name": "callback_query_id", "value": "={{ $('Parse Callback').first().json.callback_query_id }}"},
                {"name": "text", "value": "Пропущено"}
            ]
        },
        "options": {}
    },
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [768, 500],
    "id": "cb-answer-skip-002",
    "name": "Answer Skip"
}

exists = any(n['name'] == 'Answer Skip' for n in nodes)
if not exists:
    nodes.append(answer_skip)
    print("  Added Answer Skip")

# 4. Update Resolve Handover to save resolved_by
for node in nodes:
    if node['name'] == 'Resolve Handover':
        old_query = node['parameters'].get('query', '')
        if 'resolved_by_name' not in old_query:
            # Add resolved_by fields to UPDATE
            new_query = old_query.replace(
                "status = 'resolved'",
                "status = 'resolved', resolved_by_name = '{{ $('Parse Callback').first().json.manager_name }}', resolved_by_id = '{{ $('Parse Callback').first().json.manager_id }}'"
            )
            node['parameters']['query'] = new_query
            print("  Updated Resolve Handover with resolved_by")
        break

# 5. Fix connections
# Log Skip -> Skip Notify -> Answer Skip (no button removal!)
connections['Log Skip'] = {
    "main": [[{"node": "Skip Notify", "type": "main", "index": 0}]]
}
connections['Skip Notify'] = {
    "main": [[{"node": "Answer Skip", "type": "main", "index": 0}]]
}

# Update Action Switch to point to Log Skip instead of Skip Response
for i, outputs in enumerate(connections.get('Action Switch', {}).get('main', [])):
    for j, out in enumerate(outputs):
        if out['node'] == 'Skip Response':
            connections['Action Switch']['main'][i][j]['node'] = 'Log Skip'
            print("  Updated Action Switch -> Log Skip")

# Remove old nodes that are no longer needed
nodes = [n for n in nodes if n['name'] not in ['Skip Response', 'Answer Callback Skip', 'Remove Buttons Skip']]
print("  Removed old skip nodes")

# Remove old connections
for old_name in ['Skip Response', 'Answer Callback Skip', 'Remove Buttons Skip']:
    if old_name in connections:
        del connections[old_name]

# Save
resp = requests.put(
    'https://n8n.truffles.kz/api/v1/workflows/HQOWuMDIBPphC86v',
    headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
    json={'name': data['name'], 'nodes': nodes, 'connections': connections, 'settings': data.get('settings', {})}
)
print(f"  Status: {resp.status_code}")

# ==================== 10_Handover_Monitor ====================
print("\n=== Fixing 10_Handover_Monitor (add unpin) ===")

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/ZRcuYYCv1o9B0MyY',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()
nodes = data['nodes']
connections = data['connections']

# Add Unpin on Auto-close
unpin_auto = {
    "parameters": {
        "method": "POST",
        "url": "=https://api.telegram.org/bot{{ $json.telegram_bot_token }}/unpinChatMessage",
        "sendBody": True,
        "bodyParameters": {
            "parameters": [
                {"name": "chat_id", "value": "={{ $json.telegram_chat_id }}"},
                {"name": "message_id", "value": "={{ $json.telegram_message_id }}"}
            ]
        },
        "options": {"ignore_ssl_issues": False}
    },
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [1200, 500],
    "id": "hm-unpin-auto-001",
    "name": "Unpin Auto-close"
}

exists = any(n['name'] == 'Unpin Auto-close' for n in nodes)
if not exists:
    nodes.append(unpin_auto)
    print("  Added Unpin Auto-close")
    
    # Connect Notify Topic -> Unpin Auto-close
    if 'Notify Topic' in connections:
        connections['Notify Topic']['main'][0].append({"node": "Unpin Auto-close", "type": "main", "index": 0})
    else:
        connections['Notify Topic'] = {"main": [[{"node": "Unpin Auto-close", "type": "main", "index": 0}]]}
    print("  Connected Notify Topic -> Unpin Auto-close")

# Need to add telegram_message_id to Load Active Handovers query
for node in nodes:
    if node['name'] == 'Load Active Handovers':
        query = node['parameters'].get('query', '')
        if 'telegram_message_id' not in query:
            # Add telegram_message_id to SELECT
            query = query.replace(
                'h.reminder_2_sent_at,',
                'h.reminder_2_sent_at,\n  h.telegram_message_id,'
            )
            node['parameters']['query'] = query
            print("  Added telegram_message_id to Load Active Handovers")
        break

# Save
resp = requests.put(
    'https://n8n.truffles.kz/api/v1/workflows/ZRcuYYCv1o9B0MyY',
    headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
    json={'name': data['name'], 'nodes': nodes, 'connections': connections, 'settings': data.get('settings', {})}
)
print(f"  Status: {resp.status_code}")

print("\n=== Done ===")
print("Statistics fields: skipped_by, resolved_by_name, resolved_by_id")
print("Skip: logs who skipped, keeps buttons for others")
print("Auto-close: now unpins message")
