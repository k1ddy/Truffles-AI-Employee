import requests

# Удалить все точки
r = requests.post(
    'http://172.24.0.3:6333/collections/truffles_knowledge/points/delete',
    headers={'api-key': 'Iddqd777!', 'Content-Type': 'application/json'},
    json={'filter': {'must': [{'has_id': list(range(1, 1000))}]}}
)
print('Delete attempt 1:', r.status_code)

# Или удалить коллекцию и создать заново
r = requests.delete(
    'http://172.24.0.3:6333/collections/truffles_knowledge',
    headers={'api-key': 'Iddqd777!'}
)
print('Delete collection:', r.status_code)

r = requests.put(
    'http://172.24.0.3:6333/collections/truffles_knowledge',
    headers={'api-key': 'Iddqd777!', 'Content-Type': 'application/json'},
    json={'vectors': {'size': 1536, 'distance': 'Cosine'}}
)
print('Create collection:', r.status_code)
