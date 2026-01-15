"""Pending SLA and resume helpers."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Conversation, User
from app.schemas.webhook import WebhookResponse
from app.services.state_machine import ConversationState


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


def _handle_handover_confirmation_gate(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message_text: str,
    now: datetime,
    send_and_save,
    record_escalation_metric,
) -> WebhookResponse | None:
    from app.routers.webhook.context_manager import (
        _get_conversation_context,
        _get_handover_confirmation,
        _is_handover_confirmation_active,
        _reset_low_confidence_retry,
        _set_conversation_context,
        _set_handover_confirmation,
    )
    from app.services.ai_service import classify_confirmation

    from . import _legacy as legacy

    if conversation.state != ConversationState.BOT_ACTIVE.value:
        return None

    context = _get_conversation_context(conversation)
    confirmation = _get_handover_confirmation(context)
    if not confirmation:
        return None

    if not _is_handover_confirmation_active(confirmation, now):
        context = _set_handover_confirmation(context, None)
        _set_conversation_context(conversation, context)
        return None

    decision = classify_confirmation(message_text)
    if decision == "yes":
        context = _set_handover_confirmation(context, None)
        _set_conversation_context(conversation, context)
        _reset_low_confidence_retry(conversation)

        escalation_message = confirmation.get("user_message") or message_text
        _, reused, telegram_sent = legacy._reuse_active_handover(
            db=db,
            conversation=conversation,
            user=user,
            message=escalation_message,
            source="handover_confirmation",
            intent="low_confidence",
        )

        if reused:
            bot_response = legacy.MSG_ESCALATED
            result_message = (
                f"Handover confirmed (reused), telegram={'sent' if telegram_sent else 'failed'}"
            )
        else:
            record_escalation_metric("intent")
            esc_result = legacy.escalate_to_pending(
                db=db,
                conversation=conversation,
                user_message=escalation_message,
                trigger_type="intent",
                trigger_value="low_confidence",
            )

            if esc_result.ok:
                handover = esc_result.value
                telegram_sent = legacy.send_telegram_notification(
                    db=db,
                    handover=handover,
                    conversation=conversation,
                    user=user,
                    message=escalation_message,
                )
                bot_response = legacy.MSG_ESCALATED
                result_message = f"Handover confirmed, telegram={'sent' if telegram_sent else 'failed'}"
            else:
                bot_response = legacy.MSG_AI_ERROR
                result_message = f"Handover confirm escalation failed: {esc_result.error}"

        legacy._record_decision_trace(
            conversation,
            {
                "stage": "handover_confirmation",
                "decision": "confirmed",
                "reason": "user_confirmed",
                "state": conversation.state,
                "reused": reused,
            },
        )
        bot_response, sent = send_and_save(bot_response)
        if not sent:
            result_message = f"{result_message}; response_send=failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    if decision == "no":
        context = _set_handover_confirmation(context, None)
        _set_conversation_context(conversation, context)
        _reset_low_confidence_retry(conversation)

        bot_response = legacy.MSG_HANDOVER_DECLINED
        legacy._record_decision_trace(
            conversation,
            {
                "stage": "handover_confirmation",
                "decision": "declined",
                "reason": "user_declined",
                "state": conversation.state,
            },
        )
        bot_response, sent = send_and_save(bot_response)
        result_message = (
            "Handover declined, asked for salon details" if sent else "Handover decline send failed"
        )
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    context = _set_handover_confirmation(context, None)
    _set_conversation_context(conversation, context)
    return None
