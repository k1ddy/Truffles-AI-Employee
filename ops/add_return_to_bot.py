#!/usr/bin/env python3
"""
Добавляет [Вернуть боту] функциональность в 9_Telegram_Callback.

Изменения:
1. Action Switch — добавить условие return
2. Return Handover — UPDATE status = 'bot_handling'
3. Unmute Bot Return — размьютить бота
4. Return Response — текст для callback
5. Answer Callback Return — ответить Telegram
6. Update Buttons Return — показать [Беру][Решено]
7. Update Buttons после Take — изменить на [Вернуть боту][Решено]
"""

import json
import requests
import sys

WORKFLOW_ID = 'HQOWuMDIBPphC86v'
API_KEY = 'REDACTED_JWT'
BASE_URL = 'https://n8n.truffles.kz/api/v1'

def get_workflow():
    resp = requests.get(
        f'{BASE_URL}/workflows/{WORKFLOW_ID}',
        headers={'X-N8N-API-KEY': API_KEY}
    )
    return resp.json()

def update_workflow(data):
    payload = {
        'name': data.get('name'),
        'nodes': data.get('nodes'),
        'connections': data.get('connections'),
        'settings': data.get('settings', {}),
    }
    resp = requests.put(
        f'{BASE_URL}/workflows/{WORKFLOW_ID}',
        headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
        json=payload
    )
    return resp

def find_node(nodes, name):
    for n in nodes:
        if n['name'] == name:
            return n
    return None

def add_return_flow(data):
    nodes = data['nodes']
    connections = data['connections']
    
    # 1. Найти Action Switch и добавить условие для return
    action_switch = find_node(nodes, 'Action Switch')
    if not action_switch:
        print('ERROR: Action Switch not found')
        return None
    
    # Добавить условие return в switch
    rules = action_switch['parameters']['rules']['values']
    
    # Проверить что return ещё не добавлен
    for rule in rules:
        conditions = rule.get('conditions', {}).get('conditions', [])
        for cond in conditions:
            if cond.get('rightValue') == 'return':
                print('SKIP: return condition already exists')
                return None
    
    # Добавить новое условие (вставляем перед последним, т.к. последний = fallback)
    return_rule = {
        "conditions": {
            "options": {
                "caseSensitive": True,
                "leftValue": "",
                "typeValidation": "strict",
                "version": 2
            },
            "conditions": [
                {
                    "leftValue": "={{ $json.action }}",
                    "rightValue": "return",
                    "operator": {
                        "type": "string",
                        "operation": "equals"
                    }
                }
            ],
            "combinator": "and"
        }
    }
    # rules порядок: take[0], resolve[1], skip[2], (вставляем return[3])
    rules.append(return_rule)
    print('Added return condition to Action Switch (index 3)')
    
    # 2. Создать Return Handover node
    return_handover = {
        "parameters": {
            "operation": "executeQuery",
            "query": "UPDATE handovers SET status = 'bot_handling' WHERE id = '{{ $json.handover_id }}' RETURNING id, conversation_id;",
            "options": {}
        },
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.6,
        "position": [96, 700],
        "id": "cb-return-handover-001",
        "name": "Return Handover",
        "credentials": {
            "postgres": {
                "id": "SUHrbh39Ig0fBusT",
                "name": "ChatbotDB"
            }
        }
    }
    nodes.append(return_handover)
    print('Added Return Handover node')
    
    # 3. Создать Unmute Bot Return node
    unmute_return = {
        "parameters": {
            "operation": "executeQuery",
            "query": "UPDATE conversations SET bot_status = 'active', bot_muted_until = NULL, no_count = 0 WHERE id = (SELECT conversation_id FROM handovers WHERE id = '{{ $('Merge Token').first().json.handover_id }}');",
            "options": {}
        },
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.6,
        "position": [320, 700],
        "id": "cb-unmute-return-001",
        "name": "Unmute Bot Return",
        "credentials": {
            "postgres": {
                "id": "SUHrbh39Ig0fBusT",
                "name": "ChatbotDB"
            }
        }
    }
    nodes.append(unmute_return)
    print('Added Unmute Bot Return node')
    
    # 4. Создать Return Response node
    return_response = {
        "parameters": {
            "jsCode": "const input = $('Parse Callback').first().json;\n\nreturn [{\n  json: {\n    ...input,\n    response_text: '🤖 Возвращено боту',\n    success: true\n  }\n}];"
        },
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [544, 700],
        "id": "cb-return-response-001",
        "name": "Return Response"
    }
    nodes.append(return_response)
    print('Added Return Response node')
    
    # 5. Создать Answer Callback Return node
    answer_return = {
        "parameters": {
            "method": "POST",
            "url": "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/answerCallbackQuery",
            "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "callback_query_id", "value": "={{ $('Merge Token').first().json.callback_query_id }}"},
                    {"name": "text", "value": "={{ $('Return Response').first().json.response_text }}"}
                ]
            },
            "options": {}
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [768, 700],
        "id": "cb-answer-return-001",
        "name": "Answer Callback Return"
    }
    nodes.append(answer_return)
    print('Added Answer Callback Return node')
    
    # 6. Создать Update Buttons Return node — показать [Беру][Решено]
    update_return = {
        "parameters": {
            "method": "POST",
            "url": "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/editMessageReplyMarkup",
            "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "chat_id", "value": "={{ $('Merge Token').first().json.chat_id }}"},
                    {"name": "message_id", "value": "={{ $('Merge Token').first().json.message_id }}"},
                    {"name": "reply_markup", "value": "={{ JSON.stringify({inline_keyboard: [[{text: 'Беру', callback_data: 'take_' + $('Merge Token').first().json.handover_id}, {text: 'Решено ✅', callback_data: 'resolve_' + $('Merge Token').first().json.handover_id}]]}) }}"}
                ]
            },
            "options": {}
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [992, 700],
        "id": "cb-update-return-001",
        "name": "Update Buttons Return"
    }
    nodes.append(update_return)
    print('Added Update Buttons Return node')
    
    # 7. Изменить Update Buttons после Take — добавить [Вернуть боту]
    update_buttons = find_node(nodes, 'Update Buttons')
    if update_buttons:
        # Изменить reply_markup
        for param in update_buttons['parameters']['bodyParameters']['parameters']:
            if param['name'] == 'reply_markup':
                param['value'] = "={{ JSON.stringify({inline_keyboard: [[{text: 'Вернуть боту 🤖', callback_data: 'return_' + $('Merge Token').first().json.handover_id}, {text: 'Решено ✅', callback_data: 'resolve_' + $('Merge Token').first().json.handover_id}]]}) }}"
        print('Updated Update Buttons to show [Вернуть боту][Решено]')
    
    # 8. Добавить connections для return flow
    # Action Switch: rules order = outputs order
    # После добавления return rule, выходы будут:
    # [0] take, [1] resolve, [2] skip, [3] return, [4] fallback (extra)
    if 'Action Switch' in connections:
        main = connections['Action Switch']['main']
        # Вставить return connection перед fallback (который пустой [])
        # Текущий порядок: [take], [resolve], [skip], []
        # Нужный порядок: [take], [resolve], [skip], [return], []
        if len(main) >= 4:
            # Вставляем перед последним (fallback)
            main.insert(3, [{"node": "Return Handover", "type": "main", "index": 0}])
        else:
            main.append([{"node": "Return Handover", "type": "main", "index": 0}])
    
    # Return Handover -> Unmute Bot Return
    connections['Return Handover'] = {"main": [[{"node": "Unmute Bot Return", "type": "main", "index": 0}]]}
    
    # Unmute Bot Return -> Return Response
    connections['Unmute Bot Return'] = {"main": [[{"node": "Return Response", "type": "main", "index": 0}]]}
    
    # Return Response -> Answer Callback Return
    connections['Return Response'] = {"main": [[{"node": "Answer Callback Return", "type": "main", "index": 0}]]}
    
    # Answer Callback Return -> Update Buttons Return
    connections['Answer Callback Return'] = {"main": [[{"node": "Update Buttons Return", "type": "main", "index": 0}]]}
    
    print('Added connections for return flow')
    
    return data

def main():
    print('=== Adding [Вернуть боту] to 9_Telegram_Callback ===\n')
    
    # 1. Get current workflow
    print('1. Getting current workflow...')
    data = get_workflow()
    if 'nodes' not in data:
        print(f'ERROR: Failed to get workflow: {data}')
        return 1
    print(f'   Found {len(data["nodes"])} nodes\n')
    
    # 2. Backup
    with open('/home/zhan/truffles/ops/9_Telegram_Callback_backup.json', 'w') as f:
        json.dump(data, f, indent=2)
    print('2. Backup saved to 9_Telegram_Callback_backup.json\n')
    
    # 3. Add return flow
    print('3. Adding return flow...')
    modified = add_return_flow(data)
    if not modified:
        print('   No changes made')
        return 0
    print('')
    
    # 4. Update workflow
    print('4. Updating workflow...')
    resp = update_workflow(modified)
    if resp.status_code == 200:
        print(f'   SUCCESS: Workflow updated')
    else:
        print(f'   ERROR: {resp.status_code} - {resp.text[:200]}')
        return 1
    
    print('\n=== Done ===')
    print('Test: Send message to trigger escalation, then click [Вернуть боту]')
    return 0

if __name__ == '__main__':
    sys.exit(main())
