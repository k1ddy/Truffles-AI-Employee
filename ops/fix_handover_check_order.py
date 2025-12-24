#!/usr/bin/env python3
"""
Fix: Check Active Handover должен быть ПЕРЕД Skip Classifier,
чтобы сообщения при активном handover сразу шли в Forward to Topic.

Текущий flow:
  Parse Input → Intent Router → Skip Classifier?
                                  ├→ [0] Upsert User → Build Context → Check Active Handover
                                  └→ [1] Classify Intent

Нужный flow:
  Parse Input → Intent Router → Check Handover Early → Handover Active Early?
                                                        ├→ [yes] Forward to Topic Early → Exit
                                                        └→ [no] Skip Classifier? → дальше
"""

import json
import requests

API_KEY = 'REDACTED_JWT'
WORKFLOW_ID = '4vaEvzlaMrgovhNz'

def get_workflow():
    resp = requests.get(
        f'https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}',
        headers={'X-N8N-API-KEY': API_KEY}
    )
    return resp.json()

def update_workflow(data):
    resp = requests.put(
        f'https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}',
        headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
        json={
            'name': data['name'],
            'nodes': data['nodes'],
            'connections': data['connections'],
            'settings': data.get('settings', {})
        }
    )
    return resp

def find_node(nodes, name):
    for n in nodes:
        if n['name'] == name:
            return n
    return None

def fix_flow(data):
    nodes = data['nodes']
    connections = data['connections']
    
    # Найти позиции существующих нод
    intent_router = find_node(nodes, 'Intent Router')
    skip_classifier = find_node(nodes, 'Skip Classifier?')
    
    if not intent_router or not skip_classifier:
        print('ERROR: Required nodes not found')
        return False
    
    # Позиция между Intent Router и Skip Classifier
    ir_pos = intent_router['position']
    sc_pos = skip_classifier['position']
    mid_x = (ir_pos[0] + sc_pos[0]) // 2
    mid_y = ir_pos[1]
    
    # 1. Создать Check Handover Early (проверка handover ДО классификации)
    check_handover_early = {
        "parameters": {
            "operation": "executeQuery",
            "query": """SELECT 
  h.id as handover_id,
  h.conversation_id,
  c.telegram_topic_id,
  cs.telegram_chat_id,
  cs.telegram_bot_token,
  COALESCE(u.name, u.phone, 'Клиент') as client_name
FROM users u
JOIN conversations c ON c.user_id = u.id
LEFT JOIN handovers h ON h.conversation_id = c.id AND h.status IN ('pending', 'active')
LEFT JOIN client_settings cs ON cs.client_id = c.client_id
WHERE u.phone = '{{ $json.phone }}'
ORDER BY c.created_at DESC
LIMIT 1;""",
            "options": {}
        },
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.6,
        "position": [mid_x, mid_y],
        "id": "check-handover-early-001",
        "name": "Check Handover Early",
        "credentials": {
            "postgres": {
                "id": "SUHrbh39Ig0fBusT",
                "name": "ChatbotDB"
            }
        }
    }
    nodes.append(check_handover_early)
    print('Added: Check Handover Early')
    
    # 2. Создать Handover Active Early? (IF node)
    handover_active_early = {
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                "conditions": [
                    {
                        "leftValue": "={{ $json.handover_id }}",
                        "rightValue": "",
                        "operator": {"type": "string", "operation": "notEmpty"}
                    }
                ],
                "combinator": "and"
            }
        },
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [mid_x + 200, mid_y],
        "id": "handover-active-early-001",
        "name": "Handover Active Early?"
    }
    nodes.append(handover_active_early)
    print('Added: Handover Active Early?')
    
    # 3. Создать Forward to Topic Early
    forward_early = {
        "parameters": {
            "method": "POST",
            "url": "=https://api.telegram.org/bot{{ $json.telegram_bot_token }}/sendMessage",
            "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "chat_id", "value": "={{ $json.telegram_chat_id }}"},
                    {"name": "message_thread_id", "value": "={{ $json.telegram_topic_id }}"},
                    {"name": "text", "value": "=📱 {{ $json.client_name }}:\n{{ $('Parse Input').first().json.originalText || $('Parse Input').first().json.text }}"}
                ]
            },
            "options": {}
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [mid_x + 400, mid_y - 100],
        "id": "forward-early-001",
        "name": "Forward to Topic Early"
    }
    nodes.append(forward_early)
    print('Added: Forward to Topic Early')
    
    # 4. Создать Exit Early
    exit_early = {
        "parameters": {},
        "type": "n8n-nodes-base.noOp",
        "typeVersion": 1,
        "position": [mid_x + 600, mid_y - 100],
        "id": "exit-early-001",
        "name": "Exit Early (Handover)"
    }
    nodes.append(exit_early)
    print('Added: Exit Early (Handover)')
    
    # 5. Создать Merge Input (чтобы передать данные из Parse Input в Skip Classifier)
    merge_input = {
        "parameters": {
            "jsCode": "return $('Parse Input').all();"
        },
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [mid_x + 400, mid_y + 100],
        "id": "merge-input-001",
        "name": "Pass Input"
    }
    nodes.append(merge_input)
    print('Added: Pass Input')
    
    # 6. Обновить connections
    # Intent Router → Check Handover Early (вместо Skip Classifier)
    connections['Intent Router'] = {
        "main": [[{"node": "Check Handover Early", "type": "main", "index": 0}]]
    }
    
    # Check Handover Early → Handover Active Early?
    connections['Check Handover Early'] = {
        "main": [[{"node": "Handover Active Early?", "type": "main", "index": 0}]]
    }
    
    # Handover Active Early? → [true] Forward to Topic Early, [false] Pass Input
    connections['Handover Active Early?'] = {
        "main": [
            [{"node": "Forward to Topic Early", "type": "main", "index": 0}],
            [{"node": "Pass Input", "type": "main", "index": 0}]
        ]
    }
    
    # Forward to Topic Early → Exit Early
    connections['Forward to Topic Early'] = {
        "main": [[{"node": "Exit Early (Handover)", "type": "main", "index": 0}]]
    }
    
    # Pass Input → Skip Classifier?
    connections['Pass Input'] = {
        "main": [[{"node": "Skip Classifier?", "type": "main", "index": 0}]]
    }
    
    print('Updated connections')
    
    return True

def main():
    print('=== Fixing Handover Check Order ===\n')
    
    data = get_workflow()
    if 'nodes' not in data:
        print(f'ERROR: {data}')
        return 1
    
    # Backup
    with open('/home/zhan/truffles/ops/6_Multi-Agent_before_fix_order.json', 'w') as f:
        json.dump(data, f, indent=2)
    print('Backup saved\n')
    
    if not fix_flow(data):
        return 1
    
    resp = update_workflow(data)
    if resp.status_code == 200:
        print('\nSUCCESS: Workflow updated')
        print('\nNew flow:')
        print('Intent Router → Check Handover Early → Handover Active Early?')
        print('                                        ├→ [yes] Forward to Topic Early → Exit')
        print('                                        └→ [no] Pass Input → Skip Classifier? → ...')
    else:
        print(f'\nERROR: {resp.status_code} - {resp.text[:300]}')
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
