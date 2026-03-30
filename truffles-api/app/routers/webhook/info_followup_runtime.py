"""Narrow owner for info followup detection helpers."""

from __future__ import annotations

import re

from app.routers.webhook.runtime_primitives import (
    INFO_ANCHOR_GROUPS,
    SESSION_MEMORY_SHORT_TOKENS,
    _contains_any,
)
from app.services.ai_service import normalize_for_matching
from app.services.pack_runtime_service import get_system_lexicon_list
from app.services.signal_manifest_service import get_info_regex_pattern

_TOKENIZE_WORD_RE = get_info_regex_pattern("tokenize_word_pattern") or re.compile(r"\w+")
_CARRYOVER_CAPACITY_LEAD_PREFIX = "скольк"
_CARRYOVER_CAPACITY_TOKENS = ("мест",)


def _tokenize_for_matching(normalized: str) -> list[str]:
    return _TOKENIZE_WORD_RE.findall(normalized)


def _has_anchor_prefix(tokens: list[str], prefix: str) -> bool:
    if len(prefix) <= 2:
        return any(token == prefix for token in tokens)
    return any(token.startswith(prefix) for token in tokens)


def _anchor_group_hit(tokens: list[str], group: tuple[str, ...]) -> bool:
    return all(_has_anchor_prefix(tokens, prefix) for prefix in group)


def _count_anchor_hits(tokens: list[str], groups: list[tuple[str, ...]]) -> int:
    return sum(1 for group in groups if _anchor_group_hit(tokens, group))


def _contains_any_text_token(text: str | None, tokens: tuple[str, ...]) -> bool:
    if not text:
        return False
    return any(token in text for token in tokens)


def _looks_like_hours_followup(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    phrases = get_system_lexicon_list("hours_followup_phrases")
    return bool(phrases) and _contains_any(normalized, phrases)


def _looks_like_carryover_followup(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    tokens = _tokenize_for_matching(normalized)
    if not tokens:
        return False
    followup_phrases = get_system_lexicon_list("carryover_followup_phrases")
    if followup_phrases and _contains_any(normalized, followup_phrases):
        return True
    if (
        tokens[0].startswith(_CARRYOVER_CAPACITY_LEAD_PREFIX)
        and _contains_any_text_token(normalized, _CARRYOVER_CAPACITY_TOKENS)
    ):
        return True
    if len(tokens) <= SESSION_MEMORY_SHORT_TOKENS:
        pricing_groups = INFO_ANCHOR_GROUPS.get("pricing", [])
        if pricing_groups and _count_anchor_hits(tokens, pricing_groups) > 0:
            return True
    lead_tokens = set(get_system_lexicon_list("carryover_followup_lead_tokens"))
    question_phrases = get_system_lexicon_list("carryover_followup_question_phrases")
    if lead_tokens and question_phrases and tokens[0] in lead_tokens:
        if _contains_any(normalized, question_phrases):
            return True
    return False


__all__ = [
    "_looks_like_carryover_followup",
    "_looks_like_hours_followup",
]
