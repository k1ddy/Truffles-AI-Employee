#!/usr/bin/env python3
import requests
import json

QDRANT_URL = 'http://172.24.0.3:6333'
API_KEY = 'REDACTED_PASSWORD'

resp = requests.post(
    f'{QDRANT_URL}/collections/truffles_knowledge/points/scroll',
    json={'limit': 3, 'with_payload': True, 'with_vector': False},
    headers={'api-key': API_KEY}
)
points = resp.json().get('result', {}).get('points', [])

for p in points:
    print('ID:', p.get('id'))
    payload = p.get('payload', {})
    print('Payload keys:', list(payload.keys()))
    print('Full payload:', json.dumps(payload, indent=2, ensure_ascii=False)[:500])
    print('---')
