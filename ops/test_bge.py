#!/usr/bin/env python3
import requests

try:
    r = requests.post('http://bge-m3:80/embed', json={'inputs': 'test'}, timeout=10)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
