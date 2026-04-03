"""Compatibility-only decision helper exports."""

from __future__ import annotations

from app.routers.webhook.policy import _format_discounts_policy_reply
from app.services.pack_runtime_service import (
    _normalize_text as _normalize_service_text,
    get_signal_lexicon_list,
)


def _looks_like_promo_code_request(message_text: str | None, *, client_slug: str | None = None) -> bool:
    if not message_text:
        return False
    normalized = _normalize_service_text(message_text).replace("-", " ")
    if not normalized:
        return False
    promo_code_terms = get_signal_lexicon_list(client_slug, "promotion_promo_code_terms")
    fallback_terms = (
        "промокод",
        "промо код",
        "promo code",
        "promo code",
    )
    terms = [
        token.strip().casefold()
        for token in [*(promo_code_terms or []), *fallback_terms]
        if isinstance(token, str) and token.strip()
    ]
    return any(token in normalized for token in terms)


def _format_discounts_reply_for_message(
    *,
    message_text: str | None,
    policy_pack: dict | None,
    policy_type: str | None,
    client_slug: str | None = None,
    promo_code_request: bool | None = None,
) -> str | None:
    reply = _format_discounts_policy_reply(
        policy_pack=policy_pack,
        policy_type=policy_type,
    )
    if not (isinstance(reply, str) and reply.strip()):
        return None
    if promo_code_request is None:
        promo_code_request = _looks_like_promo_code_request(
            message_text,
            client_slug=client_slug,
        )
    if not promo_code_request:
        return reply
    discounts_policy = policy_pack.get("discounts") if isinstance(policy_pack, dict) else None
    promo_code = None
    if isinstance(discounts_policy, dict):
        for key in ("promo_code", "promoCode", "special_promo_code", "code"):
            raw = discounts_policy.get(key)
            if isinstance(raw, str) and raw.strip():
                promo_code = raw.strip()
                break
    if promo_code:
        return f"Сейчас действует промокод {promo_code}. {reply}"
    return f"Специальный промокод в правилах не указан. {reply}"


__all__ = [
    "_format_discounts_reply_for_message",
    "_looks_like_promo_code_request",
]
