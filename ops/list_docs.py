#!/usr/bin/env python3
"""List unique documents in Qdrant collection"""
import requests

QDRANT_URL = 'http://172.24.0.3:6333'
API_KEY = 'REDACTED_PASSWORD'

resp = requests.post(
    f'{QDRANT_URL}/collections/truffles_knowledge/points/scroll',
    json={'limit': 100, 'with_payload': True, 'with_vector': False},
    headers={'api-key': API_KEY}
)
points = resp.json().get('result', {}).get('points', [])

doc_names = set()
for p in points:
    meta = p.get('payload', {}).get('metadata', {})
    name = meta.get('doc_name') or meta.get('source') or 'unknown'
    doc_names.add(name)

print('Documents in Qdrant:')
for n in sorted(doc_names):
    print(f'  - {n}')
print(f'\nTotal unique docs: {len(doc_names)}')
print(f'Total chunks: {len(points)}')
