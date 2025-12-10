import httpx

QDRANT_HOST = "http://qdrant:6333"
QDRANT_API_KEY = "Iddqd777!"

# Get some points to see client_slugs
r = httpx.post(
    f"{QDRANT_HOST}/collections/truffles_knowledge/points/scroll",
    headers={"api-key": QDRANT_API_KEY},
    json={"limit": 5, "with_payload": True}
)

data = r.json()
for point in data.get("result", {}).get("points", []):
    payload = point.get("payload", {})
    metadata = payload.get("metadata", {})
    print(f"client_slug: {metadata.get('client_slug')}, doc: {metadata.get('doc_name')}")
