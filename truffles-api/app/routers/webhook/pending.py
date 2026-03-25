"""Pending SLA and resume helpers."""

from __future__ import annotations

from datetime import datetime
from functools import partial

from sqlalchemy.orm import Session

from app.models import Conversation, Message, User
from app.schemas.webhook import WebhookResponse
from app.services.pack_runtime_service import get_system_lexicon_list
from app.services.sla_runtime_service import resolve_pending_sla_violation
from app.services.state_machine import ConversationState
from app.services.state_service import (
    ContinuityTransportDecision,
    HandoverConfirmationRuntimeHooks,
    PendingContinuityRuntimeHooks,
    _handle_handover_confirmation_runtime,
    _handle_pending_sla_runtime,
    _resolve_pending_ack,
    _resolve_pending_close,
    _resolve_pending_no_handover_reset,
)


def _normalize_pending_text(text: str) -> str:
    from . import _legacy as legacy

    normalized = legacy.normalize_for_matching(text)
    if not normalized:
        return ""
    return normalized.replace("ё", "е")


def _matches_lexicon_any(text: str, key: str) -> bool:
    normalized = _normalize_pending_text(text)
    if not normalized:
        return False
    phrases = get_system_lexicon_list(key)
    if not phrases:
        return False
    phrase_set = set(phrases)
    if normalized in phrase_set:
        return True
    tokens = normalized.split()
    if any(token in phrase_set for token in tokens):
        return True
    return any(" " in phrase and phrase in normalized for phrase in phrases)


def _matches_lexicon_all_tokens(text: str, key: str) -> bool:
    normalized = _normalize_pending_text(text)
    if not normalized:
        return False
    phrases = get_system_lexicon_list(key)
    if not phrases:
        return False
    phrase_set = set(phrases)
    if normalized in phrase_set:
        return True
    tokens = normalized.split()
    if not tokens:
        return False
    if all(token in phrase_set for token in tokens):
        return True
    return any(" " in phrase and phrase in normalized for phrase in phrases)


def _is_pending_ack(text: str) -> bool:
    return _matches_lexicon_all_tokens(text, "pending_ack_phrases")


def _is_pending_close(text: str) -> bool:
    return _matches_lexicon_any(text, "pending_close_phrases")


def _is_pending_wait(text: str) -> bool:
    return _matches_lexicon_any(text, "pending_wait_phrases")


def _build_transport_webhook_response(
    *,
    db: Session,
    conversation: Conversation,
    decision: ContinuityTransportDecision,
    send_and_save,
) -> WebhookResponse | None:
    if not decision.handled:
        return None

    bot_response = None
    result_message = decision.success_message or "Handled"
    if isinstance(decision.bot_response, str):
        bot_response, sent = send_and_save(decision.bot_response)
        result_message = decision.success_message if sent else decision.failure_message or result_message

    db.commit()
    return WebhookResponse(
        success=True,
        message=result_message,
        conversation_id=conversation.id,
        bot_response=bot_response,
    )


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
    from . import _legacy as legacy
    from app.routers.webhook.context_manager import (
        _get_conversation_context,
        _get_handover_confirmation,
        _is_handover_confirmation_active,
        _reset_low_confidence_retry,
        _set_conversation_context,
        _set_handover_confirmation,
    )
    from app.services.ai_service import classify_confirmation

    decision = _handle_handover_confirmation_runtime(
        db=db,
        conversation=conversation,
        user=user,
        message_text=message_text,
        now=now,
        hooks=HandoverConfirmationRuntimeHooks(
            get_conversation_context=_get_conversation_context,
            get_handover_confirmation=_get_handover_confirmation,
            is_handover_confirmation_active=_is_handover_confirmation_active,
            set_handover_confirmation=_set_handover_confirmation,
            set_conversation_context=_set_conversation_context,
            reset_low_confidence_retry=_reset_low_confidence_retry,
            classify_confirmation=classify_confirmation,
            reuse_active_handover=legacy._reuse_active_handover,
            escalate_to_pending=legacy.escalate_to_pending,
            send_telegram_notification=legacy.send_telegram_notification,
            record_escalation_metric=record_escalation_metric,
            record_decision_trace=legacy._record_decision_trace,
            msg_escalated=legacy.MSG_ESCALATED,
            msg_ai_error=legacy.MSG_AI_ERROR,
            msg_handover_declined=legacy.MSG_HANDOVER_DECLINED,
        ),
    )
    return _build_transport_webhook_response(
        db=db,
        conversation=conversation,
        decision=decision,
        send_and_save=send_and_save,
    )


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
    guard_only: bool = False,
    in_domain_signal: bool = False,
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
    continuity_hooks = PendingContinuityRuntimeHooks(
        get_conversation_context=legacy._get_conversation_context,
        set_conversation_context=legacy._set_conversation_context,
        transition_state=legacy.transition_state,
        manager_resolve=partial(legacy.manager_resolve, db),
        record_decision_trace=legacy._record_decision_trace,
        update_message_decision_metadata=legacy._update_message_decision_metadata,
    )
    guard_only_skip = bool(guard_only and in_domain_signal)
    handover = legacy.get_active_handover(db, conversation.id)
    if not handover:
        _resolve_pending_no_handover_reset(
            conversation=conversation,
            saved_message=saved_message,
            router_pending_meta=router_pending_meta,
            hooks=continuity_hooks,
        )
        return None

    if legacy.is_opt_out_message(message_text):
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
        return _build_transport_webhook_response(
            db=db,
            conversation=conversation,
            decision=_resolve_pending_close(
                conversation=conversation,
                handover=handover,
                saved_message=saved_message,
                router_pending_meta=router_pending_meta,
                hooks=continuity_hooks,
            ),
            send_and_save=send_and_save,
        )

    if _is_pending_ack(message_text):
        return _build_transport_webhook_response(
            db=db,
            conversation=conversation,
            decision=_resolve_pending_ack(
                conversation=conversation,
                handover=handover,
                saved_message=saved_message,
                now=now,
                router_pending_meta=router_pending_meta,
                msg_pending_ack=legacy.MSG_PENDING_ACK,
                hooks=continuity_hooks,
            ),
            send_and_save=send_and_save,
        )

    pending_intent = getattr(handover, "trigger_value", None)
    if legacy.is_handover_status_question(message_text) and not (
        isinstance(pending_intent, str) and pending_intent.strip() == "procedure_combo"
    ):
        if guard_only_skip:
            trace_payload = {
                "stage": "pending_status",
                "decision": "guard_only",
                "state": conversation.state,
            }
            trace_payload.update(router_pending_meta)
            legacy._record_decision_trace(conversation, trace_payload)
            if saved_message:
                legacy._update_message_decision_metadata(
                    saved_message,
                    {
                        "pending_action": "pending_status_guard_only",
                        "pending_guard_only": True,
                    },
                )
            return None
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

    if _is_pending_wait(message_text):
        if guard_only_skip:
            trace_payload = {
                "stage": "pending_wait",
                "decision": "guard_only",
                "state": conversation.state,
            }
            trace_payload.update(router_pending_meta)
            legacy._record_decision_trace(conversation, trace_payload)
            if saved_message:
                legacy._update_message_decision_metadata(
                    saved_message,
                    {
                        "pending_action": "pending_wait_guard_only",
                        "pending_guard_only": True,
                    },
                )
            return None
        bot_response = legacy.MSG_PENDING_WAIT
        trace_payload = {
            "stage": "pending_wait",
            "decision": "pending_wait",
            "state": conversation.state,
        }
        trace_payload.update(router_pending_meta)
        legacy._record_decision_trace(conversation, trace_payload)
        if saved_message:
            legacy._update_message_decision_metadata(
                saved_message,
                {
                    "pending_action": "pending_wait",
                },
            )
        bot_response, sent = send_and_save(bot_response)
        result_message = "Pending wait response sent" if sent else "Pending wait send failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    sla_decision = _handle_pending_sla_runtime(
        db=db,
        conversation=conversation,
        saved_message=saved_message,
        now=now,
        guard_only_skip=guard_only_skip,
        router_pending_meta=router_pending_meta,
        pending_sla_ping_minutes=legacy.PENDING_SLA_PING_MINUTES,
        pending_sla_ping_sent_key=legacy.PENDING_SLA_PING_SENT_KEY,
        msg_pending_wait=legacy.MSG_PENDING_WAIT,
        msg_pending_sla_ping=legacy.MSG_PENDING_SLA_PING,
        resolve_pending_sla_violation_fn=resolve_pending_sla_violation,
        hooks=continuity_hooks,
    )
    if sla_decision is not None:
        return _build_transport_webhook_response(
            db=db,
            conversation=conversation,
            decision=sla_decision,
            send_and_save=send_and_save,
        )

    trace_payload = {
        "stage": "pending_guard",
        "decision": "soft_pass",
        "state": conversation.state,
    }
    if isinstance(pending_intent, str) and pending_intent.strip():
        trace_payload["pending_intent"] = pending_intent.strip()
    trace_payload.update(router_pending_meta)
    legacy._record_decision_trace(conversation, trace_payload)
    if saved_message:
        legacy._update_message_decision_metadata(
            saved_message,
            {
                "pending_action": "pending_pass",
                "pending_guard": "soft_pass",
            },
        )
    return None
