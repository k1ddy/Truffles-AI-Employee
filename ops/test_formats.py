#!/usr/bin/env python3
"""Test BGE-M3 and Qdrant API formats"""
import requests
import json

print("=== 1. BGE-M3 Response Format ===")
r = requests.post('http://172.24.0.8:80/embed', json={'inputs': 'тестовый текст'})
bge_response = r.json()
print(f"Status: {r.status_code}")
print(f"Type: {type(bge_response)}")
if isinstance(bge_response, list):
    print(f"Length: {len(bge_response)}")
    print(f"First element type: {type(bge_response[0])}")
    if isinstance(bge_response[0], list):
        print(f"Vector length: {len(bge_response[0])}")
        print(f"Sample: {bge_response[0][:3]}")
        vector = bge_response[0]
    else:
        print(f"First 3 values: {bge_response[:3]}")
        vector = bge_response
else:
    print(f"Response: {str(bge_response)[:200]}")
    vector = None

print("\n=== 2. Qdrant Upsert Format ===")
if vector:
    # Test upsert to Qdrant
    qdrant_payload = {
        "points": [
            {
                "id": 12345,
                "vector": vector,
                "payload": {
                    "content": "тестовый контент",
                    "metadata": {"doc_id": "test", "section_index": 0}
                }
            }
        ]
    }
    print(f"Payload structure: points[0].id={type(qdrant_payload['points'][0]['id'])}")
    print(f"Payload structure: points[0].vector length={len(qdrant_payload['points'][0]['vector'])}")
    
    r2 = requests.put(
        'http://172.24.0.3:6333/collections/truffles_knowledge/points',
        json=qdrant_payload,
        headers={'api-key': 'REDACTED_PASSWORD'}
    )
    print(f"Qdrant response: {r2.status_code}")
    print(f"Response: {r2.text}")
