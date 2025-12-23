import requests

r = requests.get(
    'http://172.24.0.3:6333/collections/truffles_knowledge',
    headers={'api-key': 'Iddqd777!'}
)
data = r.json()
count = data.get('result', {}).get('points_count', 0)
print(f'Points in truffles_knowledge: {count}')
