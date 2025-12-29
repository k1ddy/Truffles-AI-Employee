import math
import os
import re
import time
from enum import Enum
from typing import Any, Iterable, Tuple

import httpx

from app.logging_config import get_logger
from app.services.ai_service import (
    FAST_MODEL,
    INTENT_TIMEOUT_SECONDS,
    get_llm_provider,
    normalize_for_matching,
)

logger = get_logger("intent_service")

QDRANT_HOST = os.environ.get("QDRANT_HOST", "http://qdrant:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "truffles_knowledge")

RAG_BM25_LIMIT = int(os.environ.get("RAG_BM25_LIMIT", "5"))
RAG_BM25_MAX_DOCS = int(os.environ.get("RAG_BM25_MAX_DOCS", "200"))
RAG_BM25_TIMEOUT_SECONDS = float(os.environ.get("RAG_BM25_TIMEOUT_SECONDS", "0.8"))
RAG_HYBRID_VECTOR_WEIGHT = float(os.environ.get("RAG_HYBRID_VECTOR_WEIGHT", "0.6"))
RAG_HYBRID_BM25_WEIGHT = float(os.environ.get("RAG_HYBRID_BM25_WEIGHT", "0.4"))


def _is_env_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


class Intent(str, Enum):
    HUMAN_REQUEST = "human_request"  # Клиент просит менеджера/человека
    FRUSTRATION = "frustration"  # Клиент раздражён, ругается
    REJECTION = "rejection"  # Клиент отказывается от помощи бота ("нет", "не надо")
    QUESTION = "question"  # Вопрос о продукте/услуге
    GREETING = "greeting"  # Приветствие
    THANKS = "thanks"  # Благодарность
    OUT_OF_DOMAIN = "out_of_domain"  # Вопрос не по теме
    OTHER = "other"  # Всё остальное


class DomainIntent(str, Enum):
    IN_DOMAIN = "in_domain"
    OUT_OF_DOMAIN = "out_of_domain"
    UNKNOWN = "unknown"


ESCALATION_INTENTS = {Intent.HUMAN_REQUEST, Intent.FRUSTRATION}
REJECTION_INTENTS = {Intent.REJECTION}

CLASSIFY_PROMPT = """Классифицируй сообщение клиента. Верни ТОЛЬКО одно слово из списка:
- human_request — клиент просит человека/менеджера/оператора
- frustration — клиент раздражён, ругается, использует мат
- rejection — клиент отказывается от помощи бота (нет, не надо, не нужно, сам разберусь)
- question — вопрос о продукте, услуге, цене, доставке
- greeting — приветствие (привет, здравствуйте, добрый день)
- thanks — благодарность (спасибо, благодарю)
- out_of_domain — сообщение не по теме (погода, рецепты, программирование)
- other — всё остальное

Примеры:
"Позови менеджера" → human_request
"Хочу поговорить с человеком" → human_request
"Да блять, сколько можно ждать!" → frustration
"Нет" → rejection
"Не надо" → rejection
"Нет, подожду менеджера" → rejection
"Какая цена?" → question
"Привет!" → greeting
"Спасибо за помощь" → thanks
"Какая погода в Алматы?" → out_of_domain

Сообщение: {message}

Ответ (одно слово):"""

HUMAN_REQUEST_PATTERNS = (
    re.compile(
        r"\b(менеджер\w*|оператор\w*|админ\w*|администратор\w*|человек\w*|консультант\w*|поддержк\w*|саппорт\w*|жив(ой|ым|ому|ого|ые|ых|ую)\w*)\b"
    ),
    re.compile(r"\b(позов|позв|соедин|переключ)\w*\b"),
)

OPT_OUT_EXACT = {
    "стоп",
    "stop",
    "unsubscribe",
    "отпишись",
    "отписаться",
    "mute",
    "не пиши",
    "не пишите",
    "заткнись",
    "заткнитесь",
}

OPT_OUT_SUBSTRINGS = [
    "не хочу чтобы ты писал",
    "не хочу чтобы вы писали",
    "не хочу чтобы ты писала",
    "не хочу чтобы вы писали",
    "не пиши мне",
    "не пишите мне",
    "хватит писать",
    "перестань писать",
    "перестаньте писать",
    "больше не пиши",
    "больше не пишите",
    "не надо писать",
    "не нужно писать",
    "удали меня",
    "заткнис",
]

FRUSTRATION_PATTERNS = (
    re.compile(r"\bзаткни(сь)?\b"),
    re.compile(r"\bотъ?еб\w*\b"),
    re.compile(r"\bза[её]б\w*\b"),
    re.compile(r"\bнахуй\b"),
    re.compile(r"\bиди нах\w*\b"),
    re.compile(r"\bпош[её]л нах\w*\b"),
    re.compile(r"\bотвали\b"),
    re.compile(r"\bебан\w*\b"),
)


def is_human_request_message(message: str) -> bool:
    normalized = normalize_for_matching(message)
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in HUMAN_REQUEST_PATTERNS)


def is_opt_out_message(message: str) -> bool:
    normalized = normalize_for_matching(message)
    if not normalized:
        return False
    if normalized in OPT_OUT_EXACT:
        return True
    return any(phrase in normalized for phrase in OPT_OUT_SUBSTRINGS)


def is_frustration_message(message: str) -> bool:
    normalized = normalize_for_matching(message)
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in FRUSTRATION_PATTERNS)


def classify_intent(message: str) -> Intent:
    """Classify user message intent using LLM."""
    try:
        if is_opt_out_message(message):
            return Intent.REJECTION

        if is_frustration_message(message):
            return Intent.FRUSTRATION

        if is_human_request_message(message):
            return Intent.HUMAN_REQUEST

        llm = get_llm_provider()

        prompt = CLASSIFY_PROMPT.format(message=message)
        messages = [{"role": "user", "content": prompt}]

        llm_start = time.monotonic()
        try:
            response = llm.generate(
                messages,
                temperature=1.0,
                max_tokens=100,
                model=FAST_MODEL,
                timeout_seconds=INTENT_TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException as exc:
            logger.info(
                "Timing",
                extra={
                    "context": {
                        "stage": "intent_llm_ms",
                        "elapsed_ms": round((time.monotonic() - llm_start) * 1000, 2),
                        "model_name": FAST_MODEL,
                        "model_tier": "fast",
                        "timeout": True,
                        "timeout_seconds": INTENT_TIMEOUT_SECONDS,
                    }
                },
            )
            logger.warning(f"Intent LLM timeout after {INTENT_TIMEOUT_SECONDS}s: {exc}")
            return Intent.OTHER

        logger.info(
            "Timing",
            extra={
                "context": {
                    "stage": "intent_llm_ms",
                    "elapsed_ms": round((time.monotonic() - llm_start) * 1000, 2),
                    "model_name": FAST_MODEL,
                    "model_tier": "fast",
                    "timeout": False,
                }
            },
        )
        result = response.content.strip().lower()

        # Parse response
        for intent in Intent:
            if intent.value in result:
                return intent

        return Intent.OTHER

    except Exception as e:
        logger.error(f"Intent classification error: {e}")
        return Intent.OTHER


def should_escalate(intent: Intent) -> bool:
    """Check if intent requires escalation to human."""
    return intent in ESCALATION_INTENTS


def is_rejection(intent: Intent) -> bool:
    """Check if client is rejecting bot's help."""
    return intent in REJECTION_INTENTS


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    normalized = text.strip().casefold()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _ensure_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if isinstance(value, tuple):
        return [str(v) for v in value if v]
    if isinstance(value, str):
        return [value]
    return []


def _get_domain_router_config(client_config: dict | None) -> dict:
    if not isinstance(client_config, dict):
        return {}
    nested = client_config.get("domain_router")
    if isinstance(nested, dict):
        return nested
    if any(
        key in client_config
        for key in (
            "anchors_in",
            "anchors_out",
            "anchors_in_strict",
            "strict_in_anchors",
            "in_threshold",
            "out_threshold",
            "in_hit_threshold",
            "out_hit_threshold",
            "strict_in_hit_threshold",
        )
    ):
        return client_config
    return {}


def _score_against_anchors(
    text_normalized: str,
    tokens: set[str],
    anchors: Iterable[str],
    hit_threshold: float,
) -> tuple[float, str | None, int]:
    best_score = 0.0
    best_anchor = None
    hits = 0
    for anchor in anchors:
        anchor_normalized = _normalize_text(anchor)
        if not anchor_normalized:
            continue
        if anchor_normalized in text_normalized:
            score = 0.95
        else:
            anchor_tokens = set(anchor_normalized.split())
            if not anchor_tokens:
                continue
            score = len(tokens & anchor_tokens) / max(len(anchor_tokens), 1)
        if score > best_score:
            best_score = score
            best_anchor = anchor
        if score >= hit_threshold:
            hits += 1
    return best_score, best_anchor, hits


def classify_domain_with_scores(
    text: str,
    client_config: dict | None,
) -> Tuple[DomainIntent, float, float, dict]:
    """
    Classify message domain using per-client anchors (no network calls).
    Returns (domain_intent, in_score, out_score, meta).
    """
    config = _get_domain_router_config(client_config)
    anchors_in = _ensure_list(config.get("anchors_in"))
    anchors_out = _ensure_list(config.get("anchors_out"))
    strict_in_anchors = _ensure_list(config.get("anchors_in_strict") or config.get("strict_in_anchors"))
    in_threshold = float(config.get("in_threshold", 0.62))
    out_threshold = float(config.get("out_threshold", 0.62))
    margin = float(config.get("margin", 0.08))
    min_len = int(config.get("min_len", 5))
    in_hit_threshold = float(config.get("in_hit_threshold", in_threshold))
    out_hit_threshold = float(config.get("out_hit_threshold", out_threshold))
    strict_in_hit_threshold = float(config.get("strict_in_hit_threshold", in_threshold))

    text_normalized = _normalize_text(text)
    tokens = set(text_normalized.split()) if text_normalized else set()

    if not anchors_in and not anchors_out and not strict_in_anchors:
        return (
            DomainIntent.UNKNOWN,
            0.0,
            0.0,
            {
                "in_threshold": in_threshold,
                "out_threshold": out_threshold,
                "margin": margin,
                "in_hit_threshold": in_hit_threshold,
                "out_hit_threshold": out_hit_threshold,
                "strict_in_hit_threshold": strict_in_hit_threshold,
                "anchors_in": len(anchors_in),
                "anchors_out": len(anchors_out),
                "strict_in_anchors": len(strict_in_anchors),
                "in_hits": 0,
                "out_hits": 0,
                "strict_in_hits": 0,
                "message_len": len(text_normalized),
            },
        )

    in_score, matched_in, in_hits = _score_against_anchors(
        text_normalized, tokens, anchors_in, in_hit_threshold
    )
    out_score, matched_out, out_hits = _score_against_anchors(
        text_normalized, tokens, anchors_out, out_hit_threshold
    )
    _, matched_strict_in, strict_in_hits = _score_against_anchors(
        text_normalized, tokens, strict_in_anchors, strict_in_hit_threshold
    )

    domain_intent = DomainIntent.UNKNOWN
    if len(text_normalized) >= min_len:
        if in_score >= in_threshold and in_score >= out_score + margin:
            domain_intent = DomainIntent.IN_DOMAIN
        elif out_score >= out_threshold and out_score >= in_score + margin:
            domain_intent = DomainIntent.OUT_OF_DOMAIN

    meta = {
        "in_threshold": in_threshold,
        "out_threshold": out_threshold,
        "margin": margin,
        "in_hit_threshold": in_hit_threshold,
        "out_hit_threshold": out_hit_threshold,
        "strict_in_hit_threshold": strict_in_hit_threshold,
        "anchors_in": len(anchors_in),
        "anchors_out": len(anchors_out),
        "strict_in_anchors": len(strict_in_anchors),
        "matched_in": matched_in,
        "matched_out": matched_out,
        "matched_strict_in": matched_strict_in,
        "in_hits": in_hits,
        "out_hits": out_hits,
        "strict_in_hits": strict_in_hits,
        "message_len": len(text_normalized),
    }
    return domain_intent, in_score, out_score, meta


def is_strong_out_of_domain(
    text: str,
    domain_intent: DomainIntent,
    in_score: float,
    out_score: float,
    client_config: dict | None,
) -> tuple[bool, dict]:
    """
    Conservative strong out-of-domain gate.
    Uses stricter thresholds and minimum length to avoid false positives.
    """
    config = _get_domain_router_config(client_config)
    out_threshold = float(config.get("out_threshold", 0.62))
    in_threshold = float(config.get("in_threshold", 0.62))
    anchors_out = _ensure_list(config.get("anchors_out"))
    strict_in_anchors = _ensure_list(config.get("anchors_in_strict") or config.get("strict_in_anchors"))
    out_hit_threshold = float(config.get("out_hit_threshold", out_threshold))
    strict_in_hit_threshold = float(config.get("strict_in_hit_threshold", in_threshold))

    strict_out_threshold = float(config.get("strict_out_threshold", max(out_threshold, 0.8)))
    strong_out_threshold = float(config.get("strong_out_threshold", max(out_threshold, 0.72)))
    strict_margin = float(config.get("strict_margin", 0.18))
    strong_margin = float(config.get("strong_margin", 0.12))
    strict_in_max = float(config.get("strict_in_max", 0.4))
    strong_in_max = float(config.get("strong_in_max", 0.5))
    strict_min_len = int(config.get("strict_min_len", 6))

    text_normalized = _normalize_text(text)
    tokens = set(text_normalized.split()) if text_normalized else set()
    message_len = len(text_normalized)

    _, matched_out, out_hits = _score_against_anchors(text_normalized, tokens, anchors_out, out_hit_threshold)
    _, matched_strict_in, strict_in_hits = _score_against_anchors(
        text_normalized, tokens, strict_in_anchors, strict_in_hit_threshold
    )

    strong = False
    if out_hits > 0 and strict_in_hits == 0:
        strong = True
    elif domain_intent == DomainIntent.OUT_OF_DOMAIN:
        if (
            message_len >= strict_min_len
            and out_score >= strict_out_threshold
            and out_score >= in_score + strict_margin
            and in_score <= strict_in_max
        ):
            strong = True
        elif (
            out_score >= strong_out_threshold
            and out_score >= in_score + strong_margin
            and in_score <= strong_in_max
        ):
            strong = True

    meta = {
        "strict_out_threshold": strict_out_threshold,
        "strong_out_threshold": strong_out_threshold,
        "strict_margin": strict_margin,
        "strong_margin": strong_margin,
        "strict_in_max": strict_in_max,
        "strong_in_max": strong_in_max,
        "strict_min_len": strict_min_len,
        "message_len": message_len,
        "out_hit_threshold": out_hit_threshold,
        "strict_in_hit_threshold": strict_in_hit_threshold,
        "out_hits": out_hits,
        "strict_in_hits": strict_in_hits,
        "matched_out": matched_out,
        "matched_strict_in": matched_strict_in,
    }
    return strong, meta


def _tokenize_for_bm25(text: str) -> list[str]:
    if not text:
        return []
    tokens = re.findall(r"[\w]+", text.casefold())
    return [token for token in tokens if len(token) > 1]


def _fetch_bm25_corpus(client_slug: str, *, max_docs: int) -> list[dict]:
    if not client_slug or max_docs <= 0:
        return []
    headers = {"api-key": QDRANT_API_KEY} if QDRANT_API_KEY else None
    points: list[dict] = []
    offset = None
    limit = min(100, max_docs)
    with httpx.Client(timeout=RAG_BM25_TIMEOUT_SECONDS) as client:
        while len(points) < max_docs:
            payload = {
                "limit": limit,
                "with_payload": True,
                "with_vectors": False,
                "filter": {"must": [{"key": "metadata.client_slug", "match": {"value": client_slug}}]},
            }
            if offset is not None:
                payload["offset"] = offset
            response = client.post(
                f"{QDRANT_HOST}/collections/{QDRANT_COLLECTION}/points/scroll",
                headers=headers,
                json=payload,
            )
            if response.status_code != 200:
                logger.warning(
                    "BM25 scroll failed",
                    extra={"context": {"status": response.status_code, "client_slug": client_slug}},
                )
                break
            data = response.json().get("result") or {}
            batch = data.get("points") or []
            points.extend(batch)
            offset = data.get("next_page_offset")
            if not offset or not batch:
                break
            limit = min(100, max_docs - len(points))
    return points[:max_docs]


def _bm25_search(query: str, client_slug: str) -> list[dict]:
    query_tokens = _tokenize_for_bm25(query)
    if not query_tokens:
        return []
    try:
        corpus = _fetch_bm25_corpus(client_slug, max_docs=RAG_BM25_MAX_DOCS)
    except Exception as exc:
        logger.warning(f"BM25 corpus fetch failed: {exc}")
        return []
    if not corpus:
        return []

    doc_tokens: list[list[str]] = []
    doc_meta: list[dict] = []
    for point in corpus:
        payload = point.get("payload") or {}
        text = payload.get("content") or ""
        tokens = _tokenize_for_bm25(text)
        if not tokens:
            continue
        doc_tokens.append(tokens)
        doc_meta.append(
            {
                "id": point.get("id"),
                "text": text,
                "source": payload.get("metadata", {}).get("doc_name"),
                "metadata": payload.get("metadata", {}),
            }
        )

    if not doc_tokens:
        return []

    doc_count = len(doc_tokens)
    avg_len = sum(len(tokens) for tokens in doc_tokens) / max(doc_count, 1)
    df: dict[str, int] = {}
    for tokens in doc_tokens:
        for token in set(tokens):
            df[token] = df.get(token, 0) + 1

    k1 = 1.5
    b = 0.75
    scores: list[tuple[int, float]] = []
    for idx, tokens in enumerate(doc_tokens):
        dl = len(tokens)
        tf: dict[str, int] = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1
        score = 0.0
        for term in query_tokens:
            term_df = df.get(term, 0)
            if term_df == 0:
                continue
            idf = math.log((doc_count - term_df + 0.5) / (term_df + 0.5) + 1)
            freq = tf.get(term, 0)
            if freq == 0:
                continue
            denom = freq + k1 * (1 - b + b * (dl / max(avg_len, 1)))
            score += idf * ((freq * (k1 + 1)) / max(denom, 1e-9))
        if score > 0:
            scores.append((idx, score))

    if not scores:
        return []
    scores.sort(key=lambda item: item[1], reverse=True)
    top = scores[: max(RAG_BM25_LIMIT, 1)]
    results: list[dict] = []
    for idx, score in top:
        meta = dict(doc_meta[idx])
        meta["bm25_score"] = score
        results.append(meta)
    return results


def hybrid_retrieve_knowledge(
    *,
    query: str,
    client_slug: str,
    vector_results: list[dict],
    limit: int = 5,
) -> tuple[list[dict], dict]:
    bm25_enabled = _is_env_enabled(os.environ.get("RAG_BM25_ENABLED"), default=True)
    if not QDRANT_API_KEY or os.environ.get("PYTEST_CURRENT_TEST"):
        bm25_enabled = False
    bm25_results: list[dict] = []
    if bm25_enabled:
        try:
            bm25_results = _bm25_search(query, client_slug)
        except Exception as exc:
            logger.warning(f"BM25 search failed: {exc}")

    by_key: dict[tuple[str | None, str | None], dict] = {}
    vector_max = 0.0
    for item in vector_results or []:
        text = item.get("text")
        source = item.get("source")
        key = (source, text)
        vector_score = float(item.get("score") or 0.0)
        vector_max = max(vector_max, vector_score)
        merged = dict(item)
        merged["vector_score"] = vector_score
        merged["bm25_score"] = 0.0
        by_key[key] = merged

    bm25_max = 0.0
    for item in bm25_results:
        text = item.get("text")
        source = item.get("source")
        key = (source, text)
        bm25_score = float(item.get("bm25_score") or 0.0)
        bm25_max = max(bm25_max, bm25_score)
        if key in by_key:
            by_key[key]["bm25_score"] = bm25_score
            continue
        merged = dict(item)
        merged.setdefault("metadata", {})
        merged["vector_score"] = 0.0
        merged["bm25_score"] = bm25_score
        by_key[key] = merged

    vector_weight = max(RAG_HYBRID_VECTOR_WEIGHT, 0.0)
    bm25_weight = max(RAG_HYBRID_BM25_WEIGHT, 0.0)
    if vector_weight + bm25_weight <= 0:
        vector_weight = 0.6
        bm25_weight = 0.4

    for item in by_key.values():
        vector_score = item.get("vector_score", 0.0)
        vector_norm = vector_score / vector_max if vector_max > 0 else 0.0
        bm25_norm = item.get("bm25_score", 0.0) / bm25_max if bm25_max > 0 else 0.0
        item["hybrid_score"] = (vector_weight * vector_norm) + (bm25_weight * bm25_norm)
        item["score"] = max(vector_score, bm25_norm)

    merged_results = sorted(
        by_key.values(),
        key=lambda item: item.get("hybrid_score", 0.0),
        reverse=True,
    )
    merged_results = merged_results[: max(limit, 1)]

    bm25_max_norm = 1.0 if bm25_max > 0 else 0.0
    rag_scores = {
        "vector_max": vector_max,
        "bm25_max": bm25_max,
        "bm25_max_norm": bm25_max_norm,
        "hybrid_max": merged_results[0]["hybrid_score"] if merged_results else 0.0,
        "vector_count": len(vector_results or []),
        "bm25_count": len(bm25_results),
        "vector_weight": vector_weight,
        "bm25_weight": bm25_weight,
        "bm25_enabled": bm25_enabled,
    }
    return merged_results, rag_scores
