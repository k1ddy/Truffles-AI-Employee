#!/usr/bin/env python3
"""Test full BGE-M3 -> Qdrant flow directly"""
import requests
import json

BGE_URL = "http://172.24.0.8:80/embed"
QDRANT_URL = "http://172.24.0.3:6333"
QDRANT_KEY = "REDACTED_PASSWORD"
COLLECTION = "truffles_knowledge"

# Test chunk
chunk = {
    "pageContent": "Truffles — это AI-автоответчик для бизнеса в WhatsApp.",
    "metadata": {
        "doc_id": "test-doc-123",
        "section_index": 0,
        "doc_name": "test.md"
    }
}

print("=== Step 1: Get embedding from BGE-M3 ===")
bge_response = requests.post(BGE_URL, json={"inputs": chunk["pageContent"]})
print(f"Status: {bge_response.status_code}")
bge_json = bge_response.json()
print(f"Response type: {type(bge_json)}")
print(f"Response length: {len(bge_json)}")
print(f"First element type: {type(bge_json[0])}")
print(f"Vector length: {len(bge_json[0])}")

# Extract vector
vector = bge_json[0]
print(f"Vector sample: {vector[:3]}")

print("\n=== Step 2: Prepare Qdrant payload ===")
# Generate ID
id_str = f"{chunk['metadata']['doc_id']}-{chunk['metadata']['section_index']}"
hash_val = 0
for c in id_str:
    hash_val = ((hash_val << 5) - hash_val) + ord(c)
    hash_val = hash_val & 0xFFFFFFFF  # 32-bit unsigned
point_id = hash_val

payload = {
    "points": [
        {
            "id": point_id,
            "vector": vector,
            "payload": {
                "content": chunk["pageContent"],
                "metadata": chunk["metadata"]
            }
        }
    ]
}

print(f"Point ID: {point_id} (type: {type(point_id)})")
print(f"Vector length: {len(payload['points'][0]['vector'])}")
print(f"Vector element type: {type(payload['points'][0]['vector'][0])}")

print("\n=== Step 3: Upsert to Qdrant ===")
print(f"Payload preview: {json.dumps(payload, indent=2)[:500]}...")

qdrant_response = requests.put(
    f"{QDRANT_URL}/collections/{COLLECTION}/points",
    json=payload,
    headers={"api-key": QDRANT_KEY}
)
print(f"Status: {qdrant_response.status_code}")
print(f"Response: {qdrant_response.text}")

if qdrant_response.status_code == 200:
    print("\n=== SUCCESS! Flow works correctly ===")
else:
    print("\n=== FAILED ===")
    print("Full payload for debugging:")
    print(json.dumps(payload, indent=2)[:1000])
