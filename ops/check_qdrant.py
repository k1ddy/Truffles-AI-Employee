import requests

# Get collections
r = requests.get('http://172.24.0.3:6333/collections', headers={'api-key': 'Iddqd777!'})
print('Collections:', r.json())

# Get points from truffles_knowledge
r2 = requests.post('http://172.24.0.3:6333/collections/truffles_knowledge/points/scroll', 
    headers={'api-key': 'Iddqd777!', 'Content-Type': 'application/json'},
    json={'limit': 5, 'with_payload': True})
print('Points:', r2.json())
