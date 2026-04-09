"""Adapter-only session-memory helpers for reset/control-turn compatibility."""

from __future__ import annotations

import re
from datetime import datetime

from app.core import DialogStateService
from app.models import Conversation, Message
from app.routers.webhook.trace import _record_decision_trace, _update_message_decision_metadata
from app.services.ai_service import normalize_for_matching
from app.services.state_service import (
    _build_session_memory_observability_snapshot,
    _should_reset_session_memory_trigger,
)

_DIALOG_STATE_SERVICE = DialogStateService()
SESSION_MEMORY_KEY = "session_memory"
SESSION_MEMORY_TTL_HOURS = 24
SESSION_MEMORY_RESET_PHRASES = (
    "новый вопрос",
    "другая тема",
    "начнем сначала",
    "начнём сначала",
    "начнем заново",
    "начнём заново",
    "давай сначала",
)

def _get_session_memory(context: dict) -> dict:
    payload = context.get(SESSION_MEMORY_KEY) if isinstance(context, dict) else None
    if isinstance(payload, dict):
        return dict(payload)
    return {}


def _normalize_session_memory(memory: dict | None) -> tuple[dict, str | None]:
    return _DIALOG_STATE_SERVICE.normalize_session_memory_payload(memory)


def _is_session_memory_expired(memory: dict, now: datetime) -> bool:
    return _DIALOG_STATE_SERVICE.is_session_memory_expired(
        memory,
        now=now,
        default_ttl_hours=SESSION_MEMORY_TTL_HOURS,
    )


def _parse_session_memory_time(value: str | None) -> datetime | None:
    return _DIALOG_STATE_SERVICE._parse_iso_datetime(value)


def _should_reset_session_memory(message_text: str | None) -> bool:
    return _should_reset_session_memory_trigger(
        message_text,
        normalize_text=normalize_for_matching,
        reset_phrases=SESSION_MEMORY_RESET_PHRASES,
    )


def _is_session_reset_only_message(message_text: str | None) -> bool:
    if not message_text:
        return False
    cleaned = re.sub(r"\[[^\]]+\]", " ", message_text)
    normalized = normalize_for_matching(cleaned)
    if not normalized:
        return False
    return normalized in SESSION_MEMORY_RESET_PHRASES


def _session_memory_snapshot(memory: dict) -> dict:
    return _build_session_memory_observability_snapshot(memory)


def _record_session_memory_update(
    conversation: Conversation,
    saved_message: Message | None,
    *,
    memory: dict,
    reason: str,
) -> None:
    snapshot = _session_memory_snapshot(memory)
    trace = {"stage": "session_memory", "decision": "update", "reason": reason}
    trace.update(snapshot)
    _record_decision_trace(conversation, trace)
    if saved_message:
        _update_message_decision_metadata(saved_message, {"session_memory_update": snapshot})


def _update_session_memory_on_answer(
    context: dict,
    *,
    expected_reply_type: str,
    value: str,
    now: datetime,
) -> tuple[dict, dict]:
    memory = _DIALOG_STATE_SERVICE.update_session_memory_on_answer(
        _get_session_memory(context),
        expected_reply_type=expected_reply_type,
        value=value,
    )
    return _DIALOG_STATE_SERVICE.rebuild_context_session_memory(
        context,
        base_memory=memory,
        now=now,
        default_ttl_hours=SESSION_MEMORY_TTL_HOURS,
    )


def _clear_session_memory_expected_reply(
    context: dict,
    *,
    expected_reply_type: str | None,
    now: datetime,
) -> tuple[dict, dict, bool]:
    return _DIALOG_STATE_SERVICE.clear_context_session_memory_expected_reply(
        context,
        expected_reply_type=expected_reply_type,
        now=now,
        default_ttl_hours=SESSION_MEMORY_TTL_HOURS,
    )


def _update_session_memory_goal(
    context: dict,
    *,
    active_goal: str,
    now: datetime,
) -> tuple[dict, dict]:
    memory = _DIALOG_STATE_SERVICE.update_session_memory_goal(
        _get_session_memory(context),
        active_goal=active_goal,
    )
    return _DIALOG_STATE_SERVICE.rebuild_context_session_memory(
        context,
        base_memory=memory,
        now=now,
        default_ttl_hours=SESSION_MEMORY_TTL_HOURS,
    )
