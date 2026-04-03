"""Narrow runtime owner for booking-signal and consult-threshold helper behavior."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.services.ai_service import normalize_for_matching
from app.services.pack_runtime_service import (
    load_system_lexicons,
    load_yaml_truth,
)

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
    del message_text, client_slug
    if not isinstance(intent_decomp_payload, dict):
        return False
    raw_query = intent_decomp_payload.get("service_query")
    raw_source = intent_decomp_payload.get("service_query_source")
    return bool(
        isinstance(raw_query, str)
        and raw_query.strip()
        and raw_source != "context"
    )


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
    "_extract_datetime",
    "_has_explicit_service_signal",
    "_matches_booking_request_lexicon",
]
