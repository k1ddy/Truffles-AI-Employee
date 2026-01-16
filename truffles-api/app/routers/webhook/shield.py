"""Behavioral shield helpers (spam/toxic filtering)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Conversation, Message, User
from app.schemas.webhook import WebhookResponse
from app.services.ai_service import normalize_for_matching


def _get_shield_context(context: dict) -> dict:
    from . import _legacy as legacy

    shield = context.get(legacy.SHIELD_CONTEXT_KEY) if isinstance(context, dict) else None
    if not isinstance(shield, dict):
        return {legacy.SHIELD_RECENT_KEY: [], legacy.SHIELD_LAST_TEXT_KEY: None}
    recent = shield.get(legacy.SHIELD_RECENT_KEY)
    cleaned: list[float] = []
    if isinstance(recent, list):
        for value in recent:
            try:
                cleaned.append(float(value))
            except (TypeError, ValueError):
                continue
    cleaned.sort()
    last_text = shield.get(legacy.SHIELD_LAST_TEXT_KEY) if isinstance(shield, dict) else None
    return {legacy.SHIELD_RECENT_KEY: cleaned, legacy.SHIELD_LAST_TEXT_KEY: last_text}


def _set_shield_context(context: dict, shield: dict) -> dict:
    from . import _legacy as legacy

    context = dict(context)
    recent = shield.get(legacy.SHIELD_RECENT_KEY)
    last_text = shield.get(legacy.SHIELD_LAST_TEXT_KEY)
    if recent or last_text:
        context[legacy.SHIELD_CONTEXT_KEY] = shield
    else:
        context.pop(legacy.SHIELD_CONTEXT_KEY, None)
    return context


def _update_shield_context(
    *,
    context: dict,
    message_text: str,
    metadata,
    now: datetime,
) -> tuple[dict, dict]:
    from . import _legacy as legacy

    shield_context = _get_shield_context(context)
    previous_text = shield_context.get(legacy.SHIELD_LAST_TEXT_KEY)
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
        for ts in shield_context.get(legacy.SHIELD_RECENT_KEY, [])
        if (now_ts - ts) <= legacy.SHIELD_SPAM_WINDOW_SECONDS
    ]
    recent.append(now_ts)
    shield_context[legacy.SHIELD_RECENT_KEY] = recent[-(legacy.SHIELD_SPAM_MAX_MESSAGES + 2) :]
    shield_context[legacy.SHIELD_LAST_TEXT_KEY] = normalized_text
    context = _set_shield_context(context, shield_context)
    return context, {"previous_text": previous_text, "normalized_text": normalized_text, "recent": recent}


def _compute_shield_flags(
    *,
    message_text: str,
    normalized_text: str,
    previous_text: str | None,
    recent: list[float],
) -> tuple[bool, bool, bool, bool]:
    from . import _legacy as legacy

    is_short = len(message_text.strip()) <= legacy.SHIELD_SHORT_MESSAGE_LEN
    is_repeat = bool(normalized_text and previous_text and normalized_text == previous_text)
    is_spam_burst = (
        len(recent) > legacy.SHIELD_SPAM_MAX_MESSAGES
        and (recent[-1] - recent[0]) <= legacy.SHIELD_SPAM_WINDOW_SECONDS
        and (is_short or is_repeat)
    )
    too_long = len(message_text) > legacy.SHIELD_MAX_MESSAGE_LENGTH
    return is_short, is_repeat, is_spam_burst, too_long


def _is_toxic_message(message_text: str) -> bool:
    from . import _legacy as legacy

    return any(pattern.search(message_text) for pattern in legacy.SHIELD_TOXIC_PATTERNS)


def _is_nonsense_message(message_text: str | None) -> bool:
    from . import _legacy as legacy

    return not legacy.SHIELD_MEANINGFUL_PATTERN.search(message_text or "")


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
    skip_persist: bool,
) -> WebhookResponse | None:
    from . import _legacy as legacy

    context = legacy._get_conversation_context(conversation)
    context, shield_state = _update_shield_context(
        context=context,
        message_text=message_text,
        metadata=metadata,
        now=now,
    )
    previous_text = shield_state.get("previous_text")
    normalized_text = shield_state.get("normalized_text") or ""
    recent = shield_state.get("recent") or []
    legacy._set_conversation_context(conversation, context)

    is_short, is_repeat, is_spam_burst, too_long = _compute_shield_flags(
        message_text=message_text,
        normalized_text=normalized_text,
        previous_text=previous_text,
        recent=recent,
    )
    if is_spam_burst or too_long:
        reason = "spam" if is_spam_burst else "too_long"
        router_shield_meta = legacy._set_router_observability(
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
        legacy._record_decision_trace(conversation, trace_payload)
        if saved_message:
            legacy._update_message_decision_metadata(
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
    if (is_toxic or is_nonsense) and conversation.state == legacy.ConversationState.BOT_ACTIVE.value:
        reason = "toxic" if is_toxic else "nonsense"
        legacy._record_decision_trace(
            conversation,
            {
                "stage": "shield",
                "decision": "escalate",
                "reason": reason,
            },
        )
        if saved_message:
            legacy._update_message_decision_metadata(
                saved_message,
                {
                    "action": "escalate",
                    "intent": "shield",
                    "source": "shield",
                    "shield_reason": reason,
                },
            )
        bot_response = legacy.MSG_ESCALATED
        result_message = "Shield escalation"
        if not skip_persist and conversation.state == legacy.ConversationState.BOT_ACTIVE.value:
            record_escalation_metric("shield")
            esc_result = legacy.escalate_to_pending(
                db=db,
                conversation=conversation,
                user_message=message_text,
                trigger_type="shield",
                trigger_value=reason,
            )
            if esc_result.ok:
                handover = esc_result.value
                telegram_sent = legacy.send_telegram_notification(
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
