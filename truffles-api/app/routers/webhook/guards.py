"""Intent-queue and clarify-guard helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core import DialogStateService
from app.logging_config import get_logger
from app.models import Conversation, Message, User
from app.routers.webhook.booking import _get_booking_context, _set_booking_context
from app.routers.webhook.context_manager import (
    _get_context_manager,
    _get_conversation_context,
    _get_reengage_confirmation,
    _is_reengage_confirmation_active,
    _record_context_manager_decision,
    _reset_low_confidence_retry,
    _set_context_manager,
    _set_conversation_context,
    _set_reengage_confirmation,
    _update_compact_summary,
)
from app.routers.webhook.guard_runtime import (
    MSG_FACT_GUARD_CLARIFY,
    MSG_MUTED_LONG,
    MSG_MUTED_TEMP,
    MSG_REENGAGE_CONFIRM,
    MSG_REENGAGE_DECLINED,
    MULTI_INTENT_LABELS,
    SESSION_TIMEOUT_HOURS,
    _canonicalize_guard_metadata_action,
    _coerce_batch_messages,
    get_mute_settings,
)
from app.routers.webhook.runtime_primitives import CLARIFY_MAX_ATTEMPTS, MSG_ESCALATED
from app.routers.webhook.trace import (
    _record_decision_trace,
    _record_message_decision_meta,
    _retain_decision_trace,
    _set_router_observability,
    _update_message_decision_metadata,
)
from app.schemas.webhook import WebhookResponse
from app.services.ai_service import (
    is_acknowledgement_message,
    is_low_signal_message,
    normalize_for_matching,
)
from app.services.handover_owner_service import (
    ActiveHandoverReuseRuntimeHooks,
    _reuse_active_handover,
    escalate_to_pending,
    get_active_handover,
    send_telegram_notification,
)
from app.services.human_lock_service import get_active_human_lock, normalize_remote_jid
from app.services.intent_service import is_opt_out_message
from app.services.message_service import save_message
from app.services.sla_runtime_service import (
    SLA_RUNTIME_CONTEXT_KEY,
    SLA_RUNTIME_MODE_COLLECT_ONLY,
    is_collect_only_runtime_active,
)
from app.services.state_machine import ConversationState
from app.services.state_service import transition_state

logger = get_logger("webhook")

DECISION_TRACE_KEY = "decision_trace"
_DIALOG_STATE_SERVICE = DialogStateService()


def _canonical_booking_resume_signal(
    *,
    booking_active: bool,
    expected_reply_shortcircuit: bool = False,
    reengage_confirmation: dict | None = None,
) -> bool:
    if expected_reply_shortcircuit:
        return True
    if booking_active:
        return True
    if isinstance(reengage_confirmation, dict):
        stored_messages = reengage_confirmation.get("booking_messages")
        return bool(isinstance(stored_messages, list) and stored_messages)
    return False



def _is_human_lock_trace_entry(item: dict, *, lock_until: str | None = None) -> bool:
    if not isinstance(item, dict):
        return False
    if item.get("stage") != "routing":
        return False
    if item.get("decision") != "human_lock_silent":
        return False
    if item.get("reason") != "human_lock":
        return False
    if lock_until and item.get("lock_until") not in {None, lock_until}:
        return False
    return True


def _ensure_human_lock_trace_persisted(
    *,
    conversation: Conversation,
    trace_payload: dict,
) -> bool:
    context = _get_conversation_context(conversation)
    existing_trace = context.get(DECISION_TRACE_KEY)
    if isinstance(existing_trace, list):
        trace_list = [item for item in existing_trace if isinstance(item, dict)]
    elif isinstance(existing_trace, dict):
        trace_list = [existing_trace]
    else:
        trace_list = []

    if any(
        _is_human_lock_trace_entry(item, lock_until=trace_payload.get("lock_until"))
        for item in trace_list
    ):
        return True

    fallback_trace = dict(trace_payload)
    fallback_trace["recorded_at"] = datetime.now(timezone.utc).isoformat()
    trace_list.append(fallback_trace)
    context[DECISION_TRACE_KEY] = _retain_decision_trace(trace_list)
    _set_conversation_context(conversation, context)
    return True


def _get_intent_queue(context: dict) -> list[str]:
    return _DIALOG_STATE_SERVICE.get_intent_queue(context)


def _set_intent_queue(context: dict, queue: list[str] | None) -> dict:
    return _DIALOG_STATE_SERVICE.set_intent_queue(context, queue=queue)


def _format_multi_intent_followup(primary: str, secondary: list[str]) -> str | None:
    if not primary:
        return None

    labels = []
    for intent in secondary:
        label = MULTI_INTENT_LABELS.get(intent)
        if label:
            labels.append(label)
    if not labels:
        return "Есть ещё вопрос — уточните, пожалуйста."
    label_text = ", ".join(labels)
    if primary == "booking":
        return f"По {label_text} отвечу после записи."
    return f"Ещё был вопрос по {label_text}. Уточните, пожалуйста."


def _match_intent_choice_from_text(intent_queue: list[str], message_text: str) -> str | None:

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
        label = MULTI_INTENT_LABELS.get(intent)
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

    labels = []
    for intent in intent_queue:
        label = MULTI_INTENT_LABELS.get(intent)
        if label:
            labels.append(f"по {label}")
    if not labels:
        return "Что разобрать дальше?"
    label_text = ", ".join(labels)
    return f"Что разобрать дальше: [{label_text}]?"


def _get_clarify_attempt_state(manager: dict, intent: str) -> tuple[int, str | None]:
    return _DIALOG_STATE_SERVICE.get_clarify_attempt_state(manager, intent=intent)


def _set_clarify_attempt(manager: dict, intent: str, count: int, now: datetime) -> dict:
    return _DIALOG_STATE_SERVICE.set_clarify_attempt_state(
        manager,
        intent=intent,
        count=count,
        now=now,
    )


def _should_escalate_for_clarify(manager: dict, intent: str) -> bool:

    count, _ = _get_clarify_attempt_state(manager, intent)
    return count >= CLARIFY_MAX_ATTEMPTS


def _booking_clarify_guard_reason(
    *,
    booking_interrupt_info: bool,
    basic_info_message: bool,
    session_memory_reset_reason: str | None,
    memory_expected_reply_type: str | None,
    message_text: str | None,
    booking_slot_signal: bool,
) -> str | None:
    if booking_interrupt_info:
        return "booking_interrupt_info"
    if session_memory_reset_reason:
        return f"session_memory_{session_memory_reset_reason}"
    if memory_expected_reply_type:
        return "session_memory_expected_reply"
    if basic_info_message:
        return "basic_info_message"
    if booking_slot_signal:
        return "booking_slot_signal"
    if message_text and (
        is_low_signal_message(message_text)
        or is_acknowledgement_message(message_text)
    ):
        return "low_signal"
    return None


def _register_clarify_attempt(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    intent: str,
    now: datetime,
    reason: str,
) -> int:

    context = _get_conversation_context(conversation)
    manager = _get_context_manager(context)
    count, _ = _get_clarify_attempt_state(manager, intent)
    count += 1
    manager = _set_clarify_attempt(manager, intent, count, now)
    context = _set_context_manager(context, manager)
    _set_conversation_context(conversation, context)
    attempt_payload = {"intent": intent, "count": count, "last_at": now.isoformat()}
    _record_context_manager_decision(
        conversation,
        saved_message,
        decision="clarify_attempt",
        updates={"clarify_attempt": attempt_payload, "clarify_reason": reason},
    )
    if count >= CLARIFY_MAX_ATTEMPTS:
        _update_compact_summary(
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

    bot_response = MSG_ESCALATED
    _reset_low_confidence_retry(conversation)
    result_message = f"{source} clarify limit escalation"

    _, reused, telegram_sent = _reuse_active_handover(
        db=db,
        conversation=conversation,
        user=user,
        message=message_text,
        source=source,
        intent=escalation_intent,
        hooks=ActiveHandoverReuseRuntimeHooks(
            get_active_handover=get_active_handover,
            transition_state=transition_state,
            send_telegram_notification=send_telegram_notification,
            record_decision_trace=_record_decision_trace,
        ),
    )
    if reused:
        result_message = f"{source} clarify limit reuse, telegram={'sent' if telegram_sent else 'failed'}"
    elif conversation.state == ConversationState.BOT_ACTIVE.value and allow_handover:
        result = escalate_to_pending(
            db=db,
            conversation=conversation,
            user_message=message_text,
            trigger_type="intent",
            trigger_value=escalation_intent,
        )
        if result.ok:
            handover = result.value
            telegram_sent = send_telegram_notification(
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

    _record_decision_trace(
        conversation,
        {
            "stage": source,
            "decision": escalation_intent,
            "intent": escalation_intent,
            "state": conversation.state,
        },
    )
    _record_message_decision_meta(
        saved_message,
        action="handoff",
        intent=escalation_intent,
        source=source,
        fast_intent=False,
    )
    if saved_message:
        _update_message_decision_metadata(saved_message, {"clarify_limit": True})
    if finalize_response:
        bot_response = finalize_response(bot_response)
    save_message(
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

    if not previous_last_message_at:
        return
    last_seen = previous_last_message_at
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    time_since_last = now - last_seen
    if time_since_last > timedelta(hours=SESSION_TIMEOUT_HOURS):
        conversation.bot_status = "active"
        conversation.bot_muted_until = None
        conversation.no_count = 0
        _set_conversation_context(conversation, {})
        logger.info(f"Session reset: {time_since_last} since last message")


def _handle_reengage_and_mute_gate(
    *,
    db: Session,
    client_id,
    client_slug: str,
    conversation: Conversation,
    remote_jid: str | None,
    message_text: str,
    batch_messages: list[str] | None,
    expected_reply_shortcircuit: bool,
    now: datetime,
    send_and_save,
    saved_message=None,
) -> tuple[WebhookResponse | None, list[str], bool]:
    from app.services.ai_service import classify_confirmation


    batch_messages = _coerce_batch_messages(message_text, batch_messages)
    signal_messages = list(batch_messages)
    opt_out_in_batch = any(is_opt_out_message(msg) for msg in signal_messages)

    context = _get_conversation_context(conversation)
    booking_state = _get_booking_context(context)
    booking_active = bool(booking_state.get("active"))
    reengage_override = False
    normalized_remote_jid = normalize_remote_jid(remote_jid)
    reengage_confirmation = _get_reengage_confirmation(context)
    booking_signal = _canonical_booking_resume_signal(
        booking_active=booking_active,
        expected_reply_shortcircuit=expected_reply_shortcircuit,
        reengage_confirmation=reengage_confirmation,
    )

    if (
        conversation.state == ConversationState.BOT_ACTIVE.value
        and normalized_remote_jid
    ):
        human_lock = get_active_human_lock(
            db,
            client_id=client_id,
            remote_jid=normalized_remote_jid,
            conversation_id=conversation.id,
            now=now,
        )
        if human_lock:
            lock_until = human_lock.lock_until
            if lock_until and lock_until.tzinfo is None:
                lock_until = lock_until.replace(tzinfo=timezone.utc)
            trace_payload = {
                "stage": "routing",
                "decision": "human_lock_silent",
                "reason": "human_lock",
                "state": conversation.state,
                "remote_jid": normalized_remote_jid,
                "lock_until": lock_until.isoformat() if lock_until else None,
            }
            _record_decision_trace(conversation, trace_payload)
            trace_persisted = _ensure_human_lock_trace_persisted(
                conversation=conversation,
                trace_payload=trace_payload,
            )
            if saved_message is not None:
                _record_message_decision_meta(
                    saved_message,
                    action=_canonicalize_guard_metadata_action("human_lock_silent"),
                    intent=None,
                    source="routing",
                    fast_intent=False,
                )
                _update_message_decision_metadata(
                    saved_message,
                    {
                        "human_lock": {
                            "active": True,
                            "until": lock_until.isoformat() if lock_until else None,
                            "source": getattr(human_lock, "source", None),
                            "reason": getattr(human_lock, "reason", None),
                            "locked_by": getattr(human_lock, "locked_by_name", None),
                        },
                        "human_lock_trace": {
                            "stage": trace_payload["stage"],
                            "decision": trace_payload["decision"],
                            "reason": trace_payload["reason"],
                            "lock_until": trace_payload["lock_until"],
                            "persisted": bool(trace_persisted),
                        },
                    },
                )
            db.commit()
            return (
                WebhookResponse(
                    success=True,
                    message="Human lock active, message forwarded",
                    conversation_id=conversation.id,
                    bot_response=None,
                ),
                batch_messages,
                reengage_override,
            )

    if conversation.state == ConversationState.BOT_ACTIVE.value:
        if reengage_confirmation:
            if not _is_reengage_confirmation_active(reengage_confirmation, now):
                context = _set_reengage_confirmation(context, None)
                _set_conversation_context(conversation, context)
            else:
                decision = classify_confirmation(message_text)
                if decision == "yes":
                    context = _set_reengage_confirmation(context, None)
                    _set_conversation_context(conversation, context)
                    conversation.bot_status = "active"
                    conversation.bot_muted_until = None
                    conversation.no_count = 0
                    reengage_override = True
                    booking_signal = _canonical_booking_resume_signal(
                        booking_active=booking_active,
                        expected_reply_shortcircuit=expected_reply_shortcircuit,
                        reengage_confirmation=reengage_confirmation,
                    )
                    _record_decision_trace(
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
                    context = _set_reengage_confirmation(context, None)
                    _set_conversation_context(conversation, context)
                    mute_first, mute_second = get_mute_settings(db, client_id)
                    if conversation.no_count == 0:
                        conversation.bot_muted_until = now + timedelta(minutes=mute_first)
                        conversation.no_count = 1
                    else:
                        conversation.bot_muted_until = now + timedelta(hours=mute_second)
                        conversation.no_count += 1
                    _record_decision_trace(
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
                    bot_response = MSG_REENGAGE_DECLINED
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
                    context = _set_reengage_confirmation(context, reengage_confirmation)
                    _set_conversation_context(conversation, context)
                    _record_decision_trace(
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
                    bot_response = MSG_REENGAGE_CONFIRM
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

    if conversation.state == ConversationState.BOT_ACTIVE.value and opt_out_in_batch and booking_signal:
        confirmation_payload = {
            "asked_at": now.isoformat(),
            "booking_messages": signal_messages,
        }
        context = _set_reengage_confirmation(context, confirmation_payload)
        if booking_active:
            booking_state["active"] = False
            context = _set_booking_context(context, booking_state)
        _set_conversation_context(conversation, context)
        _record_decision_trace(
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
        bot_response = MSG_REENGAGE_CONFIRM
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
            _record_decision_trace(
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
            _record_decision_trace(
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


def _handle_post_debounce_muted_state_gate(
    *,
    conversation: Conversation,
    message_text: str,
    batch_messages: list[str] | None,
    client_slug: str,
    now: datetime,
) -> WebhookResponse | None:

    is_muted = conversation.bot_status == "muted" or (
        conversation.bot_muted_until and conversation.bot_muted_until > now
    )
    if not is_muted:
        return None

    signal_messages = _coerce_batch_messages(message_text, batch_messages)
    opt_out_in_batch = any(is_opt_out_message(msg) for msg in signal_messages)
    context = _get_conversation_context(conversation)
    booking_active = bool(_get_booking_context(context).get("active"))
    reengage_confirmation = _get_reengage_confirmation(context)
    booking_signal = _canonical_booking_resume_signal(
        booking_active=booking_active,
        reengage_confirmation=reengage_confirmation,
    )

    if reengage_confirmation and _is_reengage_confirmation_active(reengage_confirmation, now):
        conversation.bot_status = "active"
        conversation.bot_muted_until = None
        conversation.no_count = 0
        return None
    if (booking_signal or booking_active) and not opt_out_in_batch:
        conversation.bot_status = "active"
        conversation.bot_muted_until = None
        conversation.no_count = 0
        return None

    _record_decision_trace(
        conversation,
        {
            "stage": "routing",
            "decision": "muted_skip_after_debounce",
            "state": conversation.state,
            "booking_signal": booking_signal,
            "booking_active": booking_active,
            "opt_out_in_batch": opt_out_in_batch,
        },
    )
    return WebhookResponse(
        success=True,
        message="Bot muted (after debounce), forwarded to topic"
        if conversation.telegram_topic_id
        else "Bot muted (after debounce)",
        conversation_id=conversation.id,
        bot_response=None,
    )


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

    if (
        conversation.state != ConversationState.BOT_ACTIVE.value
        or not opt_out_in_batch
        or booking_signal
    ):
        return None

    mute_first, mute_second = get_mute_settings(db, client_id)
    if conversation.no_count == 0:
        conversation.bot_muted_until = now + timedelta(minutes=mute_first)
        conversation.no_count = 1
        bot_response = MSG_MUTED_TEMP
        trace_decision = "muted_first"
    else:
        conversation.bot_muted_until = now + timedelta(hours=mute_second)
        conversation.no_count += 1
        bot_response = MSG_MUTED_LONG
        trace_decision = "muted_second"
    _record_decision_trace(
        conversation,
        {
            "stage": "rejection",
            "decision": trace_decision,
            "state": conversation.state,
            "no_count": conversation.no_count,
        },
    )
    _record_message_decision_meta(
        saved_message,
        action=_canonicalize_guard_metadata_action("rejection"),
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


def _handle_sla_collect_only_gate(
    *,
    db: Session,
    conversation: Conversation,
    saved_message: Message | None,
    now: datetime,
    send_and_save,
) -> WebhookResponse | None:

    if conversation.state != ConversationState.BOT_ACTIVE.value:
        return None

    context = _get_conversation_context(conversation)
    runtime = context.get(SLA_RUNTIME_CONTEXT_KEY) if isinstance(context, dict) else None
    if not isinstance(runtime, dict):
        return None

    if runtime.get("mode") == SLA_RUNTIME_MODE_COLLECT_ONLY and not is_collect_only_runtime_active(
        context,
        now=now,
    ):
        context.pop(SLA_RUNTIME_CONTEXT_KEY, None)
        _set_conversation_context(conversation, context)
        return None

    if not is_collect_only_runtime_active(context, now=now):
        return None

    router_pending_meta = _set_router_observability(
        saved_message,
        eligible=False,
        reason="sla_collect_only",
    )
    trace_payload = {
        "stage": "routing",
        "decision": "sla_collect_only",
        "reason": runtime.get("reason_code"),
        "state": conversation.state,
        "sla_severity": runtime.get("severity"),
        "sla_profile_id": runtime.get("profile_id"),
        "sla_profile_version": runtime.get("profile_version"),
    }
    trace_payload.update(router_pending_meta)
    _record_decision_trace(conversation, trace_payload)
    _record_message_decision_meta(
        saved_message,
        action="collect",
        intent="sla_collect_only",
        source="sla_profile",
        fast_intent=False,
    )
    if saved_message:
        _update_message_decision_metadata(
            saved_message,
            {
                "sla_runtime_mode": SLA_RUNTIME_MODE_COLLECT_ONLY,
                "sla_runtime_reason": runtime.get("reason_code"),
                "sla_runtime_severity": runtime.get("severity"),
                "sla_runtime_profile_id": runtime.get("profile_id"),
                "sla_runtime_profile_version": runtime.get("profile_version"),
            },
        )
    bot_response, sent = send_and_save(MSG_FACT_GUARD_CLARIFY)
    result_message = (
        "SLA collect_only guard response sent"
        if sent
        else "SLA collect_only guard response failed"
    )
    db.commit()
    return WebhookResponse(
        success=True,
        message=result_message,
        conversation_id=conversation.id,
        bot_response=bot_response,
    )
