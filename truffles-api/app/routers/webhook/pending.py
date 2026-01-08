"""Pending SLA and resume helpers."""

from __future__ import annotations

from datetime import datetime


def _normalize_pending_text(text: str) -> str:
    from . import _legacy as legacy

    normalized = legacy.normalize_for_matching(text)
    if not normalized:
        return ""
    return normalized.replace("ё", "е")


def _is_pending_ack(text: str) -> bool:
    from . import _legacy as legacy

    normalized = _normalize_pending_text(text)
    return normalized in legacy.PENDING_ACK_PHRASES


def _is_pending_close(text: str) -> bool:
    from . import _legacy as legacy

    normalized = _normalize_pending_text(text)
    return normalized in legacy.PENDING_CLOSE_PHRASES


def _get_pending_sla(context: dict) -> dict:
    from . import _legacy as legacy

    payload = context.get(legacy.PENDING_SLA_CONTEXT_KEY) if isinstance(context, dict) else None
    return payload if isinstance(payload, dict) else {}


def _set_pending_sla(context: dict, payload: dict) -> dict:
    from . import _legacy as legacy

    if not isinstance(context, dict):
        context = {}
    context[legacy.PENDING_SLA_CONTEXT_KEY] = payload
    return context


def _get_pending_resume(context: dict) -> dict | None:
    from . import _legacy as legacy

    payload = context.get(legacy.PENDING_RESUME_KEY) if isinstance(context, dict) else None
    if isinstance(payload, dict):
        return dict(payload)
    return None


def _set_pending_resume(context: dict, payload: dict | None) -> dict:
    from . import _legacy as legacy

    context = dict(context)
    if payload:
        context[legacy.PENDING_RESUME_KEY] = payload
    else:
        context.pop(legacy.PENDING_RESUME_KEY, None)
    return context


def _build_pending_resume_snapshot(
    *,
    context: dict,
    context_manager: dict,
    expected_reply_type: str | None,
    intent_queue: list[str] | None,
    booking_context: dict | None,
    session_memory: dict,
) -> dict:
    from . import _legacy as legacy

    service_hint = context.get(legacy.SERVICE_HINT_KEY) if isinstance(context, dict) else None
    service_hint_at = context.get(legacy.SERVICE_HINT_AT_KEY) if isinstance(context, dict) else None
    return {
        "context_manager": dict(context_manager) if isinstance(context_manager, dict) else {},
        "expected_reply_type": expected_reply_type,
        "intent_queue": list(intent_queue) if isinstance(intent_queue, list) else [],
        "booking": dict(booking_context) if isinstance(booking_context, dict) else {"active": False},
        "session_memory": dict(session_memory) if isinstance(session_memory, dict) else {},
        "service_hint": service_hint,
        "service_hint_at": service_hint_at,
    }


def _restore_pending_resume(
    *,
    context: dict,
    pending_resume: dict,
    now: datetime,
) -> dict:
    from . import _legacy as legacy

    context = _set_pending_resume(context, None)
    context = _set_pending_sla(context, {})
    context.pop("handover_confirmation", None)
    context = legacy._set_context_manager(
        context,
        pending_resume.get("context_manager") if isinstance(pending_resume, dict) else {},
    )
    context = legacy._set_expected_reply_type(
        context,
        pending_resume.get("expected_reply_type") if isinstance(pending_resume, dict) else None,
    )
    context = legacy._set_intent_queue(
        context,
        pending_resume.get("intent_queue") if isinstance(pending_resume, dict) else [],
    )
    booking_context = pending_resume.get("booking") if isinstance(pending_resume, dict) else None
    if isinstance(booking_context, dict):
        context = legacy._set_booking_context(context, booking_context)
    else:
        context = legacy._set_booking_context(context, {"active": False})
    session_memory = pending_resume.get("session_memory") if isinstance(pending_resume, dict) else None
    if isinstance(session_memory, dict) and session_memory:
        session_memory["last_updated_at"] = now.isoformat()
        context = legacy._set_session_memory(context, session_memory)
    else:
        context = legacy._set_session_memory(context, None)
    service_hint = pending_resume.get("service_hint") if isinstance(pending_resume, dict) else None
    if isinstance(service_hint, str) and service_hint.strip():
        context = legacy._set_service_hint(context, service_hint.strip(), now)
    else:
        context = legacy._clear_service_hint(context)
    return context
