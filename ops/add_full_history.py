#!/usr/bin/env python3
"""
Добавляет полную историю в messages:
1. role='manager' — ответы менеджера
2. role='system' — события (эскалация, закрытие)

Изменения:
- 9_Telegram_Callback: Save Manager to History (после Send Manager Reply)
- 9_Telegram_Callback: Save Resolved to History (в resolve flow)
- 7_Escalation_Handler: Save Escalation to History (после Create Handover)
"""

import json
import requests

API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4'
BASE_URL = 'https://n8n.truffles.kz/api/v1'

CALLBACK_ID = 'HQOWuMDIBPphC86v'
ESCALATION_ID = '7jGZrdbaAAvtTnQX'

def get_workflow(workflow_id):
    resp = requests.get(
        f'{BASE_URL}/workflows/{workflow_id}',
        headers={'X-N8N-API-KEY': API_KEY}
    )
    return resp.json()

def update_workflow(workflow_id, data):
    payload = {
        'name': data.get('name'),
        'nodes': data.get('nodes'),
        'connections': data.get('connections'),
        'settings': data.get('settings', {}),
    }
    resp = requests.put(
        f'{BASE_URL}/workflows/{workflow_id}',
        headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
        json=payload
    )
    return resp

def find_node(nodes, name):
    for n in nodes:
        if n['name'] == name:
            return n
    return None

def add_manager_history_to_callback(data):
    """Добавляет Save Manager to History в 9_Telegram_Callback"""
    nodes = data['nodes']
    connections = data['connections']
    
    # Проверить что ещё не добавлено
    if find_node(nodes, 'Save Manager to History'):
        print('  SKIP: Save Manager to History already exists')
        return False
    
    # Найти Find Handover Data чтобы получить conversation_id
    # Save Manager Message уже существует, добавим после него
    
    # Создать ноду Save Manager to History
    save_manager_history = {
        "parameters": {
            "operation": "executeQuery",
            "query": "INSERT INTO messages (conversation_id, client_id, role, content, metadata)\nSELECT \n  h.conversation_id,\n  c.client_id,\n  'manager',\n  '{{ $('Parse Message').first().json.text.replace(/'/g, \"''\") }}',\n  jsonb_build_object('manager_name', '{{ $('Parse Message').first().json.manager_name }}', 'manager_id', '{{ $('Parse Message').first().json.manager_id }}')\nFROM handovers h\nJOIN conversations c ON c.id = h.conversation_id\nWHERE h.id = '{{ $('Find Handover Data').first().json.handover_id }}';",
            "options": {}
        },
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.6,
        "position": [688, 720],
        "id": "cb-save-manager-history-001",
        "name": "Save Manager to History",
        "credentials": {
            "postgres": {
                "id": "SUHrbh39Ig0fBusT",
                "name": "ChatbotDB"
            }
        }
    }
    nodes.append(save_manager_history)
    print('  Added: Save Manager to History')
    
    # Изменить connections: Save Manager Message -> Save Manager to History -> Confirm Sent
    # Текущий: Save Manager Message -> Confirm Sent to Topic
    # Новый: Save Manager Message -> Save Manager to History -> Confirm Sent to Topic
    
    if 'Save Manager Message' in connections:
        # Получить текущий target
        current_targets = connections['Save Manager Message']['main'][0]
        # Заменить на Save Manager to History
        connections['Save Manager Message']['main'][0] = [{"node": "Save Manager to History", "type": "main", "index": 0}]
        # Save Manager to History -> старый target
        connections['Save Manager to History'] = {"main": [current_targets]}
        print('  Updated connections: Save Manager Message -> Save Manager to History -> Confirm Sent')
    
    return True

def add_resolved_history_to_callback(data):
    """Добавляет Save Resolved to History в resolve flow"""
    nodes = data['nodes']
    connections = data['connections']
    
    if find_node(nodes, 'Save Resolved to History'):
        print('  SKIP: Save Resolved to History already exists')
        return False
    
    # Создать ноду
    save_resolved_history = {
        "parameters": {
            "operation": "executeQuery",
            "query": "INSERT INTO messages (conversation_id, client_id, role, content, metadata)\nSELECT \n  h.conversation_id,\n  c.client_id,\n  'system',\n  '✓ Вопрос решён менеджером',\n  jsonb_build_object('event', 'resolved', 'manager_name', '{{ $('Parse Callback').first().json.manager_name }}')\nFROM handovers h\nJOIN conversations c ON c.id = h.conversation_id\nWHERE h.id = '{{ $('Merge Token').first().json.handover_id }}';",
            "options": {}
        },
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.6,
        "position": [544, 400],
        "id": "cb-save-resolved-history-001",
        "name": "Save Resolved to History",
        "credentials": {
            "postgres": {
                "id": "SUHrbh39Ig0fBusT",
                "name": "ChatbotDB"
            }
        }
    }
    nodes.append(save_resolved_history)
    print('  Added: Save Resolved to History')
    
    # Вставить между Unmute Bot и Resolve Response
    # Текущий: Unmute Bot -> Resolve Response
    # Новый: Unmute Bot -> Save Resolved to History -> Resolve Response
    
    if 'Unmute Bot' in connections:
        current_targets = connections['Unmute Bot']['main'][0]
        connections['Unmute Bot']['main'][0] = [{"node": "Save Resolved to History", "type": "main", "index": 0}]
        connections['Save Resolved to History'] = {"main": [current_targets]}
        print('  Updated connections: Unmute Bot -> Save Resolved to History -> Resolve Response')
    
    return True

def add_escalation_history(data):
    """Добавляет Save Escalation to History в 7_Escalation_Handler"""
    nodes = data['nodes']
    connections = data['connections']
    
    if find_node(nodes, 'Save Escalation to History'):
        print('  SKIP: Save Escalation to History already exists')
        return False
    
    # Создать ноду
    # После Create Handover: $json.id = handover_id, Decide Action имеет conversation_id, client_id, reason
    save_escalation_history = {
        "parameters": {
            "operation": "executeQuery",
            "query": "INSERT INTO messages (conversation_id, client_id, role, content, metadata)\nVALUES (\n  '{{ $(\"Decide Action\").first().json.conversation_id }}',\n  '{{ $(\"Decide Action\").first().json.client_id }}',\n  'system',\n  '→ Передано менеджеру',\n  jsonb_build_object('event', 'escalation', 'reason', '{{ $(\"Decide Action\").first().json.reason }}', 'handover_id', '{{ $json.id }}')\n);",
            "options": {}
        },
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.6,
        "position": [432, 208],
        "id": "esc-save-history-001",
        "name": "Save Escalation to History",
        "credentials": {
            "postgres": {
                "id": "SUHrbh39Ig0fBusT",
                "name": "ChatbotDB"
            }
        }
    }
    nodes.append(save_escalation_history)
    print('  Added: Save Escalation to History')
    
    # Вставить после Create Handover, перед Call Telegram Adapter
    # Нужно найти Create Handover в connections
    
    if 'Create Handover' in connections:
        current_targets = connections['Create Handover']['main'][0]
        connections['Create Handover']['main'][0] = [{"node": "Save Escalation to History", "type": "main", "index": 0}]
        connections['Save Escalation to History'] = {"main": [current_targets]}
        print('  Updated connections: Create Handover -> Save Escalation to History -> Call Telegram Adapter')
    
    return True

def main():
    print('=== Adding Full History Support ===\n')
    
    # 1. Update 9_Telegram_Callback
    print('1. Updating 9_Telegram_Callback...')
    callback_data = get_workflow(CALLBACK_ID)
    if 'nodes' not in callback_data:
        print(f'   ERROR: {callback_data}')
        return 1
    
    # Backup
    with open('/home/zhan/truffles/ops/9_Telegram_Callback_before_history.json', 'w') as f:
        json.dump(callback_data, f, indent=2)
    print('   Backup saved')
    
    changed1 = add_manager_history_to_callback(callback_data)
    changed2 = add_resolved_history_to_callback(callback_data)
    
    if changed1 or changed2:
        resp = update_workflow(CALLBACK_ID, callback_data)
        if resp.status_code == 200:
            print('   SUCCESS: 9_Telegram_Callback updated')
        else:
            print(f'   ERROR: {resp.status_code} - {resp.text[:200]}')
            return 1
    
    # 2. Update 7_Escalation_Handler
    print('\n2. Updating 7_Escalation_Handler...')
    escalation_data = get_workflow(ESCALATION_ID)
    if 'nodes' not in escalation_data:
        print(f'   ERROR: {escalation_data}')
        return 1
    
    # Backup
    with open('/home/zhan/truffles/ops/7_Escalation_Handler_before_history.json', 'w') as f:
        json.dump(escalation_data, f, indent=2)
    print('   Backup saved')
    
    changed3 = add_escalation_history(escalation_data)
    
    if changed3:
        resp = update_workflow(ESCALATION_ID, escalation_data)
        if resp.status_code == 200:
            print('   SUCCESS: 7_Escalation_Handler updated')
        else:
            print(f'   ERROR: {resp.status_code} - {resp.text[:200]}')
            return 1
    
    print('\n=== Done ===')
    print('Test: Create escalation, manager reply, resolve — check messages table')
    return 0

if __name__ == '__main__':
    exit(main())
