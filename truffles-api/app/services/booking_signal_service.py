"""Booking-related signal helpers (regex and lexicon matching)."""

from __future__ import annotations

import re
from datetime import datetime

from app.services.pack_runtime_service import _normalize_text, get_system_lexicon_list
from app.services.signal_manifest_service import (
    get_booking_layout_swap_map,
    get_booking_regex_pattern,
    get_booking_regex_replacements,
    get_booking_text_tokens,
)

_NEVER_MATCH_PATTERN = re.compile(r"(?!x)x")
_PHONE_PATTERN = get_booking_regex_pattern("phone_pattern") or _NEVER_MATCH_PATTERN
_BOOKING_HOUR_FALLBACK_PATTERN = (
    get_booking_regex_pattern("booking_hour_fallback_pattern") or _NEVER_MATCH_PATTERN
)
_TIME_TOKEN_RE = get_booking_regex_pattern("time_token_pattern") or _NEVER_MATCH_PATTERN
_DAYPART_TOKEN_RE = get_booking_regex_pattern("daypart_token_pattern") or _NEVER_MATCH_PATTERN
_SPECIALIST_PREFIX_RE = get_booking_regex_pattern("specialist_prefix_pattern") or _NEVER_MATCH_PATTERN
_LAYOUT_SWAP_MAP = str.maketrans(get_booking_layout_swap_map())


def looks_like_layout_swap(text: str) -> bool:
    if not text or not text.strip():
        return False
    has_cyrillic = bool(re.search(r"[а-яё]", text, flags=re.IGNORECASE))
    has_latin = bool(re.search(r"[a-z]", text, flags=re.IGNORECASE))
    if not has_latin or has_cyrillic:
        return False
    return len(re.findall(r"[a-z]", text, flags=re.IGNORECASE)) >= 3


def swap_keyboard_layout(text: str) -> str:
    return (text or "").translate(_LAYOUT_SWAP_MAP)


def collapse_repeats(text: str, *, max_repeats: int = 2) -> str:
    if not text:
        return ""
    if max_repeats < 1:
        return text
    pattern = re.compile(rf"(.)\1{{{max_repeats},}}")

    def _replace(match: re.Match[str]) -> str:
        return match.group(1) * max_repeats

    return pattern.sub(_replace, text)


def match_booking_hour_fallback(message_text: str | None) -> dict[str, str | None] | None:
    if not message_text:
        return None
    match = _BOOKING_HOUR_FALLBACK_PATTERN.search(message_text)
    if not match:
        return None
    return {
        "prep": match.group("prep") or "",
        "hour": match.group("hour") or "",
        "minute": match.group("minute"),
    }


def looks_like_phone(message_text: str | None) -> bool:
    if not message_text:
        return False
    return bool(_PHONE_PATTERN.search(message_text))


def clean_name_candidate(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-zА-Яа-яЁё\s-]", " ", value or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_phone_digits(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    return digits or None


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    iso_match = re.match(
        r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})(?:[ T](?P<hour>\d{1,2}):(?P<minute>\d{2}))?$",
        raw,
    )
    if not iso_match:
        return None
    try:
        return datetime(
            int(iso_match.group("year")),
            int(iso_match.group("month")),
            int(iso_match.group("day")),
            int(iso_match.group("hour") or 0),
            int(iso_match.group("minute") or 0),
        )
    except ValueError:
        return None


def has_explicit_date_signal(value: str | None) -> bool:
    if not isinstance(value, str):
        return False
    token = value.strip()
    if not token:
        return False
    if extract_relative_date_token(token):
        return True
    if re.search(r"\d{4}-\d{2}-\d{2}", token):
        return True
    if re.search(r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b", token):
        return True
    return False


def pick_relative_day_token(text: str) -> str | None:
    if not text:
        return None
    for pattern, replacement in get_booking_regex_replacements("relative_day_token_patterns"):
        if pattern.search(text):
            return replacement
    return None


def extract_relative_date_token(text: str | None) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None
    for pattern, replacement in get_booking_regex_replacements("relative_day_token_patterns"):
        if pattern.search(text):
            return replacement
    return None


def pick_daypart_token(text: str) -> str | None:
    if not text:
        return None
    for pattern, replacement in get_booking_regex_replacements("daypart_token_patterns"):
        if pattern.search(text):
            return replacement
    return None


def normalize_resolved_datetime_value(
    message_text: str,
    *,
    normalized_text: str | None = None,
) -> str | None:
    raw = message_text.strip() if isinstance(message_text, str) else ""
    normalized = normalized_text.strip() if isinstance(normalized_text, str) else ""
    source = " ".join(part for part in (raw, normalized) if part).strip()
    if not source:
        return None
    day_token = pick_relative_day_token(source)
    daypart_token = pick_daypart_token(source)
    if day_token and daypart_token:
        return f"{day_token} {daypart_token}"
    if day_token:
        return day_token
    if daypart_token:
        return daypart_token
    return None


def has_duration_context_marker(normalized: str) -> bool:
    markers = get_booking_text_tokens("datetime_duration_context_markers")
    return bool(normalized and any(marker in normalized for marker in markers))


def has_daypart_stem(normalized: str) -> bool:
    stems = get_booking_text_tokens("datetime_daypart_stems")
    return bool(normalized and any(stem in normalized for stem in stems))


def extract_time_token(text: str | None) -> str | None:
    if not text:
        return None
    match = _TIME_TOKEN_RE.search(text)
    if not match:
        return None
    token = match.group(0)
    return token.replace(".", ":")


def coerce_time_token(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().replace(".", ":")
    match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", token)
    if not match:
        return None
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def strip_daypart_tokens(text: str) -> str:
    stripped_text = _DAYPART_TOKEN_RE.sub(" ", text)
    return re.sub(r"\s+", " ", stripped_text).strip()


def extract_daypart_token(text: str | None) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None
    normalized = _normalize_text(text)
    if not normalized:
        return None
    evening_keywords = get_system_lexicon_list("daypart_evening_keywords")
    morning_keywords = get_system_lexicon_list("daypart_morning_keywords")
    day_keywords = get_system_lexicon_list("daypart_day_keywords")
    if evening_keywords and any(token in normalized for token in evening_keywords):
        return "evening"
    if morning_keywords and any(token in normalized for token in morning_keywords):
        return "morning"
    if day_keywords and any(token in normalized for token in day_keywords):
        return "day"
    return None


def clean_specialist_name(value: str | None) -> str | None:
    if not value or not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    cleaned = _SPECIALIST_PREFIX_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or None
