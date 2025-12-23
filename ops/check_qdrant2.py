import urllib.request
import json

# Get collections
req = urllib.request.Request('http://172.24.0.3:6333/collections')
req.add_header('api-key', 'Iddqd777!')
r = urllib.request.urlopen(req)
print('Collections:', r.read().decode())

# Get points
data = json.dumps({'limit': 5, 'with_payload': True}).encode()
req2 = urllib.request.Request('http://172.24.0.3:6333/collections/truffles_knowledge/points/scroll', data=data, method='POST')
req2.add_header('api-key', 'Iddqd777!')
req2.add_header('Content-Type', 'application/json')
r2 = urllib.request.urlopen(req2)
print('Points:', r2.read().decode())
