#!/usr/bin/env python3
"""
Add timeout history to escalation message:
1. Add node to check previous timeouts
2. Update message to show history if exists
"""

import json
import requests

API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4'

# Get current workflow
resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/fFPEbTNlHBU92e4p',
    headers={'X-N8N-API-KEY': API_KEY}
)

if resp.status_code == 404:
    print("Workflow fFPEbTNlHBU92e4p not found, trying to find by name...")
    resp = requests.get(
        'https://n8n.truffles.kz/api/v1/workflows',
        headers={'X-N8N-API-KEY': API_KEY}
    )
    workflows = resp.json()['data']
    for w in workflows:
        if '8_Telegram_Adapter' in w['name']:
            print(f"Found: {w['id']} - {w['name']}")
            resp = requests.get(
                f"https://n8n.truffles.kz/api/v1/workflows/{w['id']}",
                headers={'X-N8N-API-KEY': API_KEY}
            )
            break

data = resp.json()
if 'nodes' not in data:
    print(f"Error: {data}")
    exit(1)

nodes = data['nodes']
connections = data['connections']

print("=== Adding Timeout History to 8_Telegram_Adapter ===")

# 1. Add "Check Previous Timeout" node
check_timeout = {
    "parameters": {
        "operation": "executeQuery",
        "query": """SELECT 
  h.user_message as prev_message,
  h.resolved_at as timeout_at,
  EXTRACT(EPOCH FROM (NOW() - h.resolved_at)) / 3600 as hours_ago
FROM handovers h
JOIN conversations c ON c.id = h.conversation_id
WHERE c.id = '{{ $json.conversation_id }}'
  AND h.status = 'timeout'
  AND h.resolved_at > NOW() - INTERVAL '24 hours'
ORDER BY h.resolved_at DESC
LIMIT 1;""",
        "options": {}
    },
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.6,
    "position": [-464, 304],
    "id": "tg-check-timeout-001",
    "name": "Check Previous Timeout",
    "credentials": {
        "postgres": {
            "id": "SUHrbh39Ig0fBusT",
            "name": "ChatbotDB"
        }
    }
}

# Check if already exists
exists = any(n['name'] == 'Check Previous Timeout' for n in nodes)
if not exists:
    nodes.append(check_timeout)
    print("  Added: Check Previous Timeout")
else:
    print("  Check Previous Timeout already exists")

# 2. Add "Build Message" node that combines data
build_message = {
    "parameters": {
        "jsCode": """const prep = $('Prepare Data').first().json;
const timeout = $('Check Previous Timeout').first()?.json;

let historyText = '';
if (timeout && timeout.prev_message) {
  const hoursAgo = Math.round(timeout.hours_ago || 0);
  historyText = `\\n\\n⚠️ ИСТОРИЯ: timeout ${hoursAgo}ч назад (не получил ответ)\\nПредыдущий вопрос: "${timeout.prev_message.substring(0, 100)}"`;
}

const messageText = `🚨 НОВАЯ ЗАЯВКА${historyText ? ' (ПОВТОРНАЯ)' : ''}

📱 Телефон: ${prep.phone}
👤 Клиент: ${prep.client_name}
🏢 Бизнес: ${prep.business_name}${historyText}

💬 Сообщение:
${prep.message}`;

return [{
  json: {
    ...prep,
    escalation_text: messageText,
    has_history: !!historyText
  }
}];"""
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [-240, 304],
    "id": "tg-build-msg-001",
    "name": "Build Message"
}

exists = any(n['name'] == 'Build Message' for n in nodes)
if not exists:
    nodes.append(build_message)
    print("  Added: Build Message")
else:
    print("  Build Message already exists")

# 3. Update Send Escalation to use escalation_text
for node in nodes:
    if node['name'] == 'Send Escalation':
        params = node['parameters']['bodyParameters']['parameters']
        for p in params:
            if p['name'] == 'text':
                # Check if already updated
                if 'escalation_text' not in p['value']:
                    p['value'] = "={{ $json.escalation_text }}"
                    print("  Updated: Send Escalation text")
                else:
                    print("  Send Escalation already updated")
        break

# 4. Update connections
# Prepare Data -> Check Previous Timeout -> Build Message -> Get Existing Topic
connections['Prepare Data'] = {
    "main": [[{"node": "Check Previous Timeout", "type": "main", "index": 0}]]
}
connections['Check Previous Timeout'] = {
    "main": [[{"node": "Build Message", "type": "main", "index": 0}]]
}
connections['Build Message'] = {
    "main": [[{"node": "Get Existing Topic", "type": "main", "index": 0}]]
}
print("  Updated connections")

# 5. Update Get Topic ID to include escalation_text
for node in nodes:
    if node['name'] == 'Get Topic ID':
        code = node['parameters'].get('jsCode', '')
        if 'escalation_text' not in code:
            node['parameters']['jsCode'] = """// Получаем topic_id из существующего или нового
const prep = $('Build Message').first().json;
let topicId;

try {
  // Если создали новый топик
  topicId = $('Create Topic').first()?.json?.result?.message_thread_id;
} catch(e) {}

if (!topicId) {
  // Если использовали существующий
  topicId = $('Get Existing Topic').first()?.json?.telegram_topic_id;
}

return [{
  json: {
    ...prep,
    topic_id: topicId
  }
}];"""
            print("  Updated: Get Topic ID")
        break

# Save
resp = requests.put(
    f"https://n8n.truffles.kz/api/v1/workflows/{data['id']}",
    headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
    json={'name': data['name'], 'nodes': nodes, 'connections': connections, 'settings': data.get('settings', {})}
)
print(f"\nStatus: {resp.status_code}")

if resp.status_code != 200:
    print(resp.text[:500])
