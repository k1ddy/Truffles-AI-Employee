"""Compatibility-only policy helper exports."""

from __future__ import annotations

from app.routers.webhook.policy import (
    _detect_policy_gate_section,
    _get_guard_topics,
    _get_policy_section,
    _load_policy_pack,
    _policy_str_list,
    _resolve_hard_law_sections,
)
from app.routers.webhook.runtime_primitives import _contains_any
from app.services.pack_runtime_service import _normalize_text


def _looks_like_policy_topic(
    message_text: str | None,
    *,
    policy_type: str | None = None,
    policy_pack: dict | None = None,
    client_slug: str | None = None,
) -> bool:
    policy_pack = (
        policy_pack
        if isinstance(policy_pack, dict)
        else _load_policy_pack(policy_type=policy_type, client_slug=client_slug)
    )
    hard_law_sections = set(_resolve_hard_law_sections(policy_pack))
    return bool(
        _detect_policy_gate_section(
            message_text,
            policy_pack=policy_pack,
            hard_law_sections=hard_law_sections,
        )
    )


def _looks_like_promotions_request(
    message_text: str | None,
    *,
    policy_type: str | None = None,
    policy_pack: dict | None = None,
    client_slug: str | None = None,
) -> bool:
    if not message_text:
        return False
    normalized = _normalize_text(message_text)
    if not normalized:
        return False
    policy_pack = (
        policy_pack
        if isinstance(policy_pack, dict)
        else _load_policy_pack(policy_type=policy_type, client_slug=client_slug)
    )
    discounts = _get_policy_section(policy_pack, "discounts")
    keywords = _policy_str_list(discounts.get("keywords") if isinstance(discounts, dict) else None)
    if keywords and _contains_any(normalized, keywords):
        return True
    birthday_window = discounts.get("birthday_window") if isinstance(discounts, dict) else None
    if isinstance(birthday_window, dict):
        phrase = birthday_window.get("phrase")
        day_words = _policy_str_list(birthday_window.get("day_words"))
        if isinstance(phrase, str) and phrase.strip():
            if phrase in normalized and _contains_any(normalized, day_words):
                return True
    return False


__all__ = [
    "_looks_like_policy_topic",
    "_looks_like_promotions_request",
]
