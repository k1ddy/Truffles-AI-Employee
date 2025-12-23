import requests

tests = [
    'сколько стоит собака?',
    'сколько стоит бот?',
    'можно создать сайт для собаки?',
]

for msg in tests:
    r = requests.post('https://n8n.truffles.kz/webhook/router-v3', json={'message': msg})
    data = r.json()
    print(msg, '|', data.get('status'), '|', data.get('label'), '|', data.get('score',0))
