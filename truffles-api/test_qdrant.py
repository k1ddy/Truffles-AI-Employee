import httpx

QDRANT_HOST = "http://qdrant:6333"
QDRANT_API_KEY = "Iddqd777!"

# Check collections
r = httpx.get(f"{QDRANT_HOST}/collections", headers={"api-key": QDRANT_API_KEY})
print(f"Collections: {r.status_code} - {r.text[:500]}")

# Check truffles_knowledge collection
r = httpx.get(f"{QDRANT_HOST}/collections/truffles_knowledge", headers={"api-key": QDRANT_API_KEY})
print(f"Collection info: {r.status_code} - {r.text[:500]}")
