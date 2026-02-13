import hashlib
import math
import os
import re
import time
from typing import Callable, List

import httpx

from app.logging_config import get_logger, record_bge_time
from app.schemas.consult import ConsultTopic
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
BGE_M3_TIMEOUT_SECONDS = float(os.environ.get("BGE_M3_TIMEOUT_SECONDS", "5.0"))
BGE_M3_CONNECT_TIMEOUT_SECONDS = float(os.environ.get("BGE_M3_CONNECT_TIMEOUT_SECONDS", "1.5"))
BGE_M3_ERROR_BACKOFF_SECONDS = float(os.environ.get("BGE_M3_ERROR_BACKOFF_SECONDS", "60.0"))
_CONSULT_TOPIC_CACHE: dict[tuple[str, str], list[list[float]]] = {}
_BGE_M3_BACKOFF_UNTIL = 0.0
_BGE_M3_BACKOFF_REASON: str | None = None


def _consult_topic_digest(topics: list[ConsultTopic]) -> str:
    parts: list[str] = []
    for topic in topics:
        allowed = ",".join(topic.allowed_advice[:2])
        parts.append(f"{topic.id}|{topic.title}|{topic.summary}|{allowed}")
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest


def _build_consult_topic_text(topic: ConsultTopic) -> str:
    parts = [topic.title, topic.summary]
    parts.extend(topic.allowed_advice[:2])
    cleaned = [part.strip() for part in parts if isinstance(part, str) and part.strip()]
    return ". ".join(cleaned)


def _tokenize_consult_text(text: str) -> list[str]:
    cleaned = re.sub(r"[^\w\s]", " ", text.casefold())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return []
    return [token for token in cleaned.split() if len(token) >= 3]


def _fuzzy_token_match(token: str, candidate: str) -> bool:
    if token == candidate:
        return True
    if len(token) >= 4 and len(candidate) >= 4:
        if token[:4] == candidate[:4]:
            return True
        if token in candidate or candidate in token:
            return True
    return False


def _is_hair_damage_query(message_text: str) -> bool:
    cleaned = re.sub(r"[^\w\s]", " ", message_text.casefold())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned or "волос" not in cleaned:
        return False
    return any(
        token in cleaned
        for token in (
            "лома",
            "ломк",
            "поврежд",
            "сух",
            "сеч",
        )
    )


def _prioritize_topic(candidates: list[dict], topic_id: str) -> None:
    for idx, candidate in enumerate(candidates):
        if candidate.get("topic_id") == topic_id:
            if idx > 0:
                candidates.insert(0, candidates.pop(idx))
            return


def _fallback_consult_topic_candidates(
    message_text: str,
    topics: list[ConsultTopic],
    *,
    top_k: int,
    timing_context: dict | None,
    error: str | None = None,
    start_time: float | None = None,
) -> list[dict]:
    started = start_time or time.monotonic()
    message_tokens = _tokenize_consult_text(message_text)
    if len(message_tokens) < 2:
        _log_timing(
            "consult_topic_resolver_ms",
            (time.monotonic() - started) * 1000,
            timing_context=timing_context,
            extra={"candidates": 0, "fallback": "lexical", "reason": "too_short", "error": error},
        )
        return []
    candidates: list[dict] = []
    for topic in topics:
        topic_text = _build_consult_topic_text(topic)
        if not topic_text:
            continue
        topic_tokens = _tokenize_consult_text(topic_text)
        if not topic_tokens:
            continue
        matches = 0
        for token in message_tokens:
            if any(_fuzzy_token_match(token, topic_token) for topic_token in topic_tokens):
                matches += 1
        if matches <= 0:
            continue
        score = round(matches / min(len(message_tokens), 3), 4)
        candidates.append(
            {
                "topic_id": topic.id,
                "title": topic.title,
                "summary": topic.summary,
                "score": score,
                "source": "lexical",
            }
        )
    candidates.sort(key=lambda item: item["score"], reverse=True)
    top_candidates = candidates[: max(top_k, 1)]
    _log_timing(
        "consult_topic_resolver_ms",
        (time.monotonic() - started) * 1000,
        timing_context=timing_context,
        extra={"candidates": len(top_candidates), "fallback": "lexical", "error": error},
    )
    return top_candidates


def _cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    if not vector_a or not vector_b or len(vector_a) != len(vector_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))
    if norm_a <= 0 or norm_b <= 0:
        return 0.0
    return dot / (norm_a * norm_b)


def resolve_consult_topic_candidates(
    message_text: str,
    topics: list[ConsultTopic],
    *,
    client_slug: str | None,
    top_k: int = 5,
    embedding_fn: Callable[[str], List[float]] | None = None,
    timing_context: dict | None = None,
) -> list[dict]:
    if not message_text or not topics:
        return []
    start = time.monotonic()
    topic_texts = [_build_consult_topic_text(topic) for topic in topics]
    if not all(topic_texts):
        return []
    use_cache = embedding_fn is None
    embedder = embedding_fn or (lambda text: get_embedding(text, client_slug=client_slug))
    cache_key = None
    topic_vectors: list[list[float]] | None = None
    if use_cache:
        digest = _consult_topic_digest(topics)
        cache_key = (client_slug or "unknown", digest)
        topic_vectors = _CONSULT_TOPIC_CACHE.get(cache_key)
    try:
        if topic_vectors is None:
            topic_vectors = [embedder(text) for text in topic_texts]
            if use_cache and cache_key:
                _CONSULT_TOPIC_CACHE[cache_key] = topic_vectors
        query_vector = embedder(message_text)
    except Exception as exc:
        alert_warning(
            "Consult topic embedding failed",
            {"client_slug": client_slug, "error": str(exc)},
        )
        _log_timing(
            "consult_topic_resolver_ms",
            (time.monotonic() - start) * 1000,
            timing_context=timing_context,
            extra={"candidates": 0, "fallback": "none", "error": str(exc)},
        )
        return []
    candidates: list[dict] = []
    for topic, topic_vector in zip(topics, topic_vectors):
        score = _cosine_similarity(query_vector, topic_vector)
        candidates.append(
            {
                "topic_id": topic.id,
                "title": topic.title,
                "summary": topic.summary,
                "score": round(score, 4),
            }
        )
    candidates.sort(key=lambda item: item["score"], reverse=True)
    top_candidates = candidates[: max(top_k, 1)]
    if top_candidates:
        top_score = top_candidates[0].get("score")
        if isinstance(top_score, (int, float)) and top_score < 0.35:
            fallback_k = max(top_k, 5)
            lexical_candidates = _fallback_consult_topic_candidates(
                message_text,
                topics,
                top_k=fallback_k,
                timing_context=timing_context,
                error="low_embedding_score",
                start_time=start,
            )
            if lexical_candidates:
                if _is_hair_damage_query(message_text):
                    _prioritize_topic(lexical_candidates, "hair_damage")
                return lexical_candidates[: max(top_k, 1)]
    _log_timing(
        "consult_topic_resolver_ms",
        (time.monotonic() - start) * 1000,
        timing_context=timing_context,
        extra={"candidates": len(top_candidates)},
    )
    return top_candidates


def get_embedding(text: str, *, client_slug: str | None = None) -> List[float]:
    """Get embedding from BGE-M3 service."""
    global _BGE_M3_BACKOFF_UNTIL, _BGE_M3_BACKOFF_REASON

    start = time.monotonic()
    if _BGE_M3_BACKOFF_UNTIL > start:
        record_bge_time(client_slug, (time.monotonic() - start) * 1000)
        raise RuntimeError(
            f"BGE-M3 temporarily disabled (backoff active): {_BGE_M3_BACKOFF_REASON or 'unavailable'}"
        )
    timeout = httpx.Timeout(
        timeout=max(BGE_M3_TIMEOUT_SECONDS, 0.1),
        connect=max(min(BGE_M3_CONNECT_TIMEOUT_SECONDS, BGE_M3_TIMEOUT_SECONDS), 0.1),
    )
    try:
        with httpx.Client(timeout=timeout) as client:
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
            _BGE_M3_BACKOFF_UNTIL = 0.0
            _BGE_M3_BACKOFF_REASON = None
            record_bge_time(client_slug, (time.monotonic() - start) * 1000)
            return embedding
    except Exception as exc:
        reason = str(exc)
        lowered = reason.casefold()
        if any(
            marker in lowered
            for marker in (
                "temporary failure in name resolution",
                "name or service not known",
                "failed to resolve",
                "nodename nor servname provided",
                "connection refused",
                "connect timeout",
            )
        ):
            _BGE_M3_BACKOFF_UNTIL = start + max(BGE_M3_ERROR_BACKOFF_SECONDS, 1.0)
            _BGE_M3_BACKOFF_REASON = reason
        record_bge_time(client_slug, (time.monotonic() - start) * 1000)
        raise


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
