"""Debounce/buffer/dedup helpers for inbound webhook messages."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Message
from app.schemas.webhook import WebhookResponse
from app.services.state_machine import ConversationState

logger = get_logger("webhook")

# Optional Redis-based debounce for bursty WhatsApp messages.
try:
    import redis.asyncio as redis_async  # type: ignore
except Exception:  # pragma: no cover
    redis_async = None


_debounce_redis_client = None
_debounce_redis_url = None


@dataclass(frozen=True)
class DuplicateMessageProbe:
    duplicate: bool
    backend: str
    fallback_reason: str | None = None


def _is_env_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _get_debounce_settings() -> tuple[bool, float, int, str, float]:
    enabled = _is_env_enabled(os.environ.get("DEBOUNCE_ENABLED"), default=True)
    inactivity_seconds = float(os.environ.get("DEBOUNCE_INACTIVITY_SECONDS", "1.5"))
    ttl_seconds = int(float(os.environ.get("DEBOUNCE_TTL_SECONDS", "30")))
    redis_url = os.environ.get("REDIS_URL", "redis://truffles_redis_1:6379/0")
    socket_timeout_seconds = float(os.environ.get("DEBOUNCE_SOCKET_TIMEOUT_SECONDS", "0.3"))
    return enabled, inactivity_seconds, ttl_seconds, redis_url, socket_timeout_seconds


def _get_message_buffer_settings() -> tuple[bool, int]:
    enabled = _is_env_enabled(os.environ.get("DEBOUNCE_ENABLED"), default=True)
    max_messages = int(float(os.environ.get("DEBOUNCE_MAX_BUFFER_MESSAGES", "8")))
    return enabled, max_messages


def _get_dedup_settings() -> tuple[int, str, float]:
    ttl_seconds = int(float(os.environ.get("DEDUP_TTL_SECONDS", "86400")))
    redis_url = os.environ.get("REDIS_URL", "redis://truffles_redis_1:6379/0")
    socket_timeout_seconds = float(os.environ.get("DEDUP_SOCKET_TIMEOUT_SECONDS", "0.3"))
    return ttl_seconds, redis_url, socket_timeout_seconds


def _is_fast_dedup_bypass_enabled() -> bool:
    test_mode = _is_env_enabled(os.environ.get("TEST_MODE"), default=False)
    fast_dedup = _is_env_enabled(os.environ.get("LLM_QUALITY_FAST_DEDUP"), default=False)
    return bool(test_mode and fast_dedup)


def _get_debounce_redis(redis_url: str, socket_timeout_seconds: float):
    global _debounce_redis_client, _debounce_redis_url

    if redis_async is None:
        return None

    if _debounce_redis_client is None or _debounce_redis_url != redis_url:
        _debounce_redis_url = redis_url
        _debounce_redis_client = redis_async.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=socket_timeout_seconds,
            socket_timeout=socket_timeout_seconds,
        )

    return _debounce_redis_client


async def should_process_debounced_message(
    *,
    client_id: str,
    remote_jid: str,
    message_id: str | None,
    sleep_func=asyncio.sleep,
    redis_client=None,
) -> bool:
    """
    Debounce bursty user messages: only the latest message in a short window triggers AI/escalation.

    Strategy: store a per-user token in Redis and check after a short pause whether it's still the last one.
    If Redis is unavailable, falls back to current behavior (process immediately).
    """
    enabled, inactivity_seconds, ttl_seconds, redis_url, socket_timeout_seconds = _get_debounce_settings()
    if not enabled:
        return True

    token = message_id or uuid4().hex
    key = f"truffles:debounce:{client_id}:{remote_jid}"

    if redis_client is None:
        redis_client = _get_debounce_redis(redis_url, socket_timeout_seconds)
    if not redis_client:
        return True

    try:
        await redis_client.set(key, token, ex=ttl_seconds)
        await sleep_func(inactivity_seconds)
        last_token = await redis_client.get(key)
        return last_token == token
    except Exception as e:
        logger.warning(f"Debounce unavailable, proceeding without it: {e}")
        return True


async def _buffer_user_message(
    *,
    redis_client,
    client_id: str,
    remote_jid: str,
    message_text: str,
    ttl_seconds: int,
    max_messages: int,
) -> None:
    if not redis_client:
        return

    key = f"truffles:buffer:{client_id}:{remote_jid}"
    try:
        await redis_client.rpush(key, message_text)
        await redis_client.ltrim(key, -max_messages, -1)
        await redis_client.expire(key, ttl_seconds)
    except Exception as e:
        logger.warning(f"Message buffer unavailable: {e}")


async def _drain_buffered_messages(*, redis_client, client_id: str, remote_jid: str) -> list[str]:
    if not redis_client:
        return []

    key = f"truffles:buffer:{client_id}:{remote_jid}"
    try:
        messages = await redis_client.lrange(key, 0, -1)
        await redis_client.delete(key)
    except Exception as e:
        logger.warning(f"Message buffer drain failed: {e}")
        return []

    cleaned: list[str] = []
    for msg in messages or []:
        if not msg:
            continue
        text_value = msg.strip()
        if text_value:
            cleaned.append(text_value)
    return cleaned


def _merge_duplicate_fallback_reason(current: str | None, addition: str) -> str:
    if not current:
        return addition
    return f"{current}+{addition}"


def _lookup_duplicate_message_in_messages_table(
    db: Session,
    *,
    client_id,
    message_id: str,
) -> Message | None:
    return (
        db.query(Message)
        .filter(
            Message.client_id == client_id,
            Message.role == "user",
            or_(
                Message.message_metadata["message_id"].astext == message_id,
                Message.message_metadata["messageId"].astext == message_id,
            ),
        )
        .order_by(Message.created_at.desc())
        .first()
    )


def _lookup_preexisting_duplicate_message(
    db: Session,
    *,
    client_id,
    message_id: str | None,
) -> DuplicateMessageProbe:
    if _is_fast_dedup_bypass_enabled():
        return DuplicateMessageProbe(
            duplicate=False,
            backend="fast_test_bypass",
            fallback_reason="test_mode_fast_dedup",
        )
    if client_id is None or not message_id:
        return DuplicateMessageProbe(duplicate=False, backend="message_dedup")

    fallback_reason = None
    try:
        existing_dedup = db.execute(
            text(
                """
                SELECT 1
                FROM message_dedup
                WHERE client_id = :client_id AND message_id = :message_id
                LIMIT 1
                """
            ),
            {"client_id": client_id, "message_id": message_id},
        ).first()
        if existing_dedup is not None:
            return DuplicateMessageProbe(
                duplicate=True,
                backend="message_dedup",
            )
    except Exception as exc:
        fallback_reason = _merge_duplicate_fallback_reason(
            fallback_reason,
            "message_dedup_lookup_error",
        )
        logger.warning(
            "Dedup owner message_dedup lookup failed, falling back to messages table",
            extra={
                "context": {
                    "client_id": str(client_id),
                    "message_id": message_id,
                    "error": str(exc),
                }
            },
        )
        try:
            db.rollback()
        except Exception:
            pass

    try:
        duplicate = _lookup_duplicate_message_in_messages_table(
            db,
            client_id=client_id,
            message_id=message_id,
        )
    except Exception as exc:
        fallback_reason = _merge_duplicate_fallback_reason(
            fallback_reason,
            "messages_lookup_error",
        )
        logger.warning(
            "Dedup owner messages-table fallback lookup failed",
            extra={
                "context": {
                    "client_id": str(client_id),
                    "message_id": message_id,
                    "error": str(exc),
                }
            },
        )
        try:
            db.rollback()
        except Exception:
            pass
        return DuplicateMessageProbe(
            duplicate=False,
            backend="messages_table",
            fallback_reason=fallback_reason,
        )
    if duplicate is not None:
        return DuplicateMessageProbe(
            duplicate=True,
            backend="messages_table",
            fallback_reason=fallback_reason,
        )
    return DuplicateMessageProbe(
        duplicate=False,
        backend="message_dedup" if fallback_reason is None else "messages_table",
        fallback_reason=fallback_reason,
    )


async def is_duplicate_message_id(
    *,
    db: Session,
    client_id,
    message_id: str | None,
    redis_client=None,
    diagnostics: dict[str, Any] | None = None,
) -> bool:
    def _finalize_diagnostics(
        *,
        duplicate: bool,
        dedup_backend: str,
        dedup_fallback_reason: str | None,
        redis_latency_ms: float | None,
        db_latency_ms: float | None,
        messages_latency_ms: float | None,
        started_at: float,
    ) -> None:
        if not isinstance(diagnostics, dict):
            return
        diagnostics["dedup_backend"] = "redis" if dedup_backend == "redis" else "db_fallback"
        diagnostics["dedup_fallback_reason"] = dedup_fallback_reason
        diagnostics["dedup_duplicate"] = bool(duplicate)
        diagnostics["dedup_latency_ms"] = round((time.monotonic() - started_at) * 1000, 2)
        if isinstance(redis_latency_ms, (int, float)):
            diagnostics["dedup_redis_latency_ms"] = round(redis_latency_ms, 2)
        if isinstance(db_latency_ms, (int, float)):
            diagnostics["dedup_db_latency_ms"] = round(db_latency_ms, 2)
        if isinstance(messages_latency_ms, (int, float)):
            diagnostics["dedup_messages_latency_ms"] = round(messages_latency_ms, 2)

    if not message_id:
        _finalize_diagnostics(
            duplicate=False,
            dedup_backend="db_fallback",
            dedup_fallback_reason="message_id_missing",
            redis_latency_ms=None,
            db_latency_ms=None,
            messages_latency_ms=None,
            started_at=time.monotonic(),
        )
        return False

    started_at = time.monotonic()
    redis_latency_ms = None
    db_latency_ms = None
    messages_latency_ms = None
    dedup_backend = "db_fallback"
    dedup_fallback_reason = "redis_unavailable"

    ttl_seconds, redis_url, socket_timeout_seconds = _get_dedup_settings()
    key = f"truffles:dedup:{client_id}:{message_id}"

    if redis_client is None:
        redis_client = _get_debounce_redis(redis_url, socket_timeout_seconds)
    if redis_client:
        redis_started = time.monotonic()
        try:
            was_set = await redis_client.set(key, "1", ex=ttl_seconds, nx=True)
            redis_latency_ms = (time.monotonic() - redis_started) * 1000
            dedup_backend = "redis"
            dedup_fallback_reason = None
            if not was_set:
                _finalize_diagnostics(
                    duplicate=True,
                    dedup_backend=dedup_backend,
                    dedup_fallback_reason=dedup_fallback_reason,
                    redis_latency_ms=redis_latency_ms,
                    db_latency_ms=db_latency_ms,
                    messages_latency_ms=messages_latency_ms,
                    started_at=started_at,
                )
                return True
        except Exception as e:
            redis_latency_ms = (time.monotonic() - redis_started) * 1000
            dedup_backend = "db_fallback"
            dedup_fallback_reason = "redis_error"
            logger.warning(f"Dedup redis unavailable, falling back to DB: {e}")

    # Persistent dedup in DB (message_dedup) to survive restarts/retries.
    db_started = time.monotonic()
    try:
        result = db.execute(
            text(
                """
                INSERT INTO message_dedup (client_id, message_id)
                VALUES (:client_id, :message_id)
                ON CONFLICT DO NOTHING
                """
            ),
            {"client_id": client_id, "message_id": message_id},
        )
        db_latency_ms = (time.monotonic() - db_started) * 1000
        db.commit()
        if result.rowcount == 0:
            logger.info(
                "Duplicate message_id (DB)",
                extra={"context": {"client_id": str(client_id), "message_id": message_id}},
            )
            _finalize_diagnostics(
                duplicate=True,
                dedup_backend=dedup_backend,
                dedup_fallback_reason=dedup_fallback_reason,
                redis_latency_ms=redis_latency_ms,
                db_latency_ms=db_latency_ms,
                messages_latency_ms=messages_latency_ms,
                started_at=started_at,
            )
            return True
    except Exception as e:
        db_latency_ms = (time.monotonic() - db_started) * 1000
        if dedup_fallback_reason:
            dedup_fallback_reason = f"{dedup_fallback_reason}+db_insert_error"
        else:
            dedup_fallback_reason = "db_insert_error"
        logger.warning(
            "DB dedup check failed, falling back to messages table",
            extra={"context": {"client_id": str(client_id), "message_id": message_id, "error": str(e)}},
        )

    messages_started = time.monotonic()
    duplicate = _lookup_duplicate_message_in_messages_table(
        db,
        client_id=client_id,
        message_id=message_id,
    )
    messages_latency_ms = (time.monotonic() - messages_started) * 1000
    if duplicate:
        logger.info(
            "Duplicate message_id (messages table)",
            extra={"context": {"client_id": str(client_id), "message_id": message_id}},
        )
    _finalize_diagnostics(
        duplicate=duplicate is not None,
        dedup_backend=dedup_backend,
        dedup_fallback_reason=dedup_fallback_reason,
        redis_latency_ms=redis_latency_ms,
        db_latency_ms=db_latency_ms,
        messages_latency_ms=messages_latency_ms,
        started_at=started_at,
    )
    return duplicate is not None


async def _handle_dedup_gate(
    *,
    db: Session,
    client,
    message_id: str | None,
    remote_jid: str,
    metadata,
    message_text: str,
    conversation_id,
    resolve_trace_conversation,
    record_early_trace,
    dedup_diagnostics: dict[str, Any] | None = None,
) -> tuple[WebhookResponse | None, str | None]:
    if _is_fast_dedup_bypass_enabled():
        if not message_id:
            from app.services.outbox_service import build_inbound_message_id

            message_id = build_inbound_message_id(
                None,
                remote_jid,
                metadata.timestamp if metadata else None,
                message_text,
            )
            if metadata:
                metadata.messageId = message_id
        if isinstance(dedup_diagnostics, dict):
            dedup_diagnostics["dedup_backend"] = "fast_test_bypass"
            dedup_diagnostics["dedup_fallback_reason"] = "test_mode_fast_dedup"
            dedup_diagnostics["dedup_duplicate"] = False
            dedup_diagnostics["dedup_latency_ms"] = 0.0
        return None, message_id

    if await is_duplicate_message_id(
        db=db,
        client_id=client.id,
        message_id=message_id,
        diagnostics=dedup_diagnostics,
    ):
        logger.info(f"Duplicate message_id skipped: {message_id}")
        trace_conversation = resolve_trace_conversation(
            trace_client=client,
            trace_conversation_id=conversation_id,
            trace_message_id=message_id,
            trace_remote_jid=remote_jid,
        )
        if record_early_trace(
            trace_conversation,
            stage="dedupe",
            decision="skip",
            reason="duplicate_message_id",
            meta={
                "dedup_backend": (
                    dedup_diagnostics.get("dedup_backend")
                    if isinstance(dedup_diagnostics, dict)
                    else None
                ),
                "dedup_fallback_reason": (
                    dedup_diagnostics.get("dedup_fallback_reason")
                    if isinstance(dedup_diagnostics, dict)
                    else None
                ),
            },
        ):
            db.commit()
        return (
            WebhookResponse(
                success=True,
                message="Duplicate message_id",
                conversation_id=None,
                bot_response=None,
            ),
            message_id,
        )
    if not message_id:
        from app.services.outbox_service import build_inbound_message_id

        message_id = build_inbound_message_id(
            None,
            remote_jid,
            metadata.timestamp if metadata else None,
            message_text,
        )
        if metadata:
            metadata.messageId = message_id
    return None, message_id


async def _handle_debounce_gate(
    *,
    db: Session,
    client,
    conversation,
    message_text: str,
    message_id: str | None,
    remote_jid: str,
    batch_messages: list[str] | None,
    batch_messages_provided: bool,
    payload_client_slug: str,
    now: datetime,
) -> tuple[WebhookResponse | None, str, list[str] | None, bool, datetime]:
    append_user_message = True
    if conversation.state in [ConversationState.BOT_ACTIVE.value, ConversationState.PENDING.value] and not batch_messages_provided:
        from .guards import _handle_post_debounce_muted_state_gate
        from .trace import _record_decision_trace

        db.commit()

        debounce_enabled, _, ttl_seconds, redis_url, socket_timeout_seconds = _get_debounce_settings()
        buffer_enabled, max_buffer_messages = _get_message_buffer_settings()
        redis_client = _get_debounce_redis(redis_url, socket_timeout_seconds)

        if debounce_enabled and buffer_enabled and redis_client:
            await _buffer_user_message(
                redis_client=redis_client,
                client_id=str(client.id),
                remote_jid=remote_jid,
                message_text=message_text,
                ttl_seconds=ttl_seconds,
                max_messages=max_buffer_messages,
            )

        should_process = await should_process_debounced_message(
            client_id=str(client.id),
            remote_jid=remote_jid,
            message_id=message_id,
            redis_client=redis_client,
        )
        if not should_process:
            logger.info(
                "Debounced intermediate message",
                extra={"context": {"remote_jid": remote_jid, "message_id": message_id}},
            )
            _record_decision_trace(
                conversation,
                {
                    "stage": "debounce",
                    "decision": "skip",
                    "reason": "intermediate_message",
                    "state": conversation.state,
                },
            )
            db.commit()
            return (
                WebhookResponse(
                    success=True,
                    message="Debounced: skipped intermediate message",
                    conversation_id=conversation.id,
                    bot_response=None,
                ),
                message_text,
                batch_messages,
                append_user_message,
                now,
            )

        if debounce_enabled and buffer_enabled and redis_client:
            buffered_messages = await _drain_buffered_messages(
                redis_client=redis_client,
                client_id=str(client.id),
                remote_jid=remote_jid,
            )
            if buffered_messages:
                logger.info(
                    "Debounce buffer drained",
                    extra={
                        "context": {
                            "remote_jid": remote_jid,
                            "message_id": message_id,
                            "buffered_count": len(buffered_messages),
                        }
                    },
                )
                message_text = " ".join(buffered_messages)
                if not batch_messages_provided:
                    batch_messages = [message.strip() for message in buffered_messages if message and message.strip()]
                    if not batch_messages and message_text.strip():
                        batch_messages = [message_text.strip()]
                append_user_message = False

        db.refresh(conversation)
        now = datetime.now(timezone.utc)
        if conversation.state == ConversationState.MANAGER_ACTIVE.value:
            _record_decision_trace(
                conversation,
                {
                    "stage": "debounce",
                    "decision": "manager_active",
                    "reason": "state_changed",
                    "state": conversation.state,
                },
            )
            db.commit()
            return (
                WebhookResponse(
                    success=True,
                    message="Manager active (after debounce), message forwarded",
                    conversation_id=conversation.id,
                    bot_response=None,
                ),
                message_text,
                batch_messages,
                append_user_message,
                now,
            )
        muted_state_response = _handle_post_debounce_muted_state_gate(
            conversation=conversation,
            message_text=message_text,
            batch_messages=batch_messages,
            client_slug=payload_client_slug,
            now=now,
        )
        if muted_state_response is not None:
            return (
                muted_state_response,
                message_text,
                batch_messages,
                append_user_message,
                now,
            )

    return None, message_text, batch_messages, append_user_message, now


__all__ = [
    "DuplicateMessageProbe",
    "_buffer_user_message",
    "_drain_buffered_messages",
    "_get_debounce_redis",
    "_get_debounce_settings",
    "_get_dedup_settings",
    "_get_message_buffer_settings",
    "_handle_debounce_gate",
    "_handle_dedup_gate",
    "_lookup_preexisting_duplicate_message",
    "is_duplicate_message_id",
    "should_process_debounced_message",
]
