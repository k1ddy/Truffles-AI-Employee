#!/usr/bin/env python3
"""Manual sync demo_salon to Qdrant - workaround for nested loop bug"""
import requests
import hashlib
import re
from pathlib import Path

CLIENT_SLUG = "demo_salon"

# Use Docker network IPs
BGE_URL = "http://172.24.0.8:80/embed"  # bge-m3 container
QDRANT_URL = "http://172.24.0.3:6333"   # qdrant container

# BGE-M3 embedding
def get_embedding(text):
    resp = requests.post(BGE_URL, json={"inputs": text})
    return resp.json()[0]

# Qdrant upsert
def upsert_to_qdrant(points):
    resp = requests.put(
        f"{QDRANT_URL}/collections/truffles_knowledge/points",
        headers={"api-key": "REDACTED_PASSWORD", "Content-Type": "application/json"},
        json={"points": points}
    )
    return resp.json()

# Split text into chunks by headers
def split_into_chunks(text, doc_name, doc_id):
    chunks = []
    sections = re.split(r'\n(?=##?\s)', text)
    
    for i, section in enumerate(sections):
        section = section.strip()
        if len(section) < 50:
            continue
            
        # Extract title from first line
        lines = section.split('\n')
        title = lines[0].replace('#', '').strip() if lines else f"Section {i}"
        
        chunks.append({
            "content": section,
            "metadata": {
                "client_slug": CLIENT_SLUG,
                "doc_id": doc_id,
                "doc_name": doc_name,
                "section_title": title,
                "section_index": i
            }
        })
    
    return chunks

# Files to sync (from Google Drive)
FILES = [
    ("1YR5B8cfdMANXOaoigV1E9vHdwrhRbJDa", "rules.md"),
    ("1AlRb6M1Ut_2eXlPrEV_UbK1YCjd6BxQn", "objections.md"),
    ("1jjw7xmkSQyZ4ldoVDhm5ODOPUaNlDVtB", "faq.md"),
    ("1BcnZhClmc_A-ZcnE9IKlIGFQVkSyJcJO", "services.md"),
]

# Read files from local copies (already uploaded to Drive)
docs_base = Path("/home/zhan/truffles/knowledge/demo_salon")
if not docs_base.exists():
    docs_base = Path("/home/zhan/truffles/ops/demo_salon_docs")

LOCAL_FILES = {
    "rules.md": str(docs_base / "rules.md"),
    "objections.md": str(docs_base / "objections.md"),
    "faq.md": str(docs_base / "faq.md"),
    "services.md": str(docs_base / "services.md"),
}

print(f"Syncing {CLIENT_SLUG}...")

all_points = []
point_id = 200000000  # Start from high number to avoid conflicts

for doc_id, doc_name in FILES:
    local_path = LOCAL_FILES.get(doc_name)
    if not local_path:
        print(f"  Skip {doc_name} - no local path")
        continue
    
    try:
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"  Skip {doc_name} - file not found")
        continue
    
    chunks = split_into_chunks(content, doc_name, doc_id)
    print(f"  {doc_name}: {len(chunks)} chunks")
    
    for chunk in chunks:
        vector = get_embedding(chunk["content"])
        all_points.append({
            "id": point_id,
            "vector": vector,
            "payload": chunk
        })
        point_id += 1

if all_points:
    print(f"\nUpserting {len(all_points)} points to Qdrant...")
    result = upsert_to_qdrant(all_points)
    print(f"Result: {result}")
else:
    print("No points to upsert")
