"""Intent-queue and clarify-guard helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Conversation, Message, User
from app.schemas.webhook import WebhookResponse
from app.services.ai_service import normalize_for_matching


def _get_intent_queue(context: dict) -> list[str]:
    from . import _legacy as legacy

    queue = context.get(legacy.INTENT_QUEUE_KEY) if isinstance(context, dict) else None
    if not isinstance(queue, list):
        return []
    cleaned: list[str] = []
    seen = set()
    for item in queue:
        if not isinstance(item, str):
            continue
        value = item.strip().casefold()
        if not value or value in seen:
            continue
        cleaned.append(value)
        seen.add(value)
    return cleaned


def _set_intent_queue(context: dict, queue: list[str] | None) -> dict:
    from . import _legacy as legacy

    context = dict(context)
    cleaned: list[str] = []
    seen = set()
    for item in queue or []:
        if not isinstance(item, str):
            continue
        value = item.strip().casefold()
        if not value or value in seen:
            continue
        cleaned.append(value)
        seen.add(value)
    if cleaned:
        context[legacy.INTENT_QUEUE_KEY] = cleaned
    else:
        context.pop(legacy.INTENT_QUEUE_KEY, None)
    return context


def _format_multi_intent_followup(primary: str, secondary: list[str]) -> str | None:
    if not primary:
        return None
    from . import _legacy as legacy

    labels = []
    for intent in secondary:
        label = legacy.MULTI_INTENT_LABELS.get(intent)
        if label:
            labels.append(label)
    if not labels:
        return "Есть ещё вопрос — уточните, пожалуйста."
    label_text = ", ".join(labels)
    if primary == "booking":
        return f"По {label_text} отвечу после записи."
    return f"Ещё был вопрос по {label_text}. Уточните, пожалуйста."


def _match_intent_choice_from_text(intent_queue: list[str], message_text: str) -> str | None:
    from . import _legacy as legacy

    normalized = normalize_for_matching(message_text)
    if not normalized:
        return None
    tokens = [token for token in normalized.split() if len(token) >= 4]
    if not tokens:
        tokens = [normalized] if len(normalized) >= 4 else []
    if not tokens:
        return None
    matches = []
    for intent in intent_queue:
        label = legacy.MULTI_INTENT_LABELS.get(intent)
        if not label:
            continue
        label_normalized = normalize_for_matching(label)
        if not label_normalized:
            continue
        for token in tokens:
            if (
                label_normalized.startswith(token)
                or token.startswith(label_normalized)
                or token in label_normalized
                or label_normalized in token
            ):
                matches.append(intent)
                break
    if len(matches) == 1:
        return matches[0]
    return None


def _select_intent_from_queue(
    intent_queue: list[str],
    intents: list[str],
    *,
    message_text: str | None = None,
) -> str | None:
    if not intent_queue or not intents:
        if message_text:
            return _match_intent_choice_from_text(intent_queue, message_text)
        return None
    for intent in intents:
        if intent in intent_queue:
            return intent
    if message_text:
        return _match_intent_choice_from_text(intent_queue, message_text)
    return None


def _format_intent_queue_prompt(intent_queue: list[str]) -> str | None:
    if not intent_queue:
        return None
    from . import _legacy as legacy

    labels = []
    for intent in intent_queue:
        label = legacy.MULTI_INTENT_LABELS.get(intent)
        if label:
            labels.append(f"по {label}")
    if not labels:
        return "Что разобрать дальше?"
    label_text = ", ".join(labels)
    return f"Что разобрать дальше: [{label_text}]?"


def _get_clarify_attempt_state(manager: dict, intent: str) -> tuple[int, str | None]:
    attempts = manager.get("clarify_attempts")
    if not isinstance(attempts, dict):
        return 0, None
    payload = attempts.get(intent)
    if not isinstance(payload, dict):
        return 0, None
    value = payload.get("count", 0)
    try:
        count = max(0, int(value))
    except (TypeError, ValueError):
        count = 0
    last_at = payload.get("last_at")
    return count, last_at if isinstance(last_at, str) else None


def _set_clarify_attempt(manager: dict, intent: str, count: int, now: datetime) -> dict:
    attempts = manager.get("clarify_attempts")
    attempts_map = dict(attempts) if isinstance(attempts, dict) else {}
    attempts_map[intent] = {"count": max(0, int(count)), "last_at": now.isoformat()}
    manager["clarify_attempts"] = attempts_map
    return manager


def _should_escalate_for_clarify(manager: dict, intent: str) -> bool:
    from . import _legacy as legacy

    count, _ = _get_clarify_attempt_state(manager, intent)
    return count >= legacy.CLARIFY_MAX_ATTEMPTS


def _booking_clarify_guard_reason(
    *,
    booking_interrupt_info: bool,
    basic_info_message: bool,
    session_memory_reset_reason: str | None,
    memory_expected_reply_type: str | None,
) -> str | None:
    if booking_interrupt_info:
        return "booking_interrupt_info"
    if session_memory_reset_reason:
        return f"session_memory_{session_memory_reset_reason}"
    if memory_expected_reply_type:
        return "session_memory_expected_reply"
    if basic_info_message:
        return "basic_info_message"
    return None


def _register_clarify_attempt(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    intent: str,
    now: datetime,
    reason: str,
) -> int:
    from . import _legacy as legacy

    context = legacy._get_conversation_context(conversation)
    manager = legacy._get_context_manager(context)
    count, _ = _get_clarify_attempt_state(manager, intent)
    count += 1
    manager = _set_clarify_attempt(manager, intent, count, now)
    context = legacy._set_context_manager(context, manager)
    legacy._set_conversation_context(conversation, context)
    attempt_payload = {"intent": intent, "count": count, "last_at": now.isoformat()}
    legacy._record_context_manager_decision(
        conversation,
        saved_message,
        decision="clarify_attempt",
        updates={"clarify_attempt": attempt_payload, "clarify_reason": reason},
    )
    if count >= legacy.CLARIFY_MAX_ATTEMPTS:
        legacy._update_compact_summary(
            conversation=conversation,
            saved_message=saved_message,
            reason="clarify_limit",
            now=now,
        )
    return count


def _handle_clarify_limit_escalation(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message_text: str,
    saved_message: Message | None,
    source: str,
    allow_handover: bool,
    escalation_intent: str = "clarify_limit",
    send_response,
    finalize_response=None,
) -> WebhookResponse:
    from . import _legacy as legacy

    bot_response = legacy.MSG_ESCALATED
    legacy._reset_low_confidence_retry(conversation)
    result_message = f"{source} clarify limit escalation"

    _, reused, telegram_sent = legacy._reuse_active_handover(
        db=db,
        conversation=conversation,
        user=user,
        message=message_text,
        source=source,
        intent=escalation_intent,
    )
    if reused:
        result_message = f"{source} clarify limit reuse, telegram={'sent' if telegram_sent else 'failed'}"
    elif conversation.state == legacy.ConversationState.BOT_ACTIVE.value and allow_handover:
        result = legacy.escalate_to_pending(
            db=db,
            conversation=conversation,
            user_message=message_text,
            trigger_type="intent",
            trigger_value=escalation_intent,
        )
        if result.ok:
            handover = result.value
            telegram_sent = legacy.send_telegram_notification(
                db=db,
                handover=handover,
                conversation=conversation,
                user=user,
                message=message_text,
            )
            result_message = f"{source} clarify limit escalation, telegram={'sent' if telegram_sent else 'failed'}"
        else:
            result_message = f"{source} clarify limit escalation failed: {result.error}"
    else:
        result_message = f"{source} clarify limit escalation skipped (already pending)"

    legacy._record_decision_trace(
        conversation,
        {
            "stage": source,
            "decision": escalation_intent,
            "intent": escalation_intent,
            "state": conversation.state,
        },
    )
    legacy._record_message_decision_meta(
        saved_message,
        action="escalate",
        intent=escalation_intent,
        source=source,
        fast_intent=False,
    )
    if saved_message:
        legacy._update_message_decision_metadata(saved_message, {"clarify_limit": True})
    if finalize_response:
        bot_response = finalize_response(bot_response)
    legacy.save_message(
        db,
        conversation.id,
        conversation.client_id,
        role="assistant",
        content=bot_response,
        message_metadata={"source": "bot"},
    )
    sent = send_response(bot_response)
    if not sent:
        result_message = f"{result_message}; response_send=failed"
    db.commit()
    return WebhookResponse(
        success=True,
        message=result_message,
        conversation_id=conversation.id,
        bot_response=bot_response,
    )


def _apply_session_timeout_reset(
    *,
    conversation: Conversation,
    previous_last_message_at: datetime | None,
    now: datetime,
) -> None:
    from . import _legacy as legacy

    if not previous_last_message_at:
        return
    last_seen = previous_last_message_at
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    time_since_last = now - last_seen
    if time_since_last > timedelta(hours=legacy.SESSION_TIMEOUT_HOURS):
        conversation.bot_status = "active"
        conversation.bot_muted_until = None
        conversation.no_count = 0
        legacy._set_conversation_context(conversation, {})
        legacy.logger.info(f"Session reset: {time_since_last} since last message")


def _handle_reengage_and_mute_gate(
    *,
    db: Session,
    client_id,
    client_slug: str,
    conversation: Conversation,
    message_text: str,
    batch_messages: list[str] | None,
    expected_reply_shortcircuit: bool,
    now: datetime,
    send_and_save,
) -> tuple[WebhookResponse | None, list[str], bool]:
    from app.services.ai_service import classify_confirmation

    from . import _legacy as legacy

    batch_messages = legacy._coerce_batch_messages(message_text, batch_messages)
    signal_messages = list(batch_messages)
    opt_out_in_batch = any(legacy.is_opt_out_message(msg) for msg in signal_messages)
    booking_signal, _ = legacy._evaluate_booking_signal(
        signal_messages,
        client_slug=client_slug,
        message_text=message_text,
    )
    if expected_reply_shortcircuit:
        booking_signal = True

    context = legacy._get_conversation_context(conversation)
    booking_state = legacy._get_booking_context(context)
    booking_active = bool(booking_state.get("active"))
    reengage_override = False

    if conversation.state == legacy.ConversationState.BOT_ACTIVE.value:
        reengage_confirmation = legacy._get_reengage_confirmation(context)
        if reengage_confirmation:
            if not legacy._is_reengage_confirmation_active(reengage_confirmation, now):
                context = legacy._set_reengage_confirmation(context, None)
                legacy._set_conversation_context(conversation, context)
            else:
                decision = classify_confirmation(message_text)
                if decision == "yes":
                    context = legacy._set_reengage_confirmation(context, None)
                    legacy._set_conversation_context(conversation, context)
                    conversation.bot_status = "active"
                    conversation.bot_muted_until = None
                    conversation.no_count = 0
                    reengage_override = True
                    stored_messages = reengage_confirmation.get("booking_messages")
                    if isinstance(stored_messages, list) and stored_messages:
                        batch_messages = legacy._coerce_batch_messages("", stored_messages)
                        signal_messages = list(batch_messages)
                        booking_signal, _ = legacy._evaluate_booking_signal(
                            signal_messages,
                            client_slug=client_slug,
                            message_text=signal_messages[-1] if signal_messages else message_text,
                        )
                    legacy._record_decision_trace(
                        conversation,
                        {
                            "stage": "routing",
                            "decision": "reengage_confirmed",
                            "reason": "confirmation_yes",
                            "state": conversation.state,
                            "booking_signal": booking_signal,
                            "opt_out_in_batch": opt_out_in_batch,
                        },
                    )
                elif decision == "no":
                    context = legacy._set_reengage_confirmation(context, None)
                    legacy._set_conversation_context(conversation, context)
                    mute_first, mute_second = legacy.get_mute_settings(db, client_id)
                    if conversation.no_count == 0:
                        conversation.bot_muted_until = now + timedelta(minutes=mute_first)
                        conversation.no_count = 1
                    else:
                        conversation.bot_muted_until = now + timedelta(hours=mute_second)
                        conversation.no_count += 1
                    legacy._record_decision_trace(
                        conversation,
                        {
                            "stage": "routing",
                            "decision": "reengage_declined",
                            "reason": "confirmation_no",
                            "state": conversation.state,
                            "booking_signal": booking_signal,
                            "opt_out_in_batch": opt_out_in_batch,
                        },
                    )
                    bot_response = legacy.MSG_REENGAGE_DECLINED
                    bot_response, sent = send_and_save(bot_response)
                    result_message = (
                        "Re-engage declined" if sent else "Re-engage decline send failed"
                    )
                    db.commit()
                    return (
                        WebhookResponse(
                            success=True,
                            message=result_message,
                            conversation_id=conversation.id,
                            bot_response=bot_response,
                        ),
                        batch_messages,
                        reengage_override,
                    )
                else:
                    reengage_confirmation["asked_at"] = now.isoformat()
                    context = legacy._set_reengage_confirmation(context, reengage_confirmation)
                    legacy._set_conversation_context(conversation, context)
                    legacy._record_decision_trace(
                        conversation,
                        {
                            "stage": "routing",
                            "decision": "reengage_confirmation_repeat",
                            "reason": "confirmation_repeat",
                            "state": conversation.state,
                            "booking_signal": booking_signal,
                            "opt_out_in_batch": opt_out_in_batch,
                        },
                    )
                    bot_response = legacy.MSG_REENGAGE_CONFIRM
                    bot_response, sent = send_and_save(bot_response)
                    result_message = (
                        "Re-engage confirmation requested"
                        if sent
                        else "Re-engage confirmation failed"
                    )
                    db.commit()
                    return (
                        WebhookResponse(
                            success=True,
                            message=result_message,
                            conversation_id=conversation.id,
                            bot_response=bot_response,
                        ),
                        batch_messages,
                        reengage_override,
                    )

    if conversation.state == legacy.ConversationState.BOT_ACTIVE.value and opt_out_in_batch and booking_signal:
        confirmation_payload = {
            "asked_at": now.isoformat(),
            "booking_messages": signal_messages,
        }
        context = legacy._set_reengage_confirmation(context, confirmation_payload)
        if booking_active:
            booking_state["active"] = False
            context = legacy._set_booking_context(context, booking_state)
        legacy._set_conversation_context(conversation, context)
        legacy._record_decision_trace(
            conversation,
            {
                "stage": "routing",
                "decision": "reengage_confirmation_requested",
                "reason": "opt_out_booking_signal",
                "state": conversation.state,
                "booking_signal": booking_signal,
                "opt_out_in_batch": opt_out_in_batch,
            },
        )
        bot_response = legacy.MSG_REENGAGE_CONFIRM
        bot_response, sent = send_and_save(bot_response)
        result_message = (
            "Re-engage confirmation requested"
            if sent
            else "Re-engage confirmation failed"
        )
        db.commit()
        return (
            WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            ),
            batch_messages,
            reengage_override,
        )

    is_muted = conversation.bot_status == "muted" or (
        conversation.bot_muted_until and conversation.bot_muted_until > now
    )
    if is_muted:
        if (booking_signal or booking_active) and not opt_out_in_batch:
            conversation.bot_status = "active"
            conversation.bot_muted_until = None
            conversation.no_count = 0
            legacy._record_decision_trace(
                conversation,
                {
                    "stage": "routing",
                    "decision": "mute_cleared_for_booking",
                    "reason": "booking_signal",
                    "state": conversation.state,
                    "booking_signal": booking_signal,
                    "booking_active": booking_active,
                    "opt_out_in_batch": opt_out_in_batch,
                },
            )
        else:
            legacy._record_decision_trace(
                conversation,
                {
                    "stage": "routing",
                    "decision": "muted_skip",
                    "reason": "muted",
                    "state": conversation.state,
                    "booking_signal": booking_signal,
                    "booking_active": booking_active,
                    "opt_out_in_batch": opt_out_in_batch,
                },
            )
            db.commit()
            return (
                WebhookResponse(
                    success=True,
                    message="Bot muted, forwarded to topic"
                    if conversation.telegram_topic_id
                    else "Bot muted",
                    conversation_id=conversation.id,
                    bot_response=None,
                ),
                batch_messages,
                reengage_override,
            )

    return None, batch_messages, reengage_override


def _handle_opt_out_mute_gate(
    *,
    db: Session,
    client_id,
    conversation: Conversation,
    saved_message: Message | None,
    opt_out_in_batch: bool,
    booking_signal: bool,
    now: datetime,
    send_and_save,
) -> WebhookResponse | None:
    from . import _legacy as legacy

    if (
        conversation.state != legacy.ConversationState.BOT_ACTIVE.value
        or not opt_out_in_batch
        or booking_signal
    ):
        return None

    mute_first, mute_second = legacy.get_mute_settings(db, client_id)
    if conversation.no_count == 0:
        conversation.bot_muted_until = now + timedelta(minutes=mute_first)
        conversation.no_count = 1
        bot_response = legacy.MSG_MUTED_TEMP
        trace_decision = "muted_first"
    else:
        conversation.bot_muted_until = now + timedelta(hours=mute_second)
        conversation.no_count += 1
        bot_response = legacy.MSG_MUTED_LONG
        trace_decision = "muted_second"
    legacy._record_decision_trace(
        conversation,
        {
            "stage": "rejection",
            "decision": trace_decision,
            "state": conversation.state,
            "no_count": conversation.no_count,
        },
    )
    legacy._record_message_decision_meta(
        saved_message,
        action="rejection",
        intent="opt_out",
        source="opt_out",
        fast_intent=False,
    )
    bot_response, sent = send_and_save(bot_response, allow_quiet_hours=False)
    result_message = (
        f"Muted (opt-out #{conversation.no_count})" if sent else "Opt-out response failed"
    )
    db.commit()
    return WebhookResponse(
        success=True,
        message=result_message,
        conversation_id=conversation.id,
        bot_response=bot_response,
    )
