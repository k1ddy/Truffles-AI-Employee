"""Behavioral shield helpers (spam/toxic filtering)."""

from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Conversation, Message, User
from app.routers.webhook.context_manager import _get_conversation_context, _set_conversation_context
from app.routers.webhook.runtime_primitives import MSG_ESCALATED
from app.routers.webhook.trace import (
    _record_decision_trace,
    _set_router_observability,
    _update_message_decision_metadata,
)
from app.schemas.webhook import WebhookResponse
from app.services.ai_service import normalize_for_matching
from app.services.handover_owner_service import escalate_to_pending, send_telegram_notification
from app.services.state_machine import ConversationState

SHIELD_CONTEXT_KEY = "shield"
SHIELD_RECENT_KEY = "recent_messages"
SHIELD_LAST_TEXT_KEY = "last_text"
SHIELD_SPAM_WINDOW_SECONDS = 5.0
SHIELD_SPAM_MAX_MESSAGES = 3
SHIELD_MAX_MESSAGE_LENGTH = 1000
SHIELD_SHORT_MESSAGE_LEN = 12
SHIELD_TOXIC_PATTERNS = [
    re.compile(r"\b(хуй|пизд|пидор|еба|сука|нахуй|убью|иди\s+на\s+хуй|бля[тд])", re.IGNORECASE),
]
SHIELD_MEANINGFUL_PATTERN = re.compile(r"[A-Za-zА-Яа-я0-9]{2,}")


def _get_shield_context(context: dict) -> dict:
    shield = context.get(SHIELD_CONTEXT_KEY) if isinstance(context, dict) else None
    if not isinstance(shield, dict):
        return {SHIELD_RECENT_KEY: [], SHIELD_LAST_TEXT_KEY: None}
    recent = shield.get(SHIELD_RECENT_KEY)
    cleaned: list[float] = []
    if isinstance(recent, list):
        for value in recent:
            try:
                cleaned.append(float(value))
            except (TypeError, ValueError):
                continue
    cleaned.sort()
    last_text = shield.get(SHIELD_LAST_TEXT_KEY) if isinstance(shield, dict) else None
    return {SHIELD_RECENT_KEY: cleaned, SHIELD_LAST_TEXT_KEY: last_text}


def _set_shield_context(context: dict, shield: dict) -> dict:
    context = dict(context)
    recent = shield.get(SHIELD_RECENT_KEY)
    last_text = shield.get(SHIELD_LAST_TEXT_KEY)
    if recent or last_text:
        context[SHIELD_CONTEXT_KEY] = shield
    else:
        context.pop(SHIELD_CONTEXT_KEY, None)
    return context


def _update_shield_context(
    *,
    context: dict,
    message_text: str,
    metadata,
    now: datetime,
) -> tuple[dict, dict]:
    shield_context = _get_shield_context(context)
    previous_text = shield_context.get(SHIELD_LAST_TEXT_KEY)
    normalized_text = normalize_for_matching(message_text)
    msg_ts = None
    if metadata and getattr(metadata, "timestamp", None) is not None:
        try:
            msg_ts = float(metadata.timestamp)
        except (TypeError, ValueError):
            msg_ts = None
    now_ts = msg_ts if msg_ts is not None else now.timestamp()
    recent = [
        ts
        for ts in shield_context.get(SHIELD_RECENT_KEY, [])
        if (now_ts - ts) <= SHIELD_SPAM_WINDOW_SECONDS
    ]
    recent.append(now_ts)
    shield_context[SHIELD_RECENT_KEY] = recent[-(SHIELD_SPAM_MAX_MESSAGES + 2) :]
    shield_context[SHIELD_LAST_TEXT_KEY] = normalized_text
    context = _set_shield_context(context, shield_context)
    return context, {"previous_text": previous_text, "normalized_text": normalized_text, "recent": recent}


def _compute_shield_flags(
    *,
    message_text: str,
    normalized_text: str,
    previous_text: str | None,
    recent: list[float],
) -> tuple[bool, bool, bool, bool]:
    is_short = len(message_text.strip()) <= SHIELD_SHORT_MESSAGE_LEN
    is_repeat = bool(normalized_text and previous_text and normalized_text == previous_text)
    is_spam_burst = (
        len(recent) > SHIELD_SPAM_MAX_MESSAGES
        and (recent[-1] - recent[0]) <= SHIELD_SPAM_WINDOW_SECONDS
        and (is_short or is_repeat)
    )
    too_long = len(message_text) > SHIELD_MAX_MESSAGE_LENGTH
    return is_short, is_repeat, is_spam_burst, too_long


def _is_toxic_message(message_text: str) -> bool:
    return any(pattern.search(message_text) for pattern in SHIELD_TOXIC_PATTERNS)


def _is_nonsense_message(message_text: str | None) -> bool:
    return not SHIELD_MEANINGFUL_PATTERN.search(message_text or "")


def _handle_shield_gate(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message_text: str,
    metadata,
    now: datetime,
    saved_message: Message | None,
    send_and_save,
    record_escalation_metric,
    booking_active: bool = False,
    booking_wants_flow: bool = False,
    booking_slot_signal: bool = False,
    skip_persist: bool,
) -> WebhookResponse | None:
    context = _get_conversation_context(conversation)
    context, shield_state = _update_shield_context(
        context=context,
        message_text=message_text,
        metadata=metadata,
        now=now,
    )
    previous_text = shield_state.get("previous_text")
    normalized_text = shield_state.get("normalized_text") or ""
    recent = shield_state.get("recent") or []
    _set_conversation_context(conversation, context)

    is_short, is_repeat, is_spam_burst, too_long = _compute_shield_flags(
        message_text=message_text,
        normalized_text=normalized_text,
        previous_text=previous_text,
        recent=recent,
    )
    if is_spam_burst or too_long:
        reason = "spam" if is_spam_burst else "too_long"
        router_shield_meta = _set_router_observability(
            saved_message,
            eligible=False,
            reason="shield_drop",
        )
        trace_payload = {
            "stage": "shield",
            "decision": "drop",
            "reason": reason,
            "message_length": len(message_text),
            "recent_messages": len(recent),
            "is_repeat": is_repeat,
            "is_short": is_short,
        }
        trace_payload.update(router_shield_meta)
        _record_decision_trace(conversation, trace_payload)
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {
                    "action": "shield_drop",
                    "intent": "shield",
                    "source": "shield",
                    "shield_reason": reason,
                },
            )
        db.commit()
        return WebhookResponse(
            success=True,
            message="Shield drop",
            conversation_id=conversation.id,
            bot_response=None,
        )

    is_toxic = _is_toxic_message(message_text)
    is_nonsense = _is_nonsense_message(message_text)
    if is_nonsense and (booking_active or booking_wants_flow or booking_slot_signal):
        return None
    if (is_toxic or is_nonsense) and conversation.state == ConversationState.BOT_ACTIVE.value:
        reason = "toxic" if is_toxic else "nonsense"
        _record_decision_trace(
            conversation,
            {
                "stage": "shield",
                "decision": "escalate",
                "reason": reason,
            },
        )
        if saved_message:
            _update_message_decision_metadata(
                saved_message,
                {
                    "action": "escalate",
                    "intent": "shield",
                    "source": "shield",
                    "shield_reason": reason,
                },
            )
        bot_response = MSG_ESCALATED
        result_message = "Shield escalation"
        if not skip_persist and conversation.state == ConversationState.BOT_ACTIVE.value:
            record_escalation_metric("shield")
            esc_result = escalate_to_pending(
                db=db,
                conversation=conversation,
                user_message=message_text,
                trigger_type="shield",
                trigger_value=reason,
            )
            if esc_result.ok:
                handover = esc_result.value
                telegram_sent = send_telegram_notification(
                    db=db,
                    handover=handover,
                    conversation=conversation,
                    user=user,
                    message=message_text,
                )
                result_message = f"Shield escalation, telegram={'sent' if telegram_sent else 'failed'}"
            else:
                result_message = f"Shield escalation failed: {esc_result.error}"
        bot_response, sent = send_and_save(bot_response, allow_quiet_hours=False)
        if not sent:
            result_message = f"{result_message}; response_send=failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )

    return None
