import os
import httpx

QDRANT_HOST = os.environ.get("QDRANT_HOST", "http://qdrant:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")

# Check collections
r = httpx.get(f"{QDRANT_HOST}/collections", headers={"api-key": QDRANT_API_KEY})
print(f"Collections: {r.status_code} - {r.text[:500]}")

# Check truffles_knowledge collection
r = httpx.get(f"{QDRANT_HOST}/collections/truffles_knowledge", headers={"api-key": QDRANT_API_KEY})
print(f"Collection info: {r.status_code} - {r.text[:500]}")
