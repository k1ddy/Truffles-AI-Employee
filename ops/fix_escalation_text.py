#!/usr/bin/env python3
"""Add escalation_text to Get Topic ID"""

import json
import requests

API_KEY = 'REDACTED_JWT'

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/fFPEbTNlkBSjo66A',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()

# Update Get Topic ID to include escalation_text
for node in data['nodes']:
    if node['name'] == 'Get Topic ID':
        node['parameters']['jsCode'] = """// Получаем topic_id из существующего или нового
const prep = $('Prepare Data').first().json;
let topicId;

try {
  // Если создали новый топик
  topicId = $('Create Topic').first()?.json?.result?.message_thread_id;
} catch(e) {}

if (!topicId) {
  // Если использовали существующий
  topicId = $('Get Existing Topic').first()?.json?.telegram_topic_id;
}

// Формируем текст эскалации
const escalationText = `📩 НОВАЯ ЗАЯВКА

📞 Телефон: ${prep.phone}
💬 Сообщение: ${prep.message}

Клиент ждёт ответа.`;

return [{
  json: {
    ...prep,
    topic_id: topicId,
    escalation_text: escalationText
  }
}];"""
        print("Updated Get Topic ID with escalation_text")
        break

# Update workflow
resp = requests.put(
    'https://n8n.truffles.kz/api/v1/workflows/fFPEbTNlkBSjo66A',
    headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
    json={
        'name': data['name'],
        'nodes': data['nodes'],
        'connections': data['connections'],
        'settings': data.get('settings', {})
    }
)
print(f"Status: {resp.status_code}")
