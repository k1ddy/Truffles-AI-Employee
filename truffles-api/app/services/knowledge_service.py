import os
import time
from typing import List

import httpx

from app.logging_config import get_logger, record_bge_time
from app.services.alert_service import alert_warning

logger = get_logger("knowledge_service")

QDRANT_HOST = os.environ.get("QDRANT_HOST", "http://qdrant:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
QDRANT_COLLECTION = "truffles_knowledge"
BGE_M3_URL = os.environ.get("BGE_M3_URL", "http://bge-m3:80/embed")


def get_embedding(text: str, *, client_slug: str | None = None) -> List[float]:
    """Get embedding from BGE-M3 service."""
    start = time.monotonic()
    with httpx.Client(timeout=30.0) as client:
        response = client.post(BGE_M3_URL, json={"inputs": text})
        if response.status_code != 200:
            record_bge_time(client_slug, (time.monotonic() - start) * 1000)
            raise Exception(f"BGE-M3 error: {response.status_code} - {response.text}")

        data = response.json()
        # Handle different response formats
        if isinstance(data, list) and len(data) > 0:
            embedding = data[0] if isinstance(data[0], list) else data
        else:
            embedding = data.get("embedding") or data.get("embeddings") or data
        record_bge_time(client_slug, (time.monotonic() - start) * 1000)
        return embedding


def _build_qdrant_filter(
    *,
    client_slug: str,
    branch_id: str | None,
    knowledge_tag: str | None,
) -> tuple[dict, dict]:
    filter_payload = {"must": [{"key": "metadata.client_slug", "match": {"value": client_slug}}]}
    filter_meta = {
        "client_slug": client_slug,
        "branch_id": branch_id,
        "knowledge_tag": knowledge_tag,
    }
    if knowledge_tag:
        filter_payload["must"].append(
            {"key": "metadata.knowledge_tag", "match": {"value": knowledge_tag}}
        )
        filter_meta.update({"filter_mode": "branch", "filter_reason": "knowledge_tag"})
    elif branch_id:
        filter_payload["must"].append(
            {"key": "metadata.branch_id", "match": {"value": branch_id}}
        )
        filter_meta.update({"filter_mode": "branch", "filter_reason": "branch_id"})
    else:
        filter_meta.update({"filter_mode": "client", "filter_reason": "branch_missing"})
    return filter_payload, filter_meta


def _set_rag_filter_trace(trace_context: dict | None, filter_meta: dict) -> None:
    if isinstance(trace_context, dict):
        trace_context["rag_filter"] = dict(filter_meta)


def search_knowledge(
    query: str,
    client_slug: str,
    limit: int = 5,
    score_threshold: float = 0.45,
    *,
    branch_id: str | None = None,
    knowledge_tag: str | None = None,
    trace_context: dict | None = None,
) -> List[dict]:
    """Search knowledge base in Qdrant."""

    # Get embedding for query
    embedding = get_embedding(query, client_slug=client_slug)

    # Search in Qdrant
    headers = {"api-key": QDRANT_API_KEY} if QDRANT_API_KEY else None
    filter_payload, filter_meta = _build_qdrant_filter(
        client_slug=client_slug,
        branch_id=branch_id,
        knowledge_tag=knowledge_tag,
    )
    _set_rag_filter_trace(trace_context, filter_meta)
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{QDRANT_HOST}/collections/{QDRANT_COLLECTION}/points/search",
            headers=headers,
            json={
                "vector": embedding,
                "limit": limit,
                "score_threshold": score_threshold,
                "filter": filter_payload,
                "with_payload": True,
            },
        )

        if response.status_code != 200:
            logger.error(f"Qdrant search error: {response.status_code} - {response.text}")
            alert_warning("Qdrant search failed", {"status": response.status_code, "query": query[:50]})
            return []

        data = response.json()
        results = []

        for point in data.get("result", []):
            payload = point.get("payload", {})
            results.append(
                {
                    "score": point.get("score"),
                    "text": payload.get("content"),  # content field in Qdrant
                    "source": payload.get("metadata", {}).get("doc_name"),
                    "metadata": payload.get("metadata", {}),
                }
            )

        if results or filter_meta.get("filter_mode") != "branch":
            logger.info(f"Knowledge search: found {len(results)} results for '{query[:30]}...'")
            return results

        fallback_payload, fallback_meta = _build_qdrant_filter(
            client_slug=client_slug,
            branch_id=None,
            knowledge_tag=None,
        )
        fallback_meta.update({"filter_mode": "client_fallback", "filter_reason": "branch_filter_empty"})
        _set_rag_filter_trace(trace_context, fallback_meta)
        response = client.post(
            f"{QDRANT_HOST}/collections/{QDRANT_COLLECTION}/points/search",
            headers=headers,
            json={
                "vector": embedding,
                "limit": limit,
                "score_threshold": score_threshold,
                "filter": fallback_payload,
                "with_payload": True,
            },
        )
        if response.status_code != 200:
            logger.error(f"Qdrant search error: {response.status_code} - {response.text}")
            alert_warning("Qdrant search failed", {"status": response.status_code, "query": query[:50]})
            return []
        data = response.json()
        results = []
        for point in data.get("result", []):
            payload = point.get("payload", {})
            results.append(
                {
                    "score": point.get("score"),
                    "text": payload.get("content"),
                    "source": payload.get("metadata", {}).get("doc_name"),
                    "metadata": payload.get("metadata", {}),
                }
            )
        logger.info(f"Knowledge search: found {len(results)} results for '{query[:30]}...' (fallback)")
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
