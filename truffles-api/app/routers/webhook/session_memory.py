"""Session memory helpers for tracking question/answer context."""

from __future__ import annotations

import re
from datetime import datetime

from app.core import DialogStateService
from app.models import Conversation, Message
from app.routers.webhook.trace import _record_decision_trace, _update_message_decision_metadata
from app.services.ai_service import normalize_for_matching
from app.services.state_service import (
    SessionMemoryRuntimeHooks,
    _build_session_memory_observability_snapshot,
    _clear_session_memory_expected_reply_context,
    _reset_session_memory_context,
    _should_reset_session_memory_trigger,
)

_DIALOG_STATE_SERVICE = DialogStateService()


def _get_session_memory(context: dict) -> dict:
    from . import _legacy as legacy

    payload = context.get(legacy.SESSION_MEMORY_KEY) if isinstance(context, dict) else None
    if isinstance(payload, dict):
        return dict(payload)
    return {}


def _normalize_session_memory(memory: dict | None) -> tuple[dict, str | None]:
    return _DIALOG_STATE_SERVICE.normalize_session_memory_payload(memory)


def _set_session_memory(context: dict, memory: dict | None) -> dict:
    from . import _legacy as legacy

    return _DIALOG_STATE_SERVICE.set_context_session_memory(
        context,
        memory,
        key=legacy.SESSION_MEMORY_KEY,
    )


def _sync_session_memory_interaction_state(
    context: dict,
    *,
    interaction_state: dict | None,
    now: datetime,
) -> tuple[dict, dict]:
    from . import _legacy as legacy

    memory, changed = _DIALOG_STATE_SERVICE.sync_session_memory_interaction_state(
        _get_session_memory(context),
        interaction_state=interaction_state,
        now=now,
        default_ttl_hours=legacy.SESSION_MEMORY_TTL_HOURS,
    )
    if changed:
        context = _set_session_memory(context, memory)
    return context, memory


def _is_session_memory_expired(memory: dict, now: datetime) -> bool:
    from . import _legacy as legacy

    return _DIALOG_STATE_SERVICE.is_session_memory_expired(
        memory,
        now=now,
        default_ttl_hours=legacy.SESSION_MEMORY_TTL_HOURS,
    )


def _parse_session_memory_time(value: str | None) -> datetime | None:
    return _DIALOG_STATE_SERVICE._parse_iso_datetime(value)


def _should_reset_session_memory(message_text: str | None) -> bool:
    from . import _legacy as legacy

    return _should_reset_session_memory_trigger(
        message_text,
        normalize_text=normalize_for_matching,
        reset_phrases=legacy.SESSION_MEMORY_RESET_PHRASES,
    )


def _is_session_reset_only_message(message_text: str | None) -> bool:
    if not message_text:
        return False
    cleaned = re.sub(r"\[[^\]]+\]", " ", message_text)
    normalized = normalize_for_matching(cleaned)
    if not normalized:
        return False
    from . import _legacy as legacy

    return normalized in legacy.SESSION_MEMORY_RESET_PHRASES


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


def _reset_session_memory(
    *,
    context: dict,
    context_manager: dict,
    reason: str,
    now: datetime,
) -> tuple[dict, dict, dict]:
    from . import _legacy as legacy

    return _reset_session_memory_context(
        context=context,
        context_manager=context_manager,
        reason=reason,
        now=now,
        session_memory_ttl_hours=legacy.SESSION_MEMORY_TTL_HOURS,
        class_manager_key=legacy.CLASS_CARRYOVER_KEY,
        service_manager_key=legacy.SERVICE_CARRYOVER_KEY,
        consult_manager_key=legacy.CONSULT_CONTEXT_KEY,
        canonical_state_key="canonical_dialog_state",
        referent_key="service",
        hooks=SessionMemoryRuntimeHooks(
            set_context_manager=legacy._set_context_manager,
            set_expected_reply_type=legacy._set_expected_reply_type,
            set_intent_queue=legacy._set_intent_queue,
            set_booking_context=legacy._set_booking_context,
            clear_service_hint=legacy._clear_service_hint,
        ),
    )


def _update_session_memory_on_question(
    context: dict,
    *,
    expected_reply_type: str,
    active_goal: str | None,
    now: datetime,
) -> tuple[dict, dict]:
    from . import _legacy as legacy

    memory = _DIALOG_STATE_SERVICE.update_session_memory_on_question(
        _get_session_memory(context),
        expected_reply_type=expected_reply_type,
        active_goal=active_goal,
    )
    memory = _DIALOG_STATE_SERVICE.touch_session_memory_payload(
        memory,
        now=now,
        default_ttl_hours=legacy.SESSION_MEMORY_TTL_HOURS,
    )
    context = _set_session_memory(context, memory)
    return context, memory


def _update_session_memory_on_answer(
    context: dict,
    *,
    expected_reply_type: str,
    value: str,
    now: datetime,
) -> tuple[dict, dict]:
    from . import _legacy as legacy

    memory = _DIALOG_STATE_SERVICE.update_session_memory_on_answer(
        _get_session_memory(context),
        expected_reply_type=expected_reply_type,
        value=value,
    )
    memory = _DIALOG_STATE_SERVICE.touch_session_memory_payload(
        memory,
        now=now,
        default_ttl_hours=legacy.SESSION_MEMORY_TTL_HOURS,
    )
    context = _set_session_memory(context, memory)
    return context, memory


def _clear_session_memory_expected_reply(
    context: dict,
    *,
    expected_reply_type: str | None,
    now: datetime,
) -> tuple[dict, dict, bool]:
    from . import _legacy as legacy

    return _clear_session_memory_expected_reply_context(
        context=context,
        expected_reply_type=expected_reply_type,
        now=now,
        session_memory_ttl_hours=legacy.SESSION_MEMORY_TTL_HOURS,
    )


def _update_session_memory_goal(
    context: dict,
    *,
    active_goal: str,
    now: datetime,
) -> tuple[dict, dict]:
    from . import _legacy as legacy

    memory = _DIALOG_STATE_SERVICE.update_session_memory_goal(
        _get_session_memory(context),
        active_goal=active_goal,
    )
    memory = _DIALOG_STATE_SERVICE.touch_session_memory_payload(
        memory,
        now=now,
        default_ttl_hours=legacy.SESSION_MEMORY_TTL_HOURS,
    )
    context = _set_session_memory(context, memory)
    return context, memory
