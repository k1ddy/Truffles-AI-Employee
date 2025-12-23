#!/usr/bin/env python3
"""
Добавляет обработку callback'ов от напоминаний:
- answered_ — отметить что ответил (просто убрать кнопки)
- snooze_ — отложить напоминание на 30 мин (сбросить reminder_1_sent_at)
"""

import json
import requests

API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4'
CALLBACK_ID = 'HQOWuMDIBPphC86v'

def get_workflow():
    resp = requests.get(
        f'https://n8n.truffles.kz/api/v1/workflows/{CALLBACK_ID}',
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
        f'https://n8n.truffles.kz/api/v1/workflows/{CALLBACK_ID}',
        headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
        json=payload
    )
    return resp

def find_node(nodes, name):
    for n in nodes:
        if n['name'] == name:
            return n
    return None

def add_callbacks(data):
    nodes = data['nodes']
    connections = data['connections']
    
    # Проверить что ещё не добавлено
    if find_node(nodes, 'Answered Response'):
        print('SKIP: Already added')
        return False
    
    # 1. Добавить условия в Action Switch
    action_switch = find_node(nodes, 'Action Switch')
    if action_switch:
        rules = action_switch['parameters']['rules']['values']
        
        # Добавить answered
        rules.append({
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                "conditions": [{"leftValue": "={{ $json.action }}", "rightValue": "answered", "operator": {"type": "string", "operation": "equals"}}],
                "combinator": "and"
            }
        })
        
        # Добавить snooze
        rules.append({
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                "conditions": [{"leftValue": "={{ $json.action }}", "rightValue": "snooze", "operator": {"type": "string", "operation": "equals"}}],
                "combinator": "and"
            }
        })
        print('Added answered and snooze to Action Switch')
    
    # 2. Добавить Answered Response
    answered_response = {
        "parameters": {
            "jsCode": "const input = $('Parse Callback').first().json;\nreturn [{ json: { ...input, response_text: '✓ Отмечено как отвеченное', success: true } }];"
        },
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [96, 900],
        "id": "cb-answered-response-001",
        "name": "Answered Response"
    }
    nodes.append(answered_response)
    
    # 3. Добавить Answer Callback Answered
    answer_answered = {
        "parameters": {
            "method": "POST",
            "url": "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/answerCallbackQuery",
            "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "callback_query_id", "value": "={{ $('Merge Token').first().json.callback_query_id }}"},
                    {"name": "text", "value": "={{ $('Answered Response').first().json.response_text }}"}
                ]
            },
            "options": {}
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [320, 900],
        "id": "cb-answer-answered-001",
        "name": "Answer Callback Answered"
    }
    nodes.append(answer_answered)
    
    # 4. Добавить Remove Buttons Answered
    remove_answered = {
        "parameters": {
            "method": "POST",
            "url": "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/editMessageReplyMarkup",
            "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "chat_id", "value": "={{ $('Merge Token').first().json.chat_id }}"},
                    {"name": "message_id", "value": "={{ $('Merge Token').first().json.message_id }}"},
                    {"name": "reply_markup", "value": "={{ JSON.stringify({inline_keyboard: []}) }}"}
                ]
            },
            "options": {}
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [544, 900],
        "id": "cb-remove-answered-001",
        "name": "Remove Buttons Answered"
    }
    nodes.append(remove_answered)
    
    # 5. Добавить Snooze Handover (сбросить reminder_1_sent_at)
    snooze_handover = {
        "parameters": {
            "operation": "executeQuery",
            "query": "UPDATE handovers SET reminder_1_sent_at = NULL, reminder_2_sent_at = NULL WHERE id = '{{ $json.handover_id }}';",
            "options": {}
        },
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.6,
        "position": [96, 1100],
        "id": "cb-snooze-handover-001",
        "name": "Snooze Handover",
        "credentials": {
            "postgres": {
                "id": "SUHrbh39Ig0fBusT",
                "name": "ChatbotDB"
            }
        }
    }
    nodes.append(snooze_handover)
    
    # 6. Добавить Snooze Response
    snooze_response = {
        "parameters": {
            "jsCode": "const input = $('Parse Callback').first().json;\nreturn [{ json: { ...input, response_text: '⏰ Отложено на 30 минут', success: true } }];"
        },
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [320, 1100],
        "id": "cb-snooze-response-001",
        "name": "Snooze Response"
    }
    nodes.append(snooze_response)
    
    # 7. Добавить Answer Callback Snooze
    answer_snooze = {
        "parameters": {
            "method": "POST",
            "url": "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/answerCallbackQuery",
            "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "callback_query_id", "value": "={{ $('Merge Token').first().json.callback_query_id }}"},
                    {"name": "text", "value": "={{ $('Snooze Response').first().json.response_text }}"}
                ]
            },
            "options": {}
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [544, 1100],
        "id": "cb-answer-snooze-001",
        "name": "Answer Callback Snooze"
    }
    nodes.append(answer_snooze)
    
    # 8. Добавить Remove Buttons Snooze
    remove_snooze = {
        "parameters": {
            "method": "POST",
            "url": "=https://api.telegram.org/bot{{ $('Merge Token').first().json.bot_token }}/editMessageReplyMarkup",
            "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {"name": "chat_id", "value": "={{ $('Merge Token').first().json.chat_id }}"},
                    {"name": "message_id", "value": "={{ $('Merge Token').first().json.message_id }}"},
                    {"name": "reply_markup", "value": "={{ JSON.stringify({inline_keyboard: []}) }}"}
                ]
            },
            "options": {}
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [768, 1100],
        "id": "cb-remove-snooze-001",
        "name": "Remove Buttons Snooze"
    }
    nodes.append(remove_snooze)
    
    print('Added 6 new nodes')
    
    # 9. Добавить connections
    # Action Switch уже имеет выходы [0-4], добавляем [5] answered и [6] snooze
    main = connections['Action Switch']['main']
    main.append([{"node": "Answered Response", "type": "main", "index": 0}])  # [5]
    main.append([{"node": "Snooze Handover", "type": "main", "index": 0}])     # [6]
    
    connections['Answered Response'] = {"main": [[{"node": "Answer Callback Answered", "type": "main", "index": 0}]]}
    connections['Answer Callback Answered'] = {"main": [[{"node": "Remove Buttons Answered", "type": "main", "index": 0}]]}
    connections['Snooze Handover'] = {"main": [[{"node": "Snooze Response", "type": "main", "index": 0}]]}
    connections['Snooze Response'] = {"main": [[{"node": "Answer Callback Snooze", "type": "main", "index": 0}]]}
    connections['Answer Callback Snooze'] = {"main": [[{"node": "Remove Buttons Snooze", "type": "main", "index": 0}]]}
    
    print('Added connections')
    
    return True

def main():
    print('=== Adding Monitor Callbacks ===')
    
    data = get_workflow()
    if 'nodes' not in data:
        print(f'ERROR: {data}')
        return 1
    
    with open('/home/zhan/truffles/ops/9_Telegram_Callback_before_monitor.json', 'w') as f:
        json.dump(data, f, indent=2)
    print('Backup saved')
    
    if not add_callbacks(data):
        return 0
    
    resp = update_workflow(data)
    if resp.status_code == 200:
        print('SUCCESS: Workflow updated')
    else:
        print(f'ERROR: {resp.status_code} - {resp.text[:200]}')
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
