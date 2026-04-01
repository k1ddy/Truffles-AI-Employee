"""Narrow runtime owner for booking-signal and consult-threshold helper behavior."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.routers.webhook.runtime_primitives import _contains_any
from app.services.ai_service import normalize_for_matching
from app.services.intent_service import DomainIntent, classify_domain_with_scores
from app.services.pack_runtime_service import (
    _match_service,
    _matches_service_request_lexicon,
    get_pack_service_hint,
    get_signal_lexicon_list,
    get_system_lexicon_list,
    load_system_lexicons,
    load_yaml_truth,
    semantic_question_type,
    semantic_service_match,
)
from app.services.pack_runtime_service import _normalize_text as _normalize_service_text

BOOKING_INFO_QUESTION_TYPES = {"pricing", "hours", "duration", "location", "parking", "master"}
TIME_PATTERN = re.compile(r"(?<!\d)(?:[01]?\d|2[0-3])[:.][0-5]\d(?!\d)")
TIME_HOUR_PATTERN = re.compile(r"\b(?:в|к)\s*(?:[01]?\d|2[0-3])\b", re.IGNORECASE)
TIME_ONLY_AMPM_PATTERN = re.compile(r"^\d{1,2}(?:am|pm)$", re.IGNORECASE)
TIME_ONLY_ALLOWED_TOKENS = {
    "в",
    "во",
    "к",
    "ко",
    "на",
    "около",
    "примерно",
    "после",
    "до",
    "ну",
    "э",
    "м",
}
TIME_ONLY_ALLOWED_PREFIXES = ("час", "мин", "вечер", "утр", "дн", "ноч")
DATE_PATTERN = re.compile(
    r"\b(?:сегодня|сегодняш\w*|завтра|завтраш\w*|послезавтра|послезавтраш\w*|понедель\w*|вторник\w*|сред\w*|четверг\w*|пятниц\w*|суббот\w*|воскрес\w*|выходн\w*|утром|днем|днём|вечером)\b",
    re.IGNORECASE,
)
DATE_NUMERIC_PATTERN = re.compile(r"\b\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?\b")
DATE_MONTH_PATTERN = re.compile(
    r"\b\d{1,2}\s*(?:январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)\w*\b",
    re.IGNORECASE,
)


def _merge_lang_phrase_maps(*maps: dict[str, Any] | None) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for mapping in maps:
        if not isinstance(mapping, dict):
            continue
        for lang_key, phrases in mapping.items():
            if not isinstance(phrases, list):
                continue
            bucket = merged.setdefault(lang_key, [])
            for phrase in phrases:
                if not isinstance(phrase, str):
                    continue
                cleaned = phrase.strip()
                if cleaned and cleaned not in bucket:
                    bucket.append(cleaned)
    return merged


def _collect_booking_request_lexicon(client_slug: str | None) -> dict[str, list[str]]:
    system_lexicons = load_system_lexicons()
    system_booking = system_lexicons.get("booking_request") if isinstance(system_lexicons, dict) else None
    truth = load_yaml_truth(client_slug)
    domain_pack = truth.get("domain_pack") if isinstance(truth, dict) else None
    synonyms = domain_pack.get("synonyms") if isinstance(domain_pack, dict) else None
    domain_booking = synonyms.get("booking") if isinstance(synonyms, dict) else None
    return _merge_lang_phrase_maps(system_booking, domain_booking)


def _matches_booking_request_lexicon(
    message_text: str | None,
    *,
    client_slug: str | None,
) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    lexicon = _collect_booking_request_lexicon(client_slug)
    if not lexicon:
        return False
    for lang_key in ("ru", "kk", "en"):
        phrases = lexicon.get(lang_key)
        if not isinstance(phrases, list):
            continue
        for phrase in phrases:
            if not isinstance(phrase, str):
                continue
            candidate = normalize_for_matching(phrase)
            if candidate and candidate in normalized:
                return True
    return False


def _extract_datetime(
    text: str,
    *,
    client_slug: str | None = None,
    relative_base: datetime | None = None,
) -> str | None:
    if not text:
        return None
    from app.routers.webhook.booking import _resolve_datetime_offline

    resolved = _resolve_datetime_offline(
        text,
        client_slug=client_slug,
        relative_base=relative_base,
    )
    if isinstance(resolved, dict):
        value = resolved.get("value")
        if isinstance(value, str) and value.strip():
            return value
    iso_date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    explicit_date_match = (
        iso_date_match
        or DATE_NUMERIC_PATTERN.search(text)
        or DATE_MONTH_PATTERN.search(text)
    )
    time_match = TIME_PATTERN.search(text) or TIME_HOUR_PATTERN.search(text)
    if explicit_date_match and time_match and explicit_date_match.start() <= time_match.start():
        combined_value = text[explicit_date_match.start() : time_match.end()].strip(" ,.")
        if combined_value:
            return combined_value
    time_match = TIME_PATTERN.search(text)
    if time_match:
        return time_match.group(0)
    hour_match = TIME_HOUR_PATTERN.search(text)
    if hour_match:
        return hour_match.group(0)
    numeric_date_match = DATE_NUMERIC_PATTERN.search(text)
    if numeric_date_match:
        return numeric_date_match.group(0)
    month_date_match = DATE_MONTH_PATTERN.search(text)
    if month_date_match:
        return month_date_match.group(0)
    date_match = DATE_PATTERN.search(text)
    if date_match:
        return date_match.group(0)
    return None


def _has_explicit_service_signal(
    message_text: str | None,
    *,
    client_slug: str | None,
    intent_decomp_payload: dict[str, Any] | None,
) -> bool:
    if not message_text:
        return False
    cleaned_text = re.sub(r"\[[^\]]+\]", " ", message_text)
    normalized = _normalize_service_text(cleaned_text)
    if not normalized:
        return False
    if isinstance(intent_decomp_payload, dict):
        raw_query = intent_decomp_payload.get("service_query")
        raw_source = intent_decomp_payload.get("service_query_source")
        if isinstance(raw_query, str) and raw_query.strip() and raw_source != "context":
            return True
    if client_slug:
        if _match_service(normalized, client_slug):
            return True
        if _matches_service_request_lexicon(normalized, client_slug):
            return True
        from app.routers.webhook.info import _detect_info_class_intents

        info_intents, _ = _detect_info_class_intents(
            cleaned_text,
            intent_decomp_set=set(),
            client_slug=client_slug,
        )
        if {"location", "hours", "parking"} & info_intents:
            return False
        if _extract_service_hint(cleaned_text, client_slug):
            return True
    return False


def _is_booking_request(text: str, *, client_slug: str | None) -> bool:
    if _matches_booking_request_lexicon(text, client_slug=client_slug):
        return True
    normalized = normalize_for_matching(text)
    if not normalized:
        return False
    booking_keywords = get_system_lexicon_list("booking_keywords")
    if booking_keywords and _contains_any(normalized, booking_keywords):
        return True
    desire_keywords = get_system_lexicon_list("booking_desire_keywords")
    need_or_desire_signal = bool(desire_keywords and _contains_any(normalized, desire_keywords))
    if not need_or_desire_signal or not client_slug:
        return False
    cleaned_text = re.sub(r"\[[^\]]+\]", " ", text)
    normalized_service = _normalize_service_text(cleaned_text)
    if not normalized_service:
        return False
    if not (_match_service(normalized_service, client_slug) or _matches_service_request_lexicon(normalized_service, client_slug)):
        return False
    try:
        has_datetime_signal = bool(_extract_datetime(cleaned_text, client_slug=client_slug))
    except TypeError:
        has_datetime_signal = bool(_extract_datetime(cleaned_text))
    if not has_datetime_signal:
        return False
    from app.routers.webhook.info import _detect_info_class_intents

    info_intents, _ = _detect_info_class_intents(
        cleaned_text,
        intent_decomp_set=set(),
        client_slug=client_slug,
    )
    return not bool({"location", "hours", "parking"} & info_intents)


def _extract_service_hint(text: str, client_slug: str | None) -> str | None:
    if not text:
        return None
    if not isinstance(client_slug, str):
        return None
    slug = client_slug.strip()
    if not slug:
        return None
    cleaned_text = re.sub(r"\[[^\]]+\]", " ", text).strip()
    if not cleaned_text:
        return None
    normalized_text = _normalize_service_text(cleaned_text)
    booking_like = _is_booking_request(cleaned_text, client_slug=slug)
    if not booking_like:
        booking_like = bool(
            TIME_PATTERN.search(cleaned_text)
            or TIME_HOUR_PATTERN.search(cleaned_text)
            or DATE_PATTERN.search(cleaned_text)
            or DATE_NUMERIC_PATTERN.search(cleaned_text)
            or DATE_MONTH_PATTERN.search(cleaned_text)
        )
    domain_intent, _, _, domain_meta = classify_domain_with_scores(cleaned_text, None)
    strict_in_hits = int(domain_meta.get("strict_in_hits") or 0)
    if domain_intent == DomainIntent.OUT_OF_DOMAIN and strict_in_hits <= 0 and not booking_like:
        return None
    match = semantic_service_match(cleaned_text, slug)
    if not match or match.action != "match":
        fallback = get_pack_service_hint(cleaned_text, client_slug=slug)
        if fallback:
            return fallback
        return None
    canonical_name = match.canonical_name
    if isinstance(canonical_name, str) and canonical_name.strip():
        if booking_like and normalized_text:
            canonical_tokens = _normalize_service_text(canonical_name).split()
            message_tokens = normalized_text.split()
            if canonical_tokens and message_tokens:
                if not any(token in message_tokens for token in canonical_tokens):
                    return None
        return canonical_name.strip()
    return None


def _looks_like_time_only_request(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    time_only_phrases = get_system_lexicon_list("time_only_request_phrases")
    if time_only_phrases and _contains_any(normalized, time_only_phrases):
        return True
    from app.routers.webhook.info import _tokenize_for_matching

    tokens = _tokenize_for_matching(normalized)
    if not tokens:
        return False
    has_time_token = False
    has_time_marker = bool(TIME_PATTERN.search(message_text) or TIME_HOUR_PATTERN.search(message_text))
    for token in tokens:
        if token.isdigit():
            if len(token) <= 2:
                has_time_token = True
                continue
            if has_time_marker and len(token) in (3, 4):
                has_time_token = True
                continue
            return False
        if TIME_ONLY_AMPM_PATTERN.fullmatch(token):
            has_time_token = True
            continue
        if token in TIME_ONLY_ALLOWED_TOKENS:
            continue
        if any(token.startswith(prefix) for prefix in TIME_ONLY_ALLOWED_PREFIXES):
            has_time_marker = True
            continue
        return False
    return has_time_token


def _evaluate_booking_signal(
    messages: list[str],
    *,
    client_slug: str | None,
    message_text: str | None,
    relative_base: datetime | None = None,
) -> tuple[bool, dict | None]:
    if not messages:
        return False, None
    if any(_is_booking_request(message, client_slug=client_slug) for message in messages):
        return True, None
    has_service = any(_extract_service_hint(message, client_slug) for message in messages)
    has_datetime = any(
        _extract_datetime(
            message,
            client_slug=client_slug,
            relative_base=relative_base,
        )
        for message in messages
    )
    booking_signal = has_service and has_datetime
    if booking_signal and message_text:
        from app.routers.webhook.info import _looks_like_info_query

        if _looks_like_info_query(message_text, client_slug=client_slug):
            return False, {"booking_blocked_reason": "info_question"}
        normalized = normalize_for_matching(message_text)
        procedure_combo_any = get_signal_lexicon_list(client_slug, "procedure_combo_require_any")
        procedure_combo_all = get_signal_lexicon_list(client_slug, "procedure_combo_require_all")
        if (
            normalized
            and procedure_combo_any
            and procedure_combo_all
            and _contains_any(normalized, procedure_combo_any)
            and _contains_any(normalized, procedure_combo_all)
        ):
            return False, {"booking_blocked_reason": "procedure_combo"}
        segments = [segment.strip() for segment in re.split(r"[?!\.,;]+", message_text) if segment.strip()]
        if not segments:
            segments = [message_text.strip()]
        for segment in segments:
            question_type = semantic_question_type(
                segment,
                include_kinds=BOOKING_INFO_QUESTION_TYPES,
                client_slug=client_slug,
            )
            if question_type and question_type.kind in BOOKING_INFO_QUESTION_TYPES:
                return (
                    False,
                    {
                        "booking_blocked_reason": "info_question",
                        "question_type": question_type.kind,
                        "question_type_score": question_type.score,
                    },
                )
    return booking_signal, None


def _has_booking_signal(
    messages: list[str],
    *,
    client_slug: str | None = None,
    message_text: str | None = None,
) -> bool:
    booking_signal, _ = _evaluate_booking_signal(
        messages,
        client_slug=client_slug,
        message_text=message_text,
    )
    return booking_signal


__all__ = [
    "BOOKING_INFO_QUESTION_TYPES",
    "DATE_MONTH_PATTERN",
    "DATE_NUMERIC_PATTERN",
    "DATE_PATTERN",
    "TIME_HOUR_PATTERN",
    "TIME_ONLY_ALLOWED_PREFIXES",
    "TIME_ONLY_ALLOWED_TOKENS",
    "TIME_ONLY_AMPM_PATTERN",
    "TIME_PATTERN",
    "_collect_booking_request_lexicon",
    "_evaluate_booking_signal",
    "_extract_datetime",
    "_extract_service_hint",
    "_has_booking_signal",
    "_has_explicit_service_signal",
    "_is_booking_request",
    "_looks_like_time_only_request",
    "_matches_booking_request_lexicon",
]
