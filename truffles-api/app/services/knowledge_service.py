import os
import time
from typing import List

import httpx

from app.logging_config import get_logger, record_bge_time
from app.services.alert_service import alert_warning

logger = get_logger("knowledge_service")


def _log_timing(
    stage: str,
    elapsed_ms: float,
    *,
    timing_context: dict | None = None,
    extra: dict | None = None,
) -> None:
    context: dict = {}
    if isinstance(timing_context, dict):
        context.update(timing_context)
    if extra:
        context.update(extra)
    context["stage"] = stage
    context["elapsed_ms"] = round(elapsed_ms, 2)
    for key in ("message_id", "outbox_id", "trace_id"):
        context.setdefault(key, None)
    if isinstance(timing_context, dict):
        timing = timing_context.get("timing")
        if not isinstance(timing, dict):
            timing = {}
        stages = timing.get("stages")
        if not isinstance(stages, dict):
            stages = {}
        stages[stage] = context["elapsed_ms"]
        timing["stages"] = stages
        timing_context["timing"] = timing
    logger.info("Timing", extra={"context": context})

QDRANT_HOST = os.environ.get("QDRANT_HOST", "http://qdrant:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
TEST_MODE = os.environ.get("TEST_MODE", "").strip().lower() in {"1", "true", "yes", "on"}
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION")
if not QDRANT_COLLECTION:
    QDRANT_COLLECTION = "truffles_knowledge_ci" if TEST_MODE else "truffles_knowledge"
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
        filter_meta.update({"filter_mode": "branch", "filter_reason": "branch_missing"})
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
    search_start = time.monotonic()

    def _log_search(extra: dict | None = None) -> None:
        _log_timing(
            "knowledge_search_ms",
            (time.monotonic() - search_start) * 1000,
            timing_context=trace_context,
            extra=extra,
        )

    # Enforce strict branch isolation: skip RAG if branch filter is missing.
    headers = {"api-key": QDRANT_API_KEY} if QDRANT_API_KEY else None
    filter_payload, filter_meta = _build_qdrant_filter(
        client_slug=client_slug,
        branch_id=branch_id,
        knowledge_tag=knowledge_tag,
    )
    _set_rag_filter_trace(trace_context, filter_meta)
    if filter_meta.get("filter_reason") == "branch_missing":
        logger.info(f"Knowledge search skipped (branch missing) for '{query[:30]}...'")
        _log_search({"reason": "branch_missing"})
        return []

    # Get embedding for query
    embedding = get_embedding(query, client_slug=client_slug)

    # Search in Qdrant
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
            _log_search({"status_code": response.status_code, "reason": "qdrant_error"})
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
            _log_search({"results": len(results)})
            return results

        filter_meta.update({"filter_reason": "branch_filter_empty"})
        _set_rag_filter_trace(trace_context, filter_meta)
        logger.info(f"Knowledge search: found 0 results for '{query[:30]}...' (strict branch)")
        _log_search({"results": len(results), "reason": "branch_filter_empty"})
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
