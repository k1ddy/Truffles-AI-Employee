#!/usr/bin/env python3
"""Check RAG chunks"""
import requests
import json
import sys

QDRANT_URL = 'http://172.24.0.3:6333'
QDRANT_KEY = 'REDACTED_PASSWORD'
COLLECTION = 'truffles_knowledge'

# Get ALL chunks
resp = requests.post(
    f'{QDRANT_URL}/collections/{COLLECTION}/points/scroll',
    headers={'api-key': QDRANT_KEY, 'Content-Type': 'application/json'},
    json={'limit': 100, 'with_payload': True, 'with_vector': False}
)

data = resp.json()
points = data.get('result', {}).get('points', [])

print(f"Total chunks: {len(points)}")
print("=" * 60)

# Analyze by document with dates
by_doc = {}

for p in points:
    payload = p.get('payload', {})
    content = payload.get('content', '')
    metadata = payload.get('metadata', {})
    doc = metadata.get('doc_name', 'unknown')
    updated = metadata.get('updated_at', 'unknown')
    
    if doc not in by_doc:
        by_doc[doc] = {'chunks': 0, 'updated': updated, 'total_size': 0}
    by_doc[doc]['chunks'] += 1
    by_doc[doc]['total_size'] += len(content)

print(f"\nDocuments in Qdrant:")
for doc, info in sorted(by_doc.items()):
    print(f"  {doc}: {info['chunks']} chunks, {info['total_size']} chars, updated: {info['updated']}")
