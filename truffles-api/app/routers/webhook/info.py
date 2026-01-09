"""Truth-gate/info bundle helpers and info-response composition."""

from __future__ import annotations

import re
from typing import Any


def _tokenize_for_matching(normalized: str) -> list[str]:
    return re.findall(r"\w+", normalized)


def _is_short_reply(message_text: str | None) -> bool:
    if not message_text:
        return False
    from . import _legacy as legacy

    normalized = legacy.normalize_for_matching(message_text)
    if not normalized:
        return False
    tokens = _tokenize_for_matching(normalized)
    return 0 < len(tokens) <= legacy.SESSION_MEMORY_SHORT_TOKENS


def _has_token_prefix(tokens: list[str], prefix: str) -> bool:
    return any(token.startswith(prefix) for token in tokens)


def _anchor_group_hit(tokens: list[str], group: tuple[str, ...]) -> bool:
    return all(_has_token_prefix(tokens, prefix) for prefix in group)


def _count_anchor_hits(tokens: list[str], groups: list[tuple[str, ...]]) -> int:
    hits = 0
    for group in groups:
        if _anchor_group_hit(tokens, group):
            hits += 1
    return hits


def _detect_info_anchor_hits(tokens: list[str]) -> dict[str, int]:
    from . import _legacy as legacy

    hits: dict[str, int] = {}
    for intent in legacy.INFO_INTENTS:
        groups = legacy.INFO_ANCHOR_GROUPS.get(intent)
        if not groups:
            continue
        count = _count_anchor_hits(tokens, groups)
        if count:
            hits[intent] = count
    return hits


def _detect_info_class_intents(
    message_text: str | None,
    *,
    intent_decomp_set: set[str],
) -> tuple[set[str], dict[str, Any]]:
    from . import _legacy as legacy

    intents = {intent for intent in intent_decomp_set if intent in legacy.INFO_INTENTS}
    meta: dict[str, Any] = {}
    normalized = legacy.normalize_for_matching(message_text) if message_text else ""
    if not normalized:
        return intents, meta

    tokens = _tokenize_for_matching(normalized)
    anchor_hits = _detect_info_anchor_hits(tokens)
    anchor_intents = {intent for intent, count in anchor_hits.items() if count > 0}
    question_like = "?" in (message_text or "")
    if not question_like and tokens:
        question_like = any(_has_token_prefix(tokens, prefix) for prefix in legacy.QUESTION_WORD_PREFIXES)
    short_query = 0 < len(tokens) <= 4

    parking_signal = any(
        token in normalized
        for token in [
            "парков",
            "паркинг",
            "во дворе",
            "двор",
            "авто",
            "машин",
            "машины",
            "машину",
        ]
    ) or ("мест" in normalized and ("авто" in normalized or "машин" in normalized or "машины" in normalized))
    guest_signal = any(
        token in normalized
        for token in [
            "гост",
            "ребен",
            "ребён",
            "дет",
            "коляс",
            "ожидан",
            "подожд",
            "пораньше",
            "раньше",
        ]
    )
    if "подруг" in normalized:
        guest_context = any(
            token in normalized
            for token in [
                "можно",
                "прийти",
                "приду",
                "привед",
                "посид",
                "подожд",
                "ожидан",
                "хочу",
                "хотел",
            ]
        )
        guest_context = guest_context or bool(
            re.search(r"\bс\s+подруг|\bсо\s+подруг", normalized)
        )
        guest_signal = guest_signal or guest_context
    location_signal = parking_signal or guest_signal or any(
        token in normalized
        for token in ["адрес", "где вы", "где находитесь", "куда ехать", "локац", "как доехать"]
    )
    hours_signal = any(
        token in normalized
        for token in ["работае", "до скольк", "во скольк", "график", "открыт", "сейчас открыты", "когда откры"]
    )

    if "location" in anchor_intents and (question_like or short_query or intent_decomp_set):
        location_signal = True
    if "hours" in anchor_intents and (question_like or short_query or intent_decomp_set):
        hours_signal = True

    if location_signal:
        intents.add("location")
    if hours_signal:
        intents.add("hours")
    question_type = None
    try:
        question_type = legacy.semantic_question_type(message_text, include_kinds=legacy.INFO_INTENTS)
    except Exception:
        question_type = None
    if question_type and question_type.kind in legacy.INFO_INTENTS:
        intents.add(question_type.kind)
        meta["question_type"] = question_type.kind
        meta["question_type_score"] = question_type.score
    anchor_boost = question_like or short_query or bool(intent_decomp_set) or bool(question_type)
    if anchor_intents and anchor_boost:
        intents.update(anchor_intents)
        meta["anchor_intents"] = sorted(anchor_intents)
        meta["anchor_hits"] = anchor_hits
        meta["anchor_boost"] = anchor_boost
    meta["info_signals"] = {
        "parking": parking_signal,
        "guest": guest_signal,
        "location": location_signal,
        "hours": hours_signal,
    }
    return intents, meta


def _looks_like_info_query(message_text: str | None) -> bool:
    intents, meta = _detect_info_class_intents(message_text, intent_decomp_set=set())
    if intents:
        return True
    info_signals = meta.get("info_signals") if isinstance(meta, dict) else None
    if isinstance(info_signals, dict):
        return any(
            info_signals.get(signal)
            for signal in ("parking", "guest", "location", "hours")
        )
    return False


def _build_info_intent_reply(
    intent: str,
    *,
    service_query: str | None,
    client_slug: str | None,
    message_text: str | None = None,
    include_info_bundle: bool = True,
) -> tuple[str | None, dict | None]:
    from app.services.demo_salon_knowledge import (
        build_info_combined_reply,
        format_reply_from_truth,
        get_demo_salon_decision,
        get_demo_salon_service_hint,
    )

    from . import _legacy as legacy

    normalized = legacy.normalize_for_matching(message_text) if message_text else ""
    parking_signal = "парков" in normalized if normalized else False
    guest_signal = False
    if normalized:
        guest_signal = any(
            token in normalized
            for token in [
                "гост",
                "ребен",
                "ребён",
                "дет",
                "коляс",
                "ожидан",
                "пораньше",
                "раньше",
                "подожд",
                "заранее",
            ]
        )
        if "подруг" in normalized:
            guest_context = any(
                token in normalized
                for token in [
                    "можно",
                    "прийти",
                    "приду",
                    "привед",
                    "посид",
                    "подожд",
                    "ожидан",
                    "хочу",
                    "хотел",
                ]
            )
            guest_context = guest_context or bool(
                re.search(r"\bс\s+подруг|\bсо\s+подруг", normalized)
            )
            guest_signal = guest_signal or guest_context
    location_signal = False
    if normalized:
        location_signal = any(token in normalized for token in ["адрес", "где вы", "где наход", "где вы находитесь"])
    include_info_bundle = include_info_bundle and (
        intent in {"location", "hours"} or location_signal or parking_signal or guest_signal
    )

    if intent == "hours":
        reply, meta = build_info_combined_reply(
            include_parking=parking_signal,
            include_guest=guest_signal,
        )
        return reply, meta or None
    if intent == "location":
        reply, meta = build_info_combined_reply(
            include_parking=parking_signal,
            include_guest=guest_signal,
        )
        return reply, meta or None
    if (
        intent in {"pricing", "duration"}
        and not service_query
        and message_text
        and client_slug == "demo_salon"
    ):
        service_query = get_demo_salon_service_hint(message_text)
    if intent == "pricing":
        question = f"Сколько стоит {service_query}?" if service_query else "Сколько стоит?"
    elif intent == "duration":
        question = f"Сколько длится {service_query}?" if service_query else "Сколько длится?"
    else:
        return None, None
    info_prefix: str | None = None
    info_meta: dict | None = None
    if include_info_bundle:
        info_prefix, info_meta = build_info_combined_reply(
            include_parking=parking_signal,
            include_guest=guest_signal,
        )
    decision = get_demo_salon_decision(question, client_slug=client_slug)
    if decision and decision.action == "reply" and decision.response:
        meta = decision.meta if isinstance(decision.meta, dict) else {}
        if info_meta:
            meta = {**info_meta, **meta}
        reply_text = decision.response
        if info_prefix:
            reply_text = f"{info_prefix} {reply_text}".strip()
        return reply_text, meta or None
    fallback = format_reply_from_truth("duration_or_price_clarify")
    if info_prefix:
        fallback = f"{info_prefix} {fallback}".strip() if fallback else info_prefix
    meta = info_meta or None
    return fallback, meta


def _extract_truth_gate_info_intents(
    message_text: str,
    *,
    policy_handler: dict | None,
    policy_type: str | None,
    client_slug: str | None,
    intent_decomp: dict | None,
) -> list[str]:
    if not message_text or not policy_handler:
        return []
    truth_gate = policy_handler.get("truth_gate")
    if not truth_gate:
        return []
    if policy_type == "demo_salon":
        decision = truth_gate(message_text, client_slug=client_slug, intent_decomp=intent_decomp)
    else:
        decision = truth_gate(message_text)
    if not decision or getattr(decision, "action", None) != "reply":
        return []
    intent = getattr(decision, "intent", None)
    if not isinstance(intent, str):
        return []
    intent_key = intent.strip().casefold()
    if intent_key == "hours":
        return ["hours"]
    if intent_key == "location" or intent_key.startswith("location_"):
        return ["location"]
    return []


__all__ = [
    "_anchor_group_hit",
    "_build_info_intent_reply",
    "_count_anchor_hits",
    "_detect_info_anchor_hits",
    "_detect_info_class_intents",
    "_extract_truth_gate_info_intents",
    "_has_token_prefix",
    "_is_short_reply",
    "_looks_like_info_query",
    "_tokenize_for_matching",
]
