"""Booking state machine helpers (expected_reply_type, slot validators)."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import dateparser
from rapidfuzz import fuzz, process

if TYPE_CHECKING:
    from app.services.demo_salon_knowledge import DemoSalonDecision

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


@lru_cache(maxsize=1)
def _load_datetime_lexicon() -> dict:
    from app.services.demo_salon_knowledge import load_yaml_truth

    truth = load_yaml_truth()
    domain_pack = truth.get("domain_pack") if isinstance(truth, dict) else None
    lexicon = domain_pack.get("datetime_lexicon") if isinstance(domain_pack, dict) else None
    return lexicon if isinstance(lexicon, dict) else {}


@lru_cache(maxsize=1)
def _build_datetime_variant_index() -> tuple[
    dict[str, str],
    set[str],
    list[tuple[tuple[str, ...], str, str]],
]:
    from . import _legacy as legacy

    lexicon = _load_datetime_lexicon()
    variant_map: dict[str, str] = {}
    canonical_set: set[str] = set()
    entries: list[tuple[tuple[str, ...], str, str]] = []

    for group_name in ("days", "dayparts"):
        group = lexicon.get(group_name)
        if not isinstance(group, dict):
            continue
        for payload in group.values():
            if not isinstance(payload, dict):
                continue
            canonical_raw = payload.get("canonical_ru")
            if not isinstance(canonical_raw, str):
                continue
            canonical = legacy._normalize_text(canonical_raw)
            if not canonical:
                continue
            canonical_set.add(canonical)
            variant_map.setdefault(canonical, canonical)
            entries.append((tuple(canonical.split()), canonical, canonical))
            for lang_key in ("ru", "kk"):
                variants = payload.get(lang_key)
                if not isinstance(variants, list):
                    continue
                for variant in variants:
                    if not isinstance(variant, str):
                        continue
                    normalized = legacy._normalize_text(variant)
                    if not normalized:
                        continue
                    variant_map[normalized] = canonical
                    entries.append((tuple(normalized.split()), canonical, normalized))

    entries.sort(key=lambda item: len(item[0]), reverse=True)
    return variant_map, canonical_set, entries


def _canonicalize_datetime_text(message_text: str) -> tuple[str, list[dict[str, Any]]]:
    from . import _legacy as legacy

    normalized = legacy._normalize_text(message_text)
    if not normalized:
        return "", []

    variant_map, canonical_set, entries = _build_datetime_variant_index()
    if not variant_map:
        return normalized, []

    tokens = normalized.split()
    matches: list[dict[str, Any]] = []
    replaced_tokens: list[str] = []
    idx = 0
    while idx < len(tokens):
        matched = False
        for variant_tokens, canonical, variant in entries:
            if not variant_tokens:
                continue
            size = len(variant_tokens)
            if idx + size <= len(tokens) and tuple(tokens[idx : idx + size]) == variant_tokens:
                replaced_tokens.append(canonical)
                matches.append({"variant": variant, "canonical": canonical, "method": "direct"})
                idx += size
                matched = True
                break
        if not matched:
            replaced_tokens.append(tokens[idx])
            idx += 1

    variants = list(variant_map.keys())
    for token_index, token in enumerate(replaced_tokens):
        if token in canonical_set or len(token) < 2:
            continue
        if any(char.isdigit() for char in token):
            continue
        match = process.extractOne(token, variants, scorer=fuzz.ratio)
        if not match:
            continue
        variant, score, _ = match
        threshold = 92 if len(token) <= 4 else 88
        if score < threshold:
            continue
        canonical = variant_map.get(variant)
        if not canonical or canonical == token:
            continue
        replaced_tokens[token_index] = canonical
        matches.append(
            {
                "variant": variant,
                "canonical": canonical,
                "method": "fuzzy",
                "score": score,
            }
        )

    return " ".join(replaced_tokens), matches


def _resolve_datetime_offline(message_text: str) -> dict[str, Any]:
    result: dict[str, Any] = {"value": None, "confidence": 0.0, "evidence": {}}
    if not message_text:
        return result

    normalized, matches = _canonicalize_datetime_text(message_text)
    if not normalized:
        return result

    settings = {"PREFER_DATES_FROM": "future"}
    parsed = dateparser.parse(message_text, languages=["ru"], settings=settings)
    if not parsed and normalized != message_text:
        parsed = dateparser.parse(normalized, languages=["ru"], settings=settings)
    if not parsed:
        if matches:
            value = message_text.strip() if any(char.isdigit() for char in message_text) else normalized
            result["value"] = value
            result["confidence"] = 0.4
            result["evidence"] = {
                "normalized_text": normalized,
                "lexicon_matches": matches,
                "parser": "lexicon",
            }
        return result

    value = message_text.strip() if any(char.isdigit() for char in message_text) else normalized
    confidence = 0.6
    if matches:
        confidence += 0.2
    if normalized != message_text:
        confidence += 0.1

    result["value"] = value
    result["confidence"] = min(confidence, 1.0)
    result["evidence"] = {
        "normalized_text": normalized,
        "lexicon_matches": matches,
        "parser": "dateparser",
    }
    return result


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
    last_message = None
    for message in reversed(messages or []):
        if message:
            last_message = message
            break
    if not last_message:
        return None
    matched, _ = _match_expected_reply(
        expected_reply_type=expected_reply_type,
        message_text=last_message,
        client_slug=client_slug,
    )
    return last_message if matched else None


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


def _update_booking_from_message(booking: dict, message_text: str, *, client_slug: str | None) -> dict:
    booking = dict(booking)
    last_question = booking.get("last_question")
    if _is_blocked_slot_message(message_text):
        return booking

    if last_question in BOOKING_SLOT_ORDER:
        booking = _apply_booking_slot(
            booking,
            last_question,
            message_text,
            allow_freeform=True,
            client_slug=client_slug,
        )

    for slot_key in BOOKING_SLOT_ORDER:
        booking = _apply_booking_slot(
            booking,
            slot_key,
            message_text,
            allow_freeform=False,
            client_slug=client_slug,
        )

    return booking


def _update_booking_from_messages(
    booking: dict,
    messages: list[str],
    *,
    client_slug: str | None,
) -> dict:
    updated = dict(booking)
    for message in messages:
        updated = _update_booking_from_message(updated, message, client_slug=client_slug)
    return updated


def _next_booking_prompt(booking: dict, *, refusal_flags: dict | None = None) -> tuple[dict, str | None]:
    booking = dict(booking)
    if not booking.get("service"):
        booking["last_question"] = "service"
        from . import _legacy as legacy

        return booking, legacy.MSG_BOOKING_ASK_SERVICE
    if not booking.get("datetime"):
        booking["last_question"] = "datetime"
        from . import _legacy as legacy

        return booking, legacy.MSG_BOOKING_ASK_DATETIME
    if not booking.get("name"):
        from . import _legacy as legacy

        if legacy._is_refusal_flag_active(refusal_flags, "name"):
            booking["last_question"] = None
            return booking, None
        booking["last_question"] = "name"
        return booking, legacy.MSG_BOOKING_ASK_NAME
    booking["last_question"] = None
    return booking, None


def _is_booking_time_service_decision(decision: DemoSalonDecision | None) -> bool:
    if not decision or getattr(decision, "action", None) != "reply":
        return False
    intent = getattr(decision, "intent", None)
    if not isinstance(intent, str):
        return False
    from . import _legacy as legacy

    return intent.strip().casefold() in legacy.BOOKING_TIME_SERVICE_INTENTS


def _build_booking_summary(booking: dict, *, refusal_flags: dict | None = None) -> str:
    service = booking.get("service") or "не указано"
    datetime_pref = booking.get("datetime") or "не указано"
    name = booking.get("name")
    from . import _legacy as legacy

    name_refused = legacy._is_refusal_flag_active(refusal_flags, "name")
    if not name and name_refused:
        name_value = "отказ"
    else:
        name_value = name or "не указано"
    summary = f"Запись: услуга={service}; дата/время={datetime_pref}; имя={name_value}."
    if legacy._is_refusal_flag_active(refusal_flags, "phone"):
        summary = f"{summary} Телефон: отказ."
    return summary


__all__ = [
    "BOOKING_SLOT_ORDER",
    "BOOKING_SLOT_VALIDATORS",
    "_apply_booking_slot",
    "_apply_expected_reply_slot",
    "_build_booking_summary",
    "_clean_name_candidate",
    "_clear_service_hint",
    "_expected_reply_for_booking_question",
    "_get_booking_context",
    "_get_recent_service_hint",
    "_is_blocked_slot_message",
    "_is_booking_related_message",
    "_is_booking_time_service_decision",
    "_is_noise_slot_message",
    "_match_expected_reply",
    "_next_booking_prompt",
    "_resolve_datetime_offline",
    "_select_expected_reply_message",
    "_select_last_non_booking_message",
    "_set_booking_context",
    "_set_service_hint",
    "_update_booking_from_message",
    "_update_booking_from_messages",
    "_validate_datetime_slot",
    "_validate_name_slot",
    "_validate_service_slot",
]
