import httpx
from typing import List, Optional
from uuid import UUID


QDRANT_HOST = "http://qdrant:6333"
QDRANT_API_KEY = "Iddqd777!"
QDRANT_COLLECTION = "truffles_knowledge"
BGE_M3_URL = "http://bge-m3:80/embed"


def get_embedding(text: str) -> List[float]:
    """Get embedding from BGE-M3 service."""
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            BGE_M3_URL,
            json={"inputs": text}
        )
        if response.status_code != 200:
            raise Exception(f"BGE-M3 error: {response.status_code} - {response.text}")
        
        data = response.json()
        # Handle different response formats
        if isinstance(data, list) and len(data) > 0:
            return data[0] if isinstance(data[0], list) else data
        return data.get("embedding") or data.get("embeddings") or data


def search_knowledge(
    query: str,
    client_slug: str,
    limit: int = 5,
    score_threshold: float = 0.5,
) -> List[dict]:
    """Search knowledge base in Qdrant."""
    
    # Get embedding for query
    embedding = get_embedding(query)
    
    # Search in Qdrant
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{QDRANT_HOST}/collections/{QDRANT_COLLECTION}/points/search",
            headers={"api-key": QDRANT_API_KEY},
            json={
                "vector": embedding,
                "limit": limit,
                "score_threshold": score_threshold,
                "filter": {
                    "must": [
                        {"key": "metadata.client_slug", "match": {"value": client_slug}}
                    ]
                },
                "with_payload": True,
            }
        )
        
        if response.status_code != 200:
            print(f"Qdrant search error: {response.status_code} - {response.text}")
            return []
        
        data = response.json()
        results = []
        
        for point in data.get("result", []):
            payload = point.get("payload", {})
            results.append({
                "score": point.get("score"),
                "text": payload.get("content"),  # content field in Qdrant
                "source": payload.get("metadata", {}).get("doc_name"),
                "metadata": payload.get("metadata", {}),
            })
        
        print(f"Knowledge search: found {len(results)} results for '{query[:30]}...'")
        return results


def format_knowledge_context(results: List[dict]) -> str:
    """Format knowledge search results for LLM context."""
    if not results:
        return ""
    
    context_parts = ["Релевантная информация из базы знаний:"]
    for i, r in enumerate(results, 1):
        text = r.get("text", "")
        if text:
            context_parts.append(f"{i}. {text}")
    
    return "\n".join(context_parts)
