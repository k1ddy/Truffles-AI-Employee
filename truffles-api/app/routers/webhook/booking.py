"""Booking state machine helpers (expected_reply_type, slot validators)."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

BOOKING_SLOT_ORDER = ("service", "datetime", "name")


def _get_booking_context(context: dict) -> dict:
    booking = context.get("booking") if isinstance(context, dict) else None
    if isinstance(booking, dict):
        return dict(booking)
    return {}


def _set_booking_context(context: dict, booking: dict) -> dict:
    context = dict(context)
    context["booking"] = booking
    return context


def _set_service_hint(context: dict, service: str, now: datetime) -> dict:
    from . import _legacy as legacy

    context = dict(context)
    context[legacy.SERVICE_HINT_KEY] = service
    context[legacy.SERVICE_HINT_AT_KEY] = now.isoformat()
    return context


def _clear_service_hint(context: dict) -> dict:
    from . import _legacy as legacy

    context = dict(context)
    context.pop(legacy.SERVICE_HINT_KEY, None)
    context.pop(legacy.SERVICE_HINT_AT_KEY, None)
    return context


def _get_recent_service_hint(context: dict, now: datetime) -> str | None:
    from . import _legacy as legacy

    if not isinstance(context, dict):
        return None
    value = context.get(legacy.SERVICE_HINT_KEY)
    if not value:
        return None
    timestamp_raw = context.get(legacy.SERVICE_HINT_AT_KEY)
    if not timestamp_raw:
        return None
    try:
        timestamp = datetime.fromisoformat(timestamp_raw)
    except (TypeError, ValueError):
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    if (now - timestamp) > timedelta(minutes=legacy.SERVICE_HINT_WINDOW_MINUTES):
        return None
    return str(value).strip() or None


def _is_blocked_slot_message(message_text: str) -> bool:
    from . import _legacy as legacy

    return legacy.is_opt_out_message(message_text) or legacy.is_frustration_message(message_text)


def _is_noise_slot_message(message_text: str) -> bool:
    from . import _legacy as legacy

    return (
        legacy.is_low_signal_message(message_text)
        or legacy.is_acknowledgement_message(message_text)
        or legacy.is_greeting_message(message_text)
        or legacy.is_thanks_message(message_text)
        or legacy.is_bot_status_question(message_text)
        or legacy.is_human_request_message(message_text)
    )


def _clean_name_candidate(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-zА-Яа-яЁё\s-]", " ", value or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _validate_service_slot(
    message_text: str,
    *,
    allow_freeform: bool,
    client_slug: str | None,
) -> str | None:
    if _is_blocked_slot_message(message_text):
        return None
    from . import _legacy as legacy

    extracted = legacy._extract_service_hint(message_text, client_slug)
    if extracted:
        return extracted
    return None


def _validate_datetime_slot(
    message_text: str,
    *,
    allow_freeform: bool,
    client_slug: str | None,
) -> str | None:
    if _is_blocked_slot_message(message_text):
        return None
    from . import _legacy as legacy

    extracted = legacy._extract_datetime(message_text)
    if extracted:
        return extracted
    return None


def _validate_name_slot(
    message_text: str,
    *,
    allow_freeform: bool,
    client_slug: str | None,
) -> str | None:
    if _is_blocked_slot_message(message_text):
        return None
    if _is_noise_slot_message(message_text):
        return None
    from . import _legacy as legacy

    if legacy._extract_service_hint(message_text, client_slug) or legacy._extract_datetime(message_text):
        return None
    name_match = legacy.NAME_PATTERN.search(message_text)
    if name_match:
        candidate = name_match.group(1)
    elif not allow_freeform:
        return None
    else:
        candidate = message_text
    cleaned = _clean_name_candidate(candidate)
    if not cleaned:
        return None
    if any(char.isdigit() for char in cleaned):
        return None
    normalized = legacy._normalize_text(cleaned)
    tokens = normalized.split()
    if not tokens or len(tokens) > 3:
        return None
    if any(len(token) < 2 for token in tokens):
        return None
    if all(token in legacy.NAME_NOISE_TOKENS for token in tokens):
        return None
    return cleaned


BOOKING_SLOT_VALIDATORS = {
    "service": _validate_service_slot,
    "datetime": _validate_datetime_slot,
    "name": _validate_name_slot,
}


def _expected_reply_for_booking_question(last_question: str | None) -> str | None:
    from . import _legacy as legacy

    if last_question == "service":
        return legacy.EXPECTED_REPLY_SERVICE
    if last_question == "datetime":
        return legacy.EXPECTED_REPLY_TIME
    if last_question == "name":
        return legacy.EXPECTED_REPLY_NAME
    return None


def _match_expected_reply(
    *,
    expected_reply_type: str | None,
    message_text: str,
    client_slug: str | None,
) -> tuple[bool, str | None]:
    if not expected_reply_type or not message_text:
        return False, None
    from . import _legacy as legacy

    if expected_reply_type == legacy.EXPECTED_REPLY_SERVICE:
        value = _validate_service_slot(message_text, allow_freeform=True, client_slug=client_slug)
    elif expected_reply_type == legacy.EXPECTED_REPLY_TIME:
        value = _validate_datetime_slot(message_text, allow_freeform=True, client_slug=client_slug)
    elif expected_reply_type == legacy.EXPECTED_REPLY_NAME:
        value = _validate_name_slot(message_text, allow_freeform=True, client_slug=client_slug)
    else:
        return False, None
    if not value:
        return False, None
    return True, value


def _apply_expected_reply_slot(context: dict, *, expected_reply_type: str | None, value: str) -> dict:
    if not expected_reply_type or not value:
        return context
    from . import _legacy as legacy

    if expected_reply_type == legacy.EXPECTED_REPLY_SERVICE:
        slot_key = "service"
    elif expected_reply_type == legacy.EXPECTED_REPLY_TIME:
        slot_key = "datetime"
    elif expected_reply_type == legacy.EXPECTED_REPLY_NAME:
        slot_key = "name"
    else:
        return context
    booking_state = _get_booking_context(context)
    if not isinstance(booking_state, dict) or not booking_state:
        return context
    if booking_state.get(slot_key):
        return context
    last_question = booking_state.get("last_question")
    if not booking_state.get("active") and last_question != slot_key:
        return context
    booking_state = dict(booking_state)
    booking_state[slot_key] = value
    return _set_booking_context(context, booking_state)


def _is_booking_related_message(
    message_text: str,
    client_slug: str | None,
    *,
    allow_name: bool = True,
    allow_service: bool = True,
) -> bool:
    if not message_text:
        return False
    from . import _legacy as legacy

    if legacy._is_booking_request(message_text):
        return True
    refusal_flags = legacy.detect_refusal_flags(message_text)
    if refusal_flags.get("name") or refusal_flags.get("phone"):
        return True
    if allow_service and legacy._extract_service_hint(message_text, client_slug):
        return True
    if legacy._extract_datetime(message_text):
        return True
    if allow_name and _validate_name_slot(message_text, allow_freeform=True, client_slug=client_slug):
        return True
    return False


def _select_last_non_booking_message(messages: list[str], *, client_slug: str | None) -> str | None:
    for message in reversed(messages or []):
        if not message:
            continue
        if _is_booking_related_message(message, client_slug, allow_name=False, allow_service=False):
            continue
        return message
    return None


def _select_expected_reply_message(
    messages: list[str],
    *,
    expected_reply_type: str | None,
    client_slug: str | None,
) -> str | None:
    if not messages or not expected_reply_type:
        return None
    for message in reversed(messages or []):
        if not message:
            continue
        matched, _ = _match_expected_reply(
            expected_reply_type=expected_reply_type,
            message_text=message,
            client_slug=client_slug,
        )
        if matched:
            return message
    return None


def _apply_booking_slot(
    booking: dict,
    slot_key: str,
    message_text: str,
    *,
    allow_freeform: bool,
    client_slug: str | None,
) -> dict:
    if booking.get(slot_key):
        return booking
    validator = BOOKING_SLOT_VALIDATORS.get(slot_key)
    if not validator:
        return booking
    value = validator(message_text, allow_freeform=allow_freeform, client_slug=client_slug)
    if value:
        booking[slot_key] = value
    return booking


__all__ = [
    "BOOKING_SLOT_ORDER",
    "BOOKING_SLOT_VALIDATORS",
    "_apply_booking_slot",
    "_apply_expected_reply_slot",
    "_clean_name_candidate",
    "_clear_service_hint",
    "_expected_reply_for_booking_question",
    "_get_booking_context",
    "_get_recent_service_hint",
    "_is_blocked_slot_message",
    "_is_booking_related_message",
    "_is_noise_slot_message",
    "_match_expected_reply",
    "_select_expected_reply_message",
    "_select_last_non_booking_message",
    "_set_booking_context",
    "_set_service_hint",
    "_validate_datetime_slot",
    "_validate_name_slot",
    "_validate_service_slot",
]
