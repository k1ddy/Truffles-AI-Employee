#!/usr/bin/env python3
import requests
import sys

url = "http://172.24.0.3:6333/collections/truffles_knowledge/points/scroll"
headers = {"api-key": "REDACTED_PASSWORD"}

doc_name = sys.argv[1] if len(sys.argv) > 1 else "faq.md"

payload = {
    "filter": {
        "must": [{"key": "metadata.doc_name", "match": {"value": doc_name}}]
    },
    "limit": 50,
    "with_payload": True
}

r = requests.post(url, json=payload, headers=headers)
points = r.json().get("result", {}).get("points", [])

print(f"Chunks in {doc_name}: {len(points)}\n")

for p in points:
    title = p["payload"].get("metadata", {}).get("section_title", "?")
    content = p["payload"].get("content", "")[:150].replace("\n", " ")
    print(f"--- {title} ---")
    print(content + "...")
    print()
