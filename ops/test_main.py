import requests
import time

tests = [
    'сколько стоит бот?',
    'как ухаживать за собакой?',
]

for msg in tests:
    payload = {
        'message': msg,
        'messageType': 'text',
        'metadata': {
            'remoteJid': '77001234567@s.whatsapp.net',
            'sender': 'Test',
            'messageId': 'test123',
            'timestamp': time.time()
        }
    }
    r = requests.post('https://n8n.truffles.kz/webhook/flow', json=payload)
    print(msg[:35], '|', r.status_code, '|', r.text[:80] if r.text else 'empty')
