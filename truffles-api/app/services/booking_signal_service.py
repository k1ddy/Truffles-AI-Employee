"""Booking-related signal helpers (regex and lexicon matching)."""

from __future__ import annotations

import re
from datetime import datetime
from functools import lru_cache
from typing import Any

from rapidfuzz import fuzz, process

from app.services.pack_runtime_service import (
    _normalize_text,
    get_system_lexicon_list,
    load_system_lexicons,
    load_yaml_truth,
)
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
    cleaned_chars: list[str] = []
    allowed_chars = {" ", "-"}
    for ch in (value or ""):
        if ch.isalpha() or ch in allowed_chars:
            cleaned_chars.append(ch)
        else:
            cleaned_chars.append(" ")
    cleaned = "".join(cleaned_chars)
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


def _merge_datetime_lexicon(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_datetime_lexicon(dict(merged[key]), value)
        else:
            merged[key] = value
    return merged


@lru_cache(maxsize=16)
def load_datetime_lexicon(client_slug: str | None) -> dict[str, Any]:
    system_lexicons = load_system_lexicons()
    system_datetime = (
        system_lexicons.get("datetime_lexicon")
        if isinstance(system_lexicons, dict)
        else None
    )
    truth = load_yaml_truth(client_slug)
    domain_pack = truth.get("domain_pack") if isinstance(truth, dict) else None
    domain_datetime = (
        domain_pack.get("datetime_lexicon")
        if isinstance(domain_pack, dict)
        else None
    )
    merged: dict[str, Any] = dict(system_datetime) if isinstance(system_datetime, dict) else {}
    if isinstance(domain_datetime, dict):
        merged = _merge_datetime_lexicon(merged, domain_datetime)
    return merged


@lru_cache(maxsize=16)
def build_datetime_variant_index(client_slug: str | None) -> tuple[
    dict[str, str],
    set[str],
    list[tuple[tuple[str, ...], str, str]],
]:
    lexicon = load_datetime_lexicon(client_slug)
    variant_map: dict[str, str] = {}
    canonical_set: set[str] = set()
    entries: list[tuple[tuple[str, ...], str, str]] = []

    for group_name in ("days", "dayparts", "months"):
        group = lexicon.get(group_name)
        if not isinstance(group, dict):
            continue
        for payload in group.values():
            if not isinstance(payload, dict):
                continue
            canonical_raw = payload.get("canonical_ru")
            if not isinstance(canonical_raw, str):
                continue
            canonical = _normalize_text(canonical_raw)
            if not canonical:
                continue
            canonical_set.add(canonical)
            variant_map.setdefault(canonical, canonical)
            entries.append((tuple(canonical.split()), canonical, canonical))
            for lang_key in ("ru", "kk", "en"):
                variants = payload.get(lang_key)
                if not isinstance(variants, list):
                    continue
                for variant in variants:
                    if not isinstance(variant, str):
                        continue
                    normalized = _normalize_text(variant)
                    if not normalized:
                        continue
                    variant_map[normalized] = canonical
                    entries.append((tuple(normalized.split()), canonical, normalized))

    entries.sort(key=lambda item: len(item[0]), reverse=True)
    return variant_map, canonical_set, entries


def canonicalize_datetime_text(
    message_text: str,
    *,
    client_slug: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    normalized = _normalize_text(message_text)
    if not normalized:
        return "", []

    variant_map, canonical_set, entries = build_datetime_variant_index(client_slug)
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


def has_pending_time_question_marker(normalized: str) -> bool:
    markers = get_booking_text_tokens("pending_time_question_markers")
    return bool(normalized and any(marker in normalized for marker in markers))


def looks_like_time_preference_statement(
    message_text: str | None,
    *,
    normalized_text: str | None = None,
) -> bool:
    if not isinstance(message_text, str) or not message_text.strip():
        return False
    if "?" in message_text:
        return False
    normalized = normalized_text.strip() if isinstance(normalized_text, str) else _normalize_text(message_text)
    if not normalized:
        return False
    preference_markers = get_system_lexicon_list("daypart_preference_markers")
    if not preference_markers or not any(marker in normalized for marker in preference_markers):
        return False
    context_tokens = get_system_lexicon_list("hours_followup_phrases")
    return bool(context_tokens and any(token in normalized for token in context_tokens))


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
