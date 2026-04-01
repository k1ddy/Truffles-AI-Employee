"""Expected-reply interruption helpers extracted from the legacy decision router.

This cluster stays compatible with the old helper names, but it now lives in a
dedicated helper module so the mounted webhook package no longer depends on
`decision.py` for package-root compatibility exports.
"""

from __future__ import annotations

import re

from app.routers.webhook.booking import (
    _is_datetime_grounded_for_prompt,
    _looks_like_booking_reschedule_request,
    _validate_datetime_slot,
    _validate_name_slot,
    _validate_service_slot,
)
from app.routers.webhook.booking_signal_runtime import (
    TIME_HOUR_PATTERN,
    TIME_PATTERN,
    _extract_datetime,
    _is_booking_request,
)
from app.routers.webhook.info import _detect_info_class_intents, _looks_like_info_query
from app.routers.webhook.media import _is_style_reference_request
from app.routers.webhook.runtime_primitives import (
    EXPECTED_REPLY_NAME,
    EXPECTED_REPLY_PHONE,
    EXPECTED_REPLY_SERVICE,
    EXPECTED_REPLY_TIME,
    QUESTION_WORD_PREFIXES,
)
from app.services.ai_service import normalize_for_matching
from app.services.booking_signal_service import (
    extract_relative_date_token,
    has_daypart_stem,
    match_booking_hour_fallback,
    normalize_phone_digits,
    pick_daypart_token,
)
from app.services.pack_runtime_service import (
    _has_duration_signal,
    _has_price_signal,
    _normalize_text,
    get_system_lexicon_list,
)

WEEKEND_RELATIVE_DAY_TOKEN = "в субботу"
BOOKING_VERIFICATION_PATTERNS = (
    re.compile(r"\bпров\w*\b.*\b(запис|брон|бронир)\w*"),
    re.compile(r"\bподтверд\w*\b.*\b(запис|брон|бронир)\w*"),
    re.compile(r"\bподтверд\w*\b.*\b(дат|врем)\w*"),
    re.compile(r"\b(жду|ожидаю|не получил\w*)\b.*\b(подтвержд|ответ)\w*"),
    re.compile(r"\b(check|verify|confirm)\b.*\b(booking|appointment|reservation)\b"),
)


def _validate_expected_reply_value(
    *,
    expected_reply_type: str | None,
    value: str | None,
    client_slug: str | None,
) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    cleaned = value.strip()
    if expected_reply_type == EXPECTED_REPLY_SERVICE:
        return _validate_service_slot(cleaned, allow_freeform=True, client_slug=client_slug)
    if expected_reply_type == EXPECTED_REPLY_TIME:
        return _validate_datetime_slot(cleaned, allow_freeform=True, client_slug=client_slug)
    if expected_reply_type == EXPECTED_REPLY_NAME:
        return _validate_name_slot(cleaned, allow_freeform=True, client_slug=client_slug)
    if expected_reply_type == EXPECTED_REPLY_PHONE:
        return normalize_phone_digits(cleaned)
    return None


def _looks_like_booking_verification_request(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in BOOKING_VERIFICATION_PATTERNS)


def _has_explicit_location_or_hours_request(
    message_text: str | None,
    *,
    client_slug: str | None,
    strict: bool = False,
) -> bool:
    if not message_text:
        return False
    _info_intents, info_meta = _detect_info_class_intents(
        message_text,
        intent_decomp_set=set(),
        client_slug=client_slug,
    )
    anchor_intents: set[str] = set()
    if isinstance(info_meta, dict):
        raw_anchor_intents = info_meta.get("anchor_intents")
        if isinstance(raw_anchor_intents, list):
            anchor_intents = {
                intent.strip().casefold()
                for intent in raw_anchor_intents
                if isinstance(intent, str) and intent.strip()
            }
    info_signals = info_meta.get("info_signals") if isinstance(info_meta, dict) else None
    master_signal = bool(isinstance(info_signals, dict) and info_signals.get("master"))
    if isinstance(info_signals, dict) and info_signals.get("location_address_hint"):
        return True
    if {"location", "hours", "parking"} & anchor_intents:
        if strict and master_signal:
            return False
        return True
    return False


def _is_question_like_message(message_text: str | None) -> bool:
    if not isinstance(message_text, str) or not message_text.strip():
        return False
    normalized_message = _normalize_text(message_text)
    if not normalized_message:
        return False
    if "?" in message_text:
        return True
    tokens = normalized_message.split()
    return bool(tokens) and any(tokens[0].startswith(prefix) for prefix in QUESTION_WORD_PREFIXES)


def _is_question_like_time_slot_constraint_candidate(
    *,
    message_text: str | None,
    candidate_value: str | None,
) -> bool:
    if not isinstance(message_text, str) or not message_text.strip():
        return False
    if not isinstance(candidate_value, str) or not candidate_value.strip():
        return False
    normalized_message = _normalize_text(message_text)
    tokens = normalized_message.split()
    question_like = "?" in message_text
    if not question_like and tokens:
        question_like = any(tokens[0].startswith(prefix) for prefix in QUESTION_WORD_PREFIXES)
    if not question_like:
        return False
    has_clock_time_signal = bool(
        TIME_PATTERN.search(message_text)
        or TIME_HOUR_PATTERN.search(message_text)
        or match_booking_hour_fallback(message_text)
        or TIME_PATTERN.search(candidate_value)
        or TIME_HOUR_PATTERN.search(candidate_value)
        or match_booking_hour_fallback(candidate_value)
    )
    return not has_clock_time_signal


def _is_daypart_only_time_slot_constraint_candidate(
    *,
    message_text: str | None,
    candidate_value: str | None,
) -> bool:
    if not isinstance(message_text, str) or not message_text.strip():
        return False
    if not isinstance(candidate_value, str) or not candidate_value.strip():
        return False
    candidate_token = pick_daypart_token(candidate_value)
    if not isinstance(candidate_token, str) or not candidate_token.strip():
        return False
    normalized_candidate = normalize_for_matching(candidate_value)
    normalized_token = normalize_for_matching(candidate_token)
    if not normalized_candidate or normalized_candidate != normalized_token:
        return False
    has_clock_time_signal = bool(
        TIME_PATTERN.search(message_text)
        or TIME_HOUR_PATTERN.search(message_text)
        or match_booking_hour_fallback(message_text)
        or TIME_PATTERN.search(candidate_value)
        or TIME_HOUR_PATTERN.search(candidate_value)
        or match_booking_hour_fallback(candidate_value)
    )
    return not has_clock_time_signal


def _is_declarative_time_window_slot_constraint_candidate(
    *,
    message_text: str | None,
) -> bool:
    if not isinstance(message_text, str) or not message_text.strip():
        return False
    if _is_question_like_message(message_text):
        return False
    return bool(
        re.search(
            r"\b(?:с|со|между)\s*(?:[01]?\d|2[0-3])(?::[0-5]\d)?\s*(?:до|по|и|-|–|—)\s*(?:[01]?\d|2[0-3])(?::[0-5]\d)?\b",
            message_text,
            re.IGNORECASE,
        )
    )


def _is_declarative_partial_date_slot_constraint_candidate(
    *,
    message_text: str | None,
    candidate_value: str | None,
    client_slug: str | None,
) -> bool:
    if not isinstance(message_text, str) or not message_text.strip():
        return False
    if not isinstance(candidate_value, str) or not candidate_value.strip():
        return False
    if _is_question_like_message(message_text):
        return False
    if _is_declarative_time_window_slot_constraint_candidate(message_text=message_text):
        return False
    if _is_datetime_grounded_for_prompt(candidate_value, client_slug=client_slug):
        return False
    normalized_message = normalize_for_matching(message_text)
    if not normalized_message or extract_relative_date_token(message_text) != WEEKEND_RELATIVE_DAY_TOKEN:
        return False
    extracted_value = _extract_datetime(message_text, client_slug=client_slug)
    if not isinstance(extracted_value, str) or not extracted_value.strip():
        return False
    normalized_candidate = normalize_for_matching(candidate_value)
    normalized_extracted = normalize_for_matching(extracted_value)
    if not normalized_candidate or not normalized_extracted:
        return False
    return normalized_candidate == normalized_extracted


def _is_time_slot_constraint_candidate(
    *,
    message_text: str | None,
    candidate_value: str | None,
    client_slug: str | None,
) -> bool:
    return _is_question_like_time_slot_constraint_candidate(
        message_text=message_text,
        candidate_value=candidate_value,
    ) or _is_daypart_only_time_slot_constraint_candidate(
        message_text=message_text,
        candidate_value=candidate_value,
    ) or _is_declarative_partial_date_slot_constraint_candidate(
        message_text=message_text,
        candidate_value=candidate_value,
        client_slug=client_slug,
    )


def _should_block_expected_reply_by_info(
    *,
    expected_reply_type: str | None,
    message_text: str | None,
    client_slug: str | None,
) -> bool:
    if expected_reply_type not in {
        EXPECTED_REPLY_SERVICE,
        EXPECTED_REPLY_TIME,
        EXPECTED_REPLY_NAME,
    }:
        return False
    if not message_text:
        return False
    normalized_message = _normalize_text(message_text)
    info_query = _looks_like_info_query(message_text, client_slug=client_slug)
    price_signal = _has_price_signal(normalized_message, message_text)
    duration_signal = _has_duration_signal(normalized_message, message_text)
    style_reference_signal = _is_style_reference_request(message_text, has_media=False)
    tokens = normalized_message.split()
    question_like = "?" in message_text
    if not question_like and tokens:
        question_like = any(tokens[0].startswith(prefix) for prefix in QUESTION_WORD_PREFIXES)
    location_question_signal = bool(
        question_like
        and _has_explicit_location_or_hours_request(
            message_text,
            client_slug=client_slug,
            strict=True,
        )
    )
    verification_signal = _looks_like_booking_verification_request(message_text)
    reschedule_signal = _looks_like_booking_reschedule_request(
        message_text,
        client_slug=client_slug,
    )
    media_offer_terms = get_system_lexicon_list("style_reference_media_terms")
    media_offer_verbs = get_system_lexicon_list("style_reference_send_terms")
    media_offer_signal = bool(
        style_reference_signal
        or (
            media_offer_terms
            and media_offer_verbs
            and any(term in normalized_message for term in media_offer_terms)
            and any(term in normalized_message for term in media_offer_verbs)
        )
    )
    explicit_info_interrupt = bool(
        price_signal
        or duration_signal
        or style_reference_signal
        or location_question_signal
        or verification_signal
        or reschedule_signal
        or media_offer_signal
    )
    expected_reply_candidate = None
    if expected_reply_type == EXPECTED_REPLY_TIME:
        expected_reply_candidate = _validate_expected_reply_value(
            expected_reply_type=expected_reply_type,
            value=message_text,
            client_slug=client_slug,
        )
    question_like_time_slot_constraint = bool(
        expected_reply_type == EXPECTED_REPLY_TIME
        and _is_question_like_time_slot_constraint_candidate(
            message_text=message_text,
            candidate_value=expected_reply_candidate,
        )
    )
    blocked = bool(info_query or explicit_info_interrupt)
    if not blocked and expected_reply_type in {EXPECTED_REPLY_TIME, EXPECTED_REPLY_NAME} and question_like:
        blocked = True
    if blocked and expected_reply_type == EXPECTED_REPLY_TIME:
        booking_signal = _is_booking_request(message_text, client_slug=client_slug)
        has_clock_time_signal = bool(
            re.search(r"\b(?:[01]?\d|2[0-3])[:.][0-5]\d\b", message_text)
            or TIME_HOUR_PATTERN.search(message_text)
            or match_booking_hour_fallback(message_text)
        )
        try:
            has_datetime_signal = bool(_extract_datetime(message_text, client_slug=client_slug))
        except TypeError:
            has_datetime_signal = bool(_extract_datetime(message_text))
        has_daypart_candidate = bool(
            isinstance(expected_reply_candidate, str)
            and expected_reply_candidate.strip()
            and has_daypart_stem(normalize_for_matching(expected_reply_candidate))
        )
        if (
            isinstance(expected_reply_candidate, str)
            and expected_reply_candidate.strip()
            and not explicit_info_interrupt
            and (
                has_datetime_signal
                or booking_signal
                or has_daypart_candidate
                or question_like_time_slot_constraint
            )
            and (
                not question_like
                or booking_signal
                or has_clock_time_signal
                or has_daypart_candidate
                or question_like_time_slot_constraint
            )
        ):
            return False
        if not has_datetime_signal:
            return blocked
        if (
            question_like
            and has_datetime_signal
            and not explicit_info_interrupt
            and (booking_signal or has_clock_time_signal)
        ):
            return False
        if question_like:
            return True
        return bool(info_query or price_signal or duration_signal)
    return blocked


__all__ = [
    "_has_explicit_location_or_hours_request",
    "_is_question_like_time_slot_constraint_candidate",
    "_is_time_slot_constraint_candidate",
    "_looks_like_booking_verification_request",
    "_should_block_expected_reply_by_info",
    "_validate_expected_reply_value",
]
