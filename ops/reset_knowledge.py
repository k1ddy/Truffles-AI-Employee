#!/usr/bin/env python3
" \\Полный сброс коллекции truffles_knowledge\\\
import requests
import sys

QDRANT = 'http://172.24.0.3:6333'
API_KEY = 'Iddqd777!'
HEADERS = {'api-key': API_KEY, 'Content-Type': 'application/json'}

# Удалить
r = requests.delete(f'{QDRANT}/collections/truffles_knowledge', headers=HEADERS)
print(f'Delete: {r.status_code}')

# Создать заново
r = requests.put(
 f'{QDRANT}/collections/truffles_knowledge',
 headers=HEADERS,
 json={'vectors': {'size': 1536, 'distance': 'Cosine'}}
)
print(f'Create: {r.status_code}')

# Проверить
r = requests.post(f'{QDRANT}/collections/truffles_knowledge/points/count', headers=HEADERS, json={})
count = r.json().get('result', {}).get('count', '?')
print(f'Points: {count}')
