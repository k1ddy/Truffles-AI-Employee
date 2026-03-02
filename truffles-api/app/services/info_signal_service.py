"""Signal helpers for info/lexicon matching (routing-neutral)."""

from __future__ import annotations

import re
from typing import Iterable

from app.services.ai_service import normalize_for_matching
from app.services.pack_runtime_service import (
    _normalize_text,
    get_signal_lexicon_list,
    get_system_lexicon_list,
)


def tokenize_for_matching(normalized: str) -> list[str]:
    return re.findall(r"\w+", normalized)


def has_token_prefix(tokens: list[str], prefix: str) -> bool:
    return any(token.startswith(prefix) for token in tokens)


def tokens_have_prefixes(tokens: list[str], prefixes: Iterable[str]) -> bool:
    return any(has_token_prefix(tokens, prefix) for prefix in prefixes)


def has_anchor_prefix(tokens: list[str], prefix: str) -> bool:
    """Anchor matching must avoid false positives on very short stems like 'до' in 'долгими'."""
    if len(prefix) <= 2:
        return any(token == prefix for token in tokens)
    return any(token.startswith(prefix) for token in tokens)


def anchor_group_hit(tokens: list[str], group: tuple[str, ...]) -> bool:
    return all(has_anchor_prefix(tokens, prefix) for prefix in group)


def count_anchor_hits(tokens: list[str], groups: list[tuple[str, ...]]) -> int:
    hits = 0
    for group in groups:
        if anchor_group_hit(tokens, group):
            hits += 1
    return hits


def signal_phrase_list(client_slug: str | None, *keys: str) -> list[str]:
    phrases: list[str] = []
    for key in keys:
        values = get_signal_lexicon_list(client_slug, key)
        if not values:
            continue
        for phrase in values:
            token = phrase.strip() if isinstance(phrase, str) else ""
            if token and token not in phrases:
                phrases.append(token)
    return phrases


def normalized_contains_any(normalized: str, phrases: Iterable[str]) -> bool:
    if not normalized:
        return False
    return any(phrase and phrase in normalized for phrase in phrases)


def signal_any_match(normalized: str, client_slug: str | None, *keys: str) -> bool:
    if not keys:
        return False
    phrases = signal_phrase_list(client_slug, *keys)
    return bool(phrases) and normalized_contains_any(normalized, phrases)


def signal_pair_match(
    normalized: str,
    client_slug: str | None,
    key_a: str,
    key_b: str,
) -> bool:
    phrases_a = signal_phrase_list(client_slug, key_a)
    phrases_b = signal_phrase_list(client_slug, key_b)
    if not phrases_a or not phrases_b:
        return False
    return normalized_contains_any(normalized, phrases_a) and normalized_contains_any(normalized, phrases_b)


def system_any_match(normalized: str, key: str) -> bool:
    phrases = get_system_lexicon_list(key)
    return bool(phrases) and normalized_contains_any(normalized, phrases)


def system_any_match_multi(normalized: str, *keys: str) -> bool:
    return any(system_any_match(normalized, key) for key in keys)


def is_short_reply(message_text: str | None, *, max_tokens: int) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    tokens = tokenize_for_matching(normalized)
    return 0 < len(tokens) <= max_tokens


def looks_like_services_overview_message(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    markers = get_signal_lexicon_list(client_slug, "services_overview_phrases")
    if not markers:
        markers = get_system_lexicon_list("services_overview_phrases")
    return bool(markers and normalized_contains_any(normalized, markers))


def looks_like_booking_verification_message(text: str | None) -> bool:
    if not text:
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    keywords = get_system_lexicon_list("booking_verification_keywords")
    return bool(keywords and normalized_contains_any(normalized, keywords))
