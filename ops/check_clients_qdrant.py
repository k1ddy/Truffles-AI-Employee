#!/usr/bin/env python3
import requests
from collections import Counter

QDRANT_URL = "http://172.24.0.3:6333"

resp = requests.post(
    f"{QDRANT_URL}/collections/truffles_knowledge/points/scroll",
    headers={"api-key": "REDACTED_PASSWORD", "Content-Type": "application/json"},
    json={"limit": 100, "with_payload": True}
)
data = resp.json()

clients = Counter()
for point in data.get("result", {}).get("points", []):
    payload = point.get("payload", {})
    metadata = payload.get("metadata", {})
    client_slug = metadata.get("client_slug", "unknown")
    clients[client_slug] += 1

print("Chunks by client:")
for client, count in clients.most_common():
    print(f"  {client}: {count}")
