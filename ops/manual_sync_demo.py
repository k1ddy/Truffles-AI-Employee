#!/usr/bin/env python3
"""Manual sync demo_salon to Qdrant - workaround for nested loop bug"""
import hashlib
import os
import re
import subprocess

import requests
from pathlib import Path

CLIENT_SLUG = "demo_salon"

def _resolve_docker_ip(container_name: str) -> str | None:
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", container_name],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    ip = result.stdout.strip()
    return ip or None


BGE_URL = os.environ.get("BGE_M3_URL")
if not BGE_URL:
    bge_ip = _resolve_docker_ip("bge-m3")
    BGE_URL = f"http://{bge_ip}:80/embed" if bge_ip else "http://bge-m3:80/embed"

QDRANT_URL = os.environ.get("QDRANT_URL")
if not QDRANT_URL:
    qdrant_ip = _resolve_docker_ip("truffles_qdrant_1")
    QDRANT_URL = f"http://{qdrant_ip}:6333" if qdrant_ip else "http://qdrant:6333"

QDRANT_API_KEY = (
    os.environ.get("QDRANT_API_KEY")
    or os.environ.get("QDRANT__SERVICE__API_KEY")
    or "REDACTED_PASSWORD"
)
QDRANT_API_KEY = QDRANT_API_KEY.strip()

# BGE-M3 embedding
def get_embedding(text):
    resp = requests.post(BGE_URL, json={"inputs": text})
    return resp.json()[0]

# Qdrant upsert
def upsert_to_qdrant(points):
    resp = requests.put(
        f"{QDRANT_URL}/collections/truffles_knowledge/points",
        headers={"api-key": QDRANT_API_KEY, "Content-Type": "application/json"},
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
docs_base = Path("/home/zhan/truffles-main/knowledge/demo_salon")
if not docs_base.exists():
    docs_base = Path("/home/zhan/truffles-main/ops/demo_salon_docs")

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
