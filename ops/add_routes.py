import requests
import os

QDRANT_URL = 'http://172.24.0.3:6333'
QDRANT_KEY = 'REDACTED_PASSWORD'
OPENAI_KEY = os.environ.get('OPENAI_API_KEY', '')
COLLECTION = 'semantic_routes'

new_phrases = [
    'сколько стоит собака',
    'сколько стоит кошка',
    'цена собаки',
    'купить собаку',
    'купить кошку',
    'сколько стоит машина',
    'сколько стоит квартира',
    'цена на еду',
    'сколько стоит телефон',
]

def get_embedding(text):
    r = requests.post(
        'https://api.openai.com/v1/embeddings',
        headers={'Authorization': f'Bearer {OPENAI_KEY}', 'Content-Type': 'application/json'},
        json={'model': 'text-embedding-3-small', 'input': text}
    )
    return r.json()['data'][0]['embedding']

points = []
start_id = 100

for i, phrase in enumerate(new_phrases):
    emb = get_embedding(phrase)
    points.append({
        'id': start_id + i,
        'vector': emb,
        'payload': {'text': phrase, 'label': 'out_of_domain', 'action': 'refuse'}
    })
    print(f'Added: {phrase}')

r = requests.put(
    f'{QDRANT_URL}/collections/{COLLECTION}/points',
    headers={'api-key': QDRANT_KEY, 'Content-Type': 'application/json'},
    json={'points': points}
)
print(f'Upsert: {r.status_code}')
