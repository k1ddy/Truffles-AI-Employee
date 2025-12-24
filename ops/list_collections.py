import requests

r = requests.get(
    'http://172.24.0.3:6333/collections',
    headers={'api-key': 'REDACTED_PASSWORD'}
)
data = r.json()
collections = data.get('result', {}).get('collections', [])
print(f'Total collections: {len(collections)}')
print()
for c in collections:
    name = c.get('name', '?')
    print(f'- {name}')
