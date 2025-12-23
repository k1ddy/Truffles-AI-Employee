import requests

r = requests.post(
    'http://172.24.0.3:6333/collections/truffles_knowledge/points/scroll',
    headers={'api-key': 'Iddqd777!', 'Content-Type': 'application/json'},
    json={'limit': 5, 'with_payload': True}
)
data = r.json()
points = data.get('result', {}).get('points', [])
print(f'Total points: {len(points)}')
for p in points:
    text = p.get('payload', {}).get('text', p.get('payload', {}).get('content', '?'))[:100]
    print(f'- {text}...')
