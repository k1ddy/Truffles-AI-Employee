#!/usr/bin/env python3
"""
Load intents into Qdrant with OpenAI embeddings.
Usage: python load_intents.py <openai_api_key>
"""

import json
import os
import sys
import requests
from typing import List

QDRANT_URL = "http://172.24.0.3:6333"
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
COLLECTION = "truffles_intents"
OPENAI_URL = "https://api.openai.com/v1/embeddings"
EMBEDDING_MODEL = "text-embedding-3-small"

def get_embeddings(texts: List[str], api_key: str) -> List[List[float]]:
    """Get embeddings from OpenAI."""
    response = requests.post(
        OPENAI_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": EMBEDDING_MODEL,
            "input": texts
        }
    )
    response.raise_for_status()
    data = response.json()
    return [item["embedding"] for item in data["data"]]

def upsert_points(points: List[dict]):
    """Upsert points to Qdrant."""
    response = requests.put(
        f"{QDRANT_URL}/collections/{COLLECTION}/points",
        headers={
            "api-key": QDRANT_API_KEY,
            "Content-Type": "application/json"
        },
        json={"points": points}
    )
    response.raise_for_status()
    return response.json()

def main():
    if not QDRANT_API_KEY:
        print("Missing QDRANT_API_KEY env var", file=sys.stderr)
        sys.exit(1)
    if len(sys.argv) < 2:
        print("Usage: python load_intents.py <openai_api_key>")
        sys.exit(1)
    
    api_key = sys.argv[1]
    
    # Load intents
    with open("intents.json", "r", encoding="utf-8") as f:
        intents = json.load(f)
    
    point_id = 1
    total_loaded = 0
    
    for category, examples in intents.items():
        print(f"Processing {category}: {len(examples)} examples...")
        
        # Get embeddings in batches of 50
        batch_size = 50
        for i in range(0, len(examples), batch_size):
            batch = examples[i:i+batch_size]
            
            # Get embeddings
            embeddings = get_embeddings(batch, api_key)
            
            # Create points
            points = []
            for text, embedding in zip(batch, embeddings):
                points.append({
                    "id": point_id,
                    "vector": embedding,
                    "payload": {
                        "text": text,
                        "category": category,
                        "language": "ru"  # TODO: detect language
                    }
                })
                point_id += 1
            
            # Upsert to Qdrant
            result = upsert_points(points)
            total_loaded += len(points)
            print(f"  Loaded {len(points)} points, total: {total_loaded}")
    
    print(f"\nDone! Total points loaded: {total_loaded}")

if __name__ == "__main__":
    main()
