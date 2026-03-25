import requests
import json

QDRANT_URL = 'http://172.24.0.3:6333'
API_KEY = 'REDACTED_PASSWORD'
COLLECTION = 'semantic_routes'

headers = {
    'api-key': API_KEY,
    'Content-Type': 'application/json'
}

# 1. Delete collection if exists
print(f'Deleting collection {COLLECTION} if exists...')
r = requests.delete(f'{QDRANT_URL}/collections/{COLLECTION}', headers=headers)
print(f'Delete: {r.status_code}')

# 2. Create collection
print(f'Creating collection {COLLECTION}...')
create_payload = {
    'vectors': {
        'size': 1536,  # text-embedding-3-small dimension
        'distance': 'Cosine'
    }
}
r = requests.put(f'{QDRANT_URL}/collections/{COLLECTION}', headers=headers, json=create_payload)
print(f'Create: {r.status_code} - {r.text}')

print('Done!')
