"""Narrow runtime owner for response-stage RAG and backlog helper behavior."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Message
from app.services.ai_service import MID_CONFIDENCE_THRESHOLD

_DEFAULT_RAG_SCORES = {"bm25_max": 0.0, "vector_max": 0.0, "hybrid_max": 0.0}
logger = get_logger("webhook")


def _merge_rag_scores(rag_scores: dict | None) -> dict:
    merged = dict(rag_scores) if isinstance(rag_scores, dict) else {}
    for key, value in _DEFAULT_RAG_SCORES.items():
        if not isinstance(merged.get(key), (int, float)):
            merged[key] = value
    return merged if merged else dict(_DEFAULT_RAG_SCORES)


def _derive_rag_status(
    *,
    rag_scores: dict,
    rag_best_score: float | None,
    rag_attempted: bool,
) -> tuple[bool, str | None]:
    if not rag_attempted:
        return False, "overridden_by_gate"
    best_score = float(rag_best_score or 0.0)
    if best_score >= MID_CONFIDENCE_THRESHOLD:
        return True, None
    vector_count = int(rag_scores.get("vector_count") or 0)
    bm25_count = int(rag_scores.get("bm25_count") or 0)
    if vector_count <= 0 and bm25_count <= 0:
        return False, "empty"
    return False, "low_score"


def _resolve_backlog_language(message: Message | None) -> str:
    if not message or not isinstance(message.message_metadata, dict):
        return "unknown"
    metadata = message.message_metadata
    for key in ("language", "lang", "locale"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    media_meta = metadata.get("media")
    if isinstance(media_meta, dict):
        transcript_language = media_meta.get("transcript_language")
        if isinstance(transcript_language, str) and transcript_language.strip():
            return transcript_language.strip().lower()
    return "unknown"


def _record_knowledge_backlog(
    db: Session,
    *,
    client_id: UUID,
    conversation_id: UUID,
    message: Message | None,
    user_text: str,
    miss_type: str,
) -> None:
    text_value = (user_text or "").strip()
    if not text_value:
        return
    language = _resolve_backlog_language(message)
    miss_value = (miss_type or "unknown").strip().lower()
    try:
        db.execute(
            text(
                """
                INSERT INTO knowledge_backlog (
                  id,
                  client_id,
                  conversation_id,
                  message_id,
                  user_text,
                  language,
                  miss_type,
                  repeat_count,
                  first_seen_at,
                  last_seen_at
                )
                VALUES (
                  gen_random_uuid(),
                  :client_id,
                  :conversation_id,
                  :message_id,
                  :user_text,
                  :language,
                  :miss_type,
                  1,
                  NOW(),
                  NOW()
                )
                ON CONFLICT (client_id, language, miss_type, user_text)
                DO UPDATE SET
                  repeat_count = knowledge_backlog.repeat_count + 1,
                  last_seen_at = EXCLUDED.last_seen_at,
                  conversation_id = EXCLUDED.conversation_id,
                  message_id = EXCLUDED.message_id
                """
            ),
            {
                "client_id": client_id,
                "conversation_id": conversation_id,
                "message_id": message.id if message else None,
                "user_text": text_value,
                "language": language,
                "miss_type": miss_value,
            },
        )
    except Exception:
        logger.warning(
            "Knowledge backlog upsert failed",
            extra={
                "context": {
                    "client_id": str(client_id),
                    "conversation_id": str(conversation_id),
                    "message_id": str(message.id) if message else None,
                    "miss_type": miss_type,
                }
            },
            exc_info=True,
        )


__all__ = [
    "_DEFAULT_RAG_SCORES",
    "_derive_rag_status",
    "_merge_rag_scores",
    "_record_knowledge_backlog",
    "_resolve_backlog_language",
]
