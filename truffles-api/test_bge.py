import httpx

try:
    r = httpx.post('http://bge-m3:80/embed', json={'inputs': 'test'}, timeout=30)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
