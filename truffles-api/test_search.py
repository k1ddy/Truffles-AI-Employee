import httpx

QDRANT_HOST = "http://qdrant:6333"
QDRANT_API_KEY = "Iddqd777!"
BGE_M3_URL = "http://bge-m3:80/embed"

# Get embedding
query = "цены на стрижку"
r = httpx.post(BGE_M3_URL, json={"inputs": query}, timeout=30)
embedding = r.json()
print(f"Embedding type: {type(embedding)}, len: {len(embedding)}")

# Handle nested array
if isinstance(embedding, list) and len(embedding) > 0:
    if isinstance(embedding[0], list):
        embedding = embedding[0]
print(f"Vector len: {len(embedding)}")

# Search without filter first
r = httpx.post(
    f"{QDRANT_HOST}/collections/truffles_knowledge/points/search",
    headers={"api-key": QDRANT_API_KEY},
    json={
        "vector": embedding,
        "limit": 3,
        "with_payload": True,
    }
)
print(f"Search result: {r.status_code}")
print(r.text[:1000])
