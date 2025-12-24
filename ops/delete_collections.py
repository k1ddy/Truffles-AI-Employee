import requests

QDRANT_URL = 'http://172.24.0.3:6333'
API_KEY = 'REDACTED_PASSWORD'

to_delete = ['FAQ_ru', 'semantic_routes', 'truffles_intents']

for name in to_delete:
    r = requests.delete(
        f'{QDRANT_URL}/collections/{name}',
        headers={'api-key': API_KEY}
    )
    print(f'Delete {name}: {r.status_code}')

# Verify
r = requests.get(f'{QDRANT_URL}/collections', headers={'api-key': API_KEY})
collections = r.json().get('result', {}).get('collections', [])
print()
print('Remaining collections:')
for c in collections:
    print(f'- {c.get("name")}')
