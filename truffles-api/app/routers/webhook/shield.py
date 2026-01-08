"""Behavioral shield helpers (spam/toxic filtering)."""

from __future__ import annotations

from datetime import datetime

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
