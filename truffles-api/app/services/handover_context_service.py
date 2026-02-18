from __future__ import annotations

from datetime import datetime
from typing import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Message

HANDOVER_CONTEXT_LOOKBACK_LIMIT = 10
HANDOVER_CONTEXT_MESSAGE_MAX_CHARS = 280
HANDOVER_CONTEXT_SUMMARY_MAX_CHARS = 1600

ROLE_LABELS = {
    "user": "client",
    "assistant": "assistant",
    "manager": "manager",
    "system": "system",
}


def _trim_text(value: object, *, max_chars: int = HANDOVER_CONTEXT_MESSAGE_MAX_CHARS) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return None
    if len(cleaned) <= max_chars:
        return cleaned
    return f"{cleaned[: max_chars - 1].rstrip()}…"


def _normalize_role(value: object) -> str:
    if not isinstance(value, str):
        return "unknown"
    normalized = value.strip().lower()
    return normalized or "unknown"


def get_recent_conversation_messages(
    db: Session,
    conversation_id: UUID,
    *,
    limit: int = HANDOVER_CONTEXT_LOOKBACK_LIMIT,
) -> list[Message]:
    safe_limit = max(1, int(limit or HANDOVER_CONTEXT_LOOKBACK_LIMIT))
    try:
        rows = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(safe_limit)
            .all()
        )
    except Exception:
        return []
    if isinstance(rows, tuple):
        rows = list(rows)
    if not isinstance(rows, list):
        return []
    rows = [item for item in rows if item is not None]
    rows.sort(key=lambda item: getattr(item, "created_at", datetime.min))
    return rows


def build_handover_messages(messages: Iterable[Message] | None) -> list[dict]:
    payload: list[dict] = []
    for message in messages or []:
        role = _normalize_role(getattr(message, "role", None))
        content = _trim_text(getattr(message, "content", None))
        if not content:
            continue

        item: dict[str, object] = {
            "role": role,
            "content": content,
        }
        created_at = getattr(message, "created_at", None)
        if isinstance(created_at, datetime):
            item["created_at"] = created_at.isoformat()
        message_id = _trim_text(getattr(message, "message_id", None), max_chars=96)
        if message_id:
            item["message_id"] = message_id
        metadata = getattr(message, "message_metadata", None)
        if isinstance(metadata, dict):
            media = metadata.get("media")
            if isinstance(media, dict):
                item["has_media"] = True
                media_type = _trim_text(media.get("media_type") or media.get("type"), max_chars=32)
                if media_type:
                    item["media_type"] = media_type
        payload.append(item)
    return payload


def build_handover_context_summary(
    messages: Iterable[dict] | None,
    *,
    fallback: str | None = None,
    max_chars: int = HANDOVER_CONTEXT_SUMMARY_MAX_CHARS,
) -> str | None:
    lines: list[str] = []
    for item in messages or []:
        if not isinstance(item, dict):
            continue
        role = _normalize_role(item.get("role"))
        content = _trim_text(item.get("content"), max_chars=HANDOVER_CONTEXT_MESSAGE_MAX_CHARS)
        if not content:
            continue
        label = ROLE_LABELS.get(role, role)
        lines.append(f"{label}: {content}")
    if not lines:
        return _trim_text(fallback, max_chars=max_chars)
    summary = "\n".join(lines)
    if len(summary) <= max_chars:
        return summary
    return f"{summary[: max_chars - 1].rstrip()}…"
