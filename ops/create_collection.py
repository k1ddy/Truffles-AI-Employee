import requests

r = requests.put(
    'http://172.24.0.3:6333/collections/truffles_knowledge',
    headers={'api-key': 'REDACTED_PASSWORD', 'Content-Type': 'application/json'},
    json={
        'vectors': {
            'size': 1536,
            'distance': 'Cosine'
        }
    }
)
print('Create collection:', r.status_code, r.text)
