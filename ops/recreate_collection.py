#!/usr/bin/env python3
"""Recreate Qdrant collection for BGE-M3 (1024 dimensions)"""
import requests

QDRANT_URL = "http://172.24.0.3:6333"
QDRANT_API_KEY = "REDACTED_PASSWORD"
COLLECTION = "truffles_knowledge"

headers = {"api-key": QDRANT_API_KEY}

# 1. Delete existing collection
print(f"Deleting collection {COLLECTION}...")
r = requests.delete(f"{QDRANT_URL}/collections/{COLLECTION}", headers=headers)
print(f"Delete: {r.status_code} - {r.text}")

# 2. Create new collection with 1024 dimensions
print(f"\nCreating collection {COLLECTION} with 1024 dimensions...")
payload = {
    "vectors": {
        "size": 1024,
        "distance": "Cosine"
    }
}
r = requests.put(f"{QDRANT_URL}/collections/{COLLECTION}", json=payload, headers=headers)
print(f"Create: {r.status_code} - {r.text}")

# 3. Verify
print(f"\nVerifying collection...")
r = requests.get(f"{QDRANT_URL}/collections/{COLLECTION}", headers=headers)
info = r.json()
print(f"Collection info: {info}")
