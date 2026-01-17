"""Pending SLA and resume helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Conversation, Message, User
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


def _forward_pending_to_telegram(
    *,
    db: Session,
    client_id,
    conversation: Conversation,
    metadata,
    message_text: str,
    has_media: bool,
    media_info,
    media_decision,
    media_policy: dict | None,
    saved_message: Message | None,
    transcript: str | None,
) -> None:
    from . import _legacy as legacy

    forwarded_to_telegram = bool(metadata.forwarded_to_telegram) if metadata else False

    if (
        conversation.state
        in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]
        and not forwarded_to_telegram
    ):
        if conversation.telegram_topic_id:
            bot_token, chat_id = legacy.get_telegram_credentials(db, client_id)
            if bot_token and chat_id:
                telegram = legacy.TelegramService(bot_token)
                forward_result = None
                caption = None
                if (
                    has_media
                    and media_info
                    and media_decision
                    and media_decision.allowed
                    and (media_policy or {}).get("forward_to_telegram")
                ):
                    stored_path = None
                    if saved_message and isinstance(saved_message.message_metadata, dict):
                        stored_path = (saved_message.message_metadata.get("media") or {}).get(
                            "storage_path"
                        )
                    caption = legacy._build_media_caption(message_text, media_info)
                    forward_result = legacy._send_telegram_media(
                        telegram=telegram,
                        chat_id=chat_id,
                        topic_id=conversation.telegram_topic_id,
                        media=media_info,
                        caption=caption,
                        stored_path=stored_path,
                    )
                elif not has_media:
                    forward_result = telegram.send_message(
                        chat_id=chat_id,
                        text=f"👤 <b>Клиент:</b> {message_text}",
                        message_thread_id=conversation.telegram_topic_id,
                    )
                if forward_result and forward_result.get("ok"):
                    if metadata:
                        metadata.forwarded_to_telegram = True
                    if (
                        transcript
                        and caption
                        and legacy._is_voice_note(media_info)
                        and saved_message
                        and transcript.strip() == caption.strip()
                    ):
                        legacy._update_message_media_metadata(
                            saved_message, {"transcript_forwarded": True}
                        )
                elif forward_result:
                    legacy.logger.warning(
                        "Forward to Telegram failed",
                        extra={
                            "context": {
                                "conversation_id": str(conversation.id),
                                "state": conversation.state,
                                "telegram_topic_id": conversation.telegram_topic_id,
                                "error": forward_result.get("description") or forward_result.get("error"),
                            }
                        },
                    )

    if (
        transcript
        and media_info
        and legacy._is_voice_note(media_info)
        and conversation.state
        in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]
        and conversation.telegram_topic_id
    ):
        already_forwarded = False
        if saved_message and isinstance(saved_message.message_metadata, dict):
            media_meta = saved_message.message_metadata.get("media") or {}
            already_forwarded = bool(media_meta.get("transcript_forwarded"))
        if not already_forwarded:
            bot_token, chat_id = legacy.get_telegram_credentials(db, client_id)
            if bot_token and chat_id:
                telegram = legacy.TelegramService(bot_token)
                forward_result = telegram.send_message(
                    chat_id=chat_id,
                    text=f"📝 <b>Транскрипт:</b> {transcript}",
                    message_thread_id=conversation.telegram_topic_id,
                )
                if forward_result and forward_result.get("ok") and saved_message:
                    legacy._update_message_media_metadata(
                        saved_message, {"transcript_forwarded": True}
                    )
                elif forward_result:
                    legacy.logger.warning(
                        "Transcript forward to Telegram failed",
                        extra={
                            "context": {
                                "conversation_id": str(conversation.id),
                                "state": conversation.state,
                                "telegram_topic_id": conversation.telegram_topic_id,
                                "error": forward_result.get("description") or forward_result.get("error"),
                            }
                        },
                    )


def _handle_manager_active_gate(
    *,
    db: Session,
    conversation: Conversation,
    saved_message: Message | None,
) -> WebhookResponse | None:
    from . import _legacy as legacy

    if conversation.state != ConversationState.MANAGER_ACTIVE.value:
        return None

    router_pending_meta = legacy._set_router_observability(
        saved_message,
        eligible=False,
        reason="pending",
    )
    trace_payload = {
        "stage": "routing",
        "decision": "manager_active_silent",
        "state": conversation.state,
    }
    trace_payload.update(router_pending_meta)
    legacy._record_decision_trace(conversation, trace_payload)
    db.commit()
    return WebhookResponse(
        success=True,
        message="Manager active, message forwarded",
        conversation_id=conversation.id,
        bot_response=None,
    )


def _handle_pending_gate(
    *,
    db: Session,
    conversation: Conversation,
    message_text: str,
    saved_message: Message | None,
    now: datetime,
    send_and_save,
) -> WebhookResponse | None:
    from . import _legacy as legacy

    if conversation.state != ConversationState.PENDING.value:
        return None

    router_pending_meta = legacy._set_router_observability(
        saved_message,
        eligible=False,
        reason="pending",
    )
    if legacy.is_opt_out_message(message_text):
        handover = legacy.get_active_handover(db, conversation.id)
        if handover:
            legacy.manager_resolve(
                db, conversation, handover, manager_id="system", manager_name="system"
            )
        bot_response = legacy.MSG_MUTED_TEMP
        trace_payload = {
            "stage": "rejection",
            "decision": "cancel_handover",
            "state": conversation.state,
        }
        trace_payload.update(router_pending_meta)
        legacy._record_decision_trace(conversation, trace_payload)
        legacy._record_message_decision_meta(
            saved_message,
            action="rejection",
            intent="opt_out",
            source="pending",
            fast_intent=False,
        )
        bot_response, sent = send_and_save(bot_response)
        result_message = "Pending opt-out handled" if sent else "Pending opt-out send failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    if _is_pending_close(message_text):
        handover = legacy.get_active_handover(db, conversation.id)
        if handover:
            legacy.manager_resolve(db, conversation, handover, manager_id="system", manager_name="system")
        conversation.bot_status = "muted"
        conversation.bot_muted_until = None
        trace_payload = {
            "stage": "pending_sla",
            "decision": "pending_close",
            "state": conversation.state,
        }
        trace_payload.update(router_pending_meta)
        legacy._record_decision_trace(conversation, trace_payload)
        if saved_message:
            legacy._update_message_decision_metadata(
                saved_message,
                {
                    "pending_action": "pending_close",
                },
            )
        db.commit()
        return WebhookResponse(
            success=True,
            message="Pending closed by user",
            conversation_id=conversation.id,
            bot_response=None,
        )

    if _is_pending_ack(message_text):
        handover = legacy.get_active_handover(db, conversation.id)
        if handover:
            legacy.manager_resolve(
                db,
                conversation,
                handover,
                manager_id="system",
                manager_name="system",
                preserve_context=True,
            )
        else:
            legacy.transition_state(
                conversation,
                ConversationState.BOT_ACTIVE,
                allow_same=False,
                enforce=True,
            )
            if not isinstance(conversation.context, dict):
                conversation.context = {}
        conversation.bot_status = "active"
        pending_resume = _get_pending_resume(legacy._get_conversation_context(conversation))
        if pending_resume:
            restored_context = _restore_pending_resume(
                context=legacy._get_conversation_context(conversation),
                pending_resume=pending_resume,
                now=now,
            )
            restored_context = legacy._set_re_entry_required(
                restored_context,
                reason="pending_resume",
                now=now,
            )
            legacy._set_conversation_context(conversation, restored_context)
            legacy._record_decision_trace(
                conversation,
                {
                    "stage": "pending_resume",
                    "decision": "restore",
                    "reason": "pending_ack",
                },
            )
            legacy._record_decision_trace(
                conversation,
                {
                    "stage": "re_entry",
                    "decision": "required",
                    "reason": "pending_resume",
                },
            )
        elif not handover:
            legacy._record_decision_trace(
                conversation,
                {
                    "stage": "pending_resume",
                    "decision": "resume",
                    "reason": "pending_ack_no_handover",
                },
            )
        trace_payload = {
            "stage": "pending_sla",
            "decision": "pending_ack",
            "state": conversation.state,
        }
        trace_payload.update(router_pending_meta)
        legacy._record_decision_trace(conversation, trace_payload)
        if saved_message:
            legacy._update_message_decision_metadata(
                saved_message,
                {
                    "pending_action": "pending_ack",
                    "pending_resume_restored": bool(pending_resume),
                },
            )
        bot_response = legacy.MSG_PENDING_ACK
        bot_response, sent = send_and_save(bot_response)
        result_message = "Pending ack response sent" if sent else "Pending ack send failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    if legacy.is_handover_status_question(message_text):
        bot_response = legacy.MSG_PENDING_STATUS
        trace_payload = {
            "stage": "pending_status",
            "decision": "status_reply",
            "state": conversation.state,
        }
        trace_payload.update(router_pending_meta)
        legacy._record_decision_trace(conversation, trace_payload)
        if saved_message:
            legacy._update_message_decision_metadata(
                saved_message,
                {
                    "pending_action": "pending_status",
                },
            )
        bot_response, sent = send_and_save(bot_response)
        result_message = "Pending status response sent" if sent else "Pending status response failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    context = legacy._get_conversation_context(conversation)
    pending_sla = _get_pending_sla(context)
    ping_sent_at = pending_sla.get(legacy.PENDING_SLA_PING_SENT_KEY)
    escalated_at = conversation.escalated_at
    if escalated_at and escalated_at.tzinfo is None:
        escalated_at = escalated_at.replace(tzinfo=timezone.utc)
    ping_due = bool(
        escalated_at
        and not ping_sent_at
        and now - escalated_at >= timedelta(minutes=legacy.PENDING_SLA_PING_MINUTES)
    )
    if ping_due:
        pending_sla[legacy.PENDING_SLA_PING_SENT_KEY] = now.isoformat()
        context = _set_pending_sla(context, pending_sla)
        legacy._set_conversation_context(conversation, context)
        trace_payload = {
            "stage": "pending_sla",
            "decision": "ping",
            "state": conversation.state,
        }
        trace_payload.update(router_pending_meta)
        legacy._record_decision_trace(conversation, trace_payload)
        if saved_message:
            legacy._update_message_decision_metadata(
                saved_message,
                {
                    "pending_sla_ping": True,
                    "pending_action": "pending_sla_ping",
                },
            )
        bot_response = legacy.MSG_PENDING_SLA_PING
        bot_response, sent = send_and_save(bot_response)
        result_message = "Pending SLA ping sent" if sent else "Pending SLA ping send failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    bot_response = legacy.MSG_PENDING_WAIT
    trace_payload = {
        "stage": "pending_wait",
        "decision": "pending_wait",
        "state": conversation.state,
    }
    trace_payload.update(router_pending_meta)
    legacy._record_decision_trace(conversation, trace_payload)
    legacy._record_message_decision_meta(
        saved_message,
        action="pending_wait",
        intent=None,
        source="pending",
        fast_intent=False,
    )
    if saved_message:
        legacy._update_message_decision_metadata(
            saved_message,
            {
                "pending_action": "pending_wait",
            },
        )
    bot_response, sent = send_and_save(bot_response)
    result_message = "Pending wait response sent" if sent else "Pending wait response failed"
    db.commit()
    return WebhookResponse(
        success=True,
        message=result_message,
        conversation_id=conversation.id,
        bot_response=bot_response,
    )
