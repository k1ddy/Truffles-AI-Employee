"""Debounce/buffer/dedup helpers for inbound webhook messages."""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Message

logger = get_logger("webhook")

# Optional Redis-based debounce for bursty WhatsApp messages.
try:
    import redis.asyncio as redis_async  # type: ignore
except Exception:  # pragma: no cover
    redis_async = None


_debounce_redis_client = None
_debounce_redis_url = None


def _get_debounce_settings() -> tuple[bool, float, int, str, float]:
    from . import _legacy as legacy

    enabled = legacy._is_env_enabled(os.environ.get("DEBOUNCE_ENABLED"), default=True)
    inactivity_seconds = float(os.environ.get("DEBOUNCE_INACTIVITY_SECONDS", "1.5"))
    ttl_seconds = int(float(os.environ.get("DEBOUNCE_TTL_SECONDS", "30")))
    redis_url = os.environ.get("REDIS_URL", "redis://truffles_redis_1:6379/0")
    socket_timeout_seconds = float(os.environ.get("DEBOUNCE_SOCKET_TIMEOUT_SECONDS", "0.3"))
    return enabled, inactivity_seconds, ttl_seconds, redis_url, socket_timeout_seconds


def _get_message_buffer_settings() -> tuple[bool, int]:
    from . import _legacy as legacy

    enabled = legacy._is_env_enabled(os.environ.get("DEBOUNCE_ENABLED"), default=True)
    max_messages = int(float(os.environ.get("DEBOUNCE_MAX_BUFFER_MESSAGES", "8")))
    return enabled, max_messages


def _get_dedup_settings() -> tuple[int, str, float]:
    ttl_seconds = int(float(os.environ.get("DEDUP_TTL_SECONDS", "86400")))
    redis_url = os.environ.get("REDIS_URL", "redis://truffles_redis_1:6379/0")
    socket_timeout_seconds = float(os.environ.get("DEDUP_SOCKET_TIMEOUT_SECONDS", "0.3"))
    return ttl_seconds, redis_url, socket_timeout_seconds


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

    redis_client = redis_client or _get_debounce_redis(redis_url, socket_timeout_seconds)
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


async def is_duplicate_message_id(
    *,
    db: Session,
    client_id,
    message_id: str | None,
    redis_client=None,
) -> bool:
    if not message_id:
        return False

    ttl_seconds, redis_url, socket_timeout_seconds = _get_dedup_settings()
    key = f"truffles:dedup:{client_id}:{message_id}"

    redis_client = redis_client or _get_debounce_redis(redis_url, socket_timeout_seconds)
    if redis_client:
        try:
            was_set = await redis_client.set(key, "1", ex=ttl_seconds, nx=True)
            if not was_set:
                return True
        except Exception as e:
            logger.warning(f"Dedup redis unavailable, falling back to DB: {e}")

    # Persistent dedup in DB (message_dedup) to survive restarts/retries.
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
        db.commit()
        if result.rowcount == 0:
            logger.info(
                "Duplicate message_id (DB)",
                extra={"context": {"client_id": str(client_id), "message_id": message_id}},
            )
            return True
    except Exception as e:
        logger.warning(
            "DB dedup check failed, falling back to messages table",
            extra={"context": {"client_id": str(client_id), "message_id": message_id, "error": str(e)}},
        )

    duplicate = (
        db.query(Message)
        .filter(
            Message.client_id == client_id,
            Message.message_metadata["message_id"].astext == message_id,
        )
        .first()
    )
    if duplicate:
        logger.info(
            "Duplicate message_id (messages table)",
            extra={"context": {"client_id": str(client_id), "message_id": message_id}},
        )
    return duplicate is not None


__all__ = [
    "_buffer_user_message",
    "_drain_buffered_messages",
    "_get_debounce_redis",
    "_get_debounce_settings",
    "_get_dedup_settings",
    "_get_message_buffer_settings",
    "is_duplicate_message_id",
    "should_process_debounced_message",
]
