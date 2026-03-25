"""Neutral runtime adapter for non-demo packs.

The adapter provides a deterministic, pack-agnostic fallback contract
without importing demo-specific knowledge modules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.services.knowledge_runtime import get_runtime_truth
from app.services.pack_compiler_service import compile_pack_payload
from app.services.pack_runtime_types import PackDecision

_KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parents[1] / "knowledge"
_DEFAULT_CLIENT_SLUG = "generic"
_PROMO_MARKERS = ("акци", "скидк", "промо", "бонус", "special offer")
_PRICE_QUESTION_PATTERNS = (
    re.compile(r"\bскольк\w*(?:\s+\w+){0,2}\s+сто(?:ит|ят)\b"),
    re.compile(r"\bкак(?:ая|ова)?\s+цен\w*\b"),
)
_DURATION_QUESTION_PATTERNS = (
    re.compile(r"\bскольк\w*(?:\s+\w+){0,3}\s+(?:длит|заним)\w*\b"),
    re.compile(r"\bкак(?:\s+\w+){0,2}\s+долг\w*\b"),
)


@dataclass(frozen=True)
class SemanticServiceMatch:
    action: str
    response: str
    score: float
    canonical_name: str | None = None
    suggestions: list[str] | None = None


@dataclass(frozen=True)
class SemanticQuestionType:
    kind: str
    score: float
    second_score: float


def _normalize_client_slug(client_slug: str | None) -> str:
    slug = str(client_slug or _DEFAULT_CLIENT_SLUG).strip().lower()
    return slug or _DEFAULT_CLIENT_SLUG


def _client_knowledge_dir(client_slug: str | None) -> Path:
    return _KNOWLEDGE_BASE_DIR / _normalize_client_slug(client_slug)


def _truth_path(client_slug: str | None) -> Path:
    return _client_knowledge_dir(client_slug) / "SALON_TRUTH.yaml"


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


@lru_cache(maxsize=64)
def _load_yaml_truth_cached(client_slug: str | None = _DEFAULT_CLIENT_SLUG) -> dict:
    raw = _load_yaml(_truth_path(client_slug))
    if not raw:
        return {}
    try:
        compiled = compile_pack_payload(raw)
    except Exception:
        compiled = None
    effective = compiled.get("effective_pack") if isinstance(compiled, dict) else None
    return effective if isinstance(effective, dict) else raw


def _merge_truth_overlay(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in overlay.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _merge_truth_overlay(existing, value)
        else:
            merged[key] = value
    return merged


def load_yaml_truth(client_slug: str | None = _DEFAULT_CLIENT_SLUG) -> dict:
    runtime_truth = get_runtime_truth()
    if runtime_truth is not None:
        runtime_allow_fallback = bool(runtime_truth.allow_fallback)
        runtime_slug = runtime_truth.client_slug
        if runtime_slug and client_slug:
            normalized = _normalize_client_slug(client_slug)
            if normalized and normalized != runtime_slug:
                if not runtime_allow_fallback:
                    return {}
                return _load_yaml_truth_cached(client_slug)
        if isinstance(runtime_truth.truth, dict):
            if runtime_allow_fallback:
                fallback_truth = _load_yaml_truth_cached(client_slug)
                if not runtime_truth.truth:
                    return fallback_truth
                return _merge_truth_overlay(fallback_truth, runtime_truth.truth)
            return runtime_truth.truth
        if not runtime_allow_fallback:
            return {}
    truth = _load_yaml_truth_cached(client_slug)
    if truth:
        return truth
    if _normalize_client_slug(client_slug) != _DEFAULT_CLIENT_SLUG:
        return _load_yaml_truth_cached(_DEFAULT_CLIENT_SLUG)
    return {}


def load_policy_pack(client_slug: str | None = _DEFAULT_CLIENT_SLUG) -> dict:
    truth = load_yaml_truth(client_slug)
    client_pack = truth.get("client_pack") if isinstance(truth, dict) else None
    policy = client_pack.get("policy") if isinstance(client_pack, dict) else None
    if isinstance(policy, dict):
        return policy
    root_policy = truth.get("policy") if isinstance(truth, dict) else None
    return root_policy if isinstance(root_policy, dict) else {}


def _flatten_lexicon_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        items: list[str] = []
        for nested in value.values():
            items.extend(_flatten_lexicon_values(nested))
        return items
    if isinstance(value, list):
        items: list[str] = []
        for nested in value:
            items.extend(_flatten_lexicon_values(nested))
        return items
    if isinstance(value, str):
        cleaned = value.strip().lower()
        return [cleaned] if cleaned else []
    return []


@lru_cache(maxsize=1)
def load_system_lexicons() -> dict:
    path = _KNOWLEDGE_BASE_DIR / "generic" / "SYSTEM_LEXICONS.yaml"
    payload = _load_yaml(path)
    return payload if isinstance(payload, dict) else {}


def get_system_lexicon_list(key: str) -> list[str]:
    lexicons = load_system_lexicons()
    if not isinstance(lexicons, dict):
        return []
    values = _flatten_lexicon_values(lexicons.get(key))
    seen: set[str] = set()
    result: list[str] = []
    for token in values:
        if token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result


def get_signal_lexicon_list(client_slug: str | None, key: str) -> list[str]:
    truth = load_yaml_truth(client_slug)
    client_pack = truth.get("client_pack") if isinstance(truth, dict) else None
    signals = client_pack.get("signals") if isinstance(client_pack, dict) else None
    payload_values = _flatten_lexicon_values(signals.get(key) if isinstance(signals, dict) else None)
    if payload_values:
        return payload_values
    return get_system_lexicon_list(key)


def _normalize_anchor_groups(value: Any) -> list[tuple[str, ...]]:
    groups: list[tuple[str, ...]] = []
    if not isinstance(value, dict):
        return groups
    for lang_groups in value.values():
        if not isinstance(lang_groups, list):
            continue
        for group in lang_groups:
            if isinstance(group, (list, tuple)):
                tokens = [str(item).strip().lower() for item in group if str(item).strip()]
                if tokens:
                    groups.append(tuple(tokens))
    return groups


@lru_cache(maxsize=32)
def get_system_anchor_groups(intent: str) -> list[tuple[str, ...]]:
    lexicons = load_system_lexicons()
    groups = lexicons.get("info_anchor_groups") if isinstance(lexicons, dict) else None
    if not isinstance(groups, dict):
        return []
    return _normalize_anchor_groups(groups.get(intent))


def _normalize_text(text: str) -> str:
    value = str(text or "").strip().lower().replace("ё", "е")
    value = re.sub(r"[^\w\s:/.-]+", " ", value, flags=re.UNICODE)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _contains_any(text: str, tokens: list[str]) -> bool:
    if not text:
        return False
    return any(token and token in text for token in tokens)


def _contains_word(text: str, token: str) -> bool:
    return re.search(rf"\b{re.escape(token)}\b", text) is not None


def _contains_any_terms(
    text: str,
    tokens: list[str],
    *,
    exact_terms: set[str] | None = None,
    stem_terms: dict[str, str] | None = None,
) -> bool:
    if not text:
        return False
    words = [token for token in text.split() if token]
    exact_terms = {term.casefold() for term in (exact_terms or set()) if term}
    stem_terms = {
        str(term).casefold(): str(stem).casefold()
        for term, stem in (stem_terms or {}).items()
        if term and stem
    }
    for token in tokens:
        candidate = str(token or "").strip().casefold()
        if not candidate:
            continue
        if any(char.isspace() for char in candidate):
            if candidate in text:
                return True
            continue
        if candidate in exact_terms:
            if any(word == candidate for word in words):
                return True
            continue
        stem = stem_terms.get(candidate, candidate)
        if any(word.startswith(stem) for word in words):
            return True
    return False


def _has_price_signal(
    normalized: str,
    raw_text: str | None = None,
    *,
    client_slug: str | None = None,
) -> bool:
    text = normalized or _normalize_text(raw_text or "")
    if _contains_any_terms(
        text,
        get_signal_lexicon_list(client_slug, "price_keywords"),
        exact_terms={"почем", "скок", "скока"},
        stem_terms={"цена": "цен", "стоимость": "стоимост"},
    ):
        return True
    return any(pattern.search(text) for pattern in _PRICE_QUESTION_PATTERNS)


def _has_duration_signal(
    normalized: str,
    message: str | None = None,
    *,
    client_slug: str | None = None,
) -> bool:
    text = normalized or _normalize_text(message or "")
    if _contains_any(text, get_signal_lexicon_list(client_slug, "duration_keywords")):
        return True
    if any(pattern.search(text) for pattern in _DURATION_QUESTION_PATTERNS):
        return True
    if "время на" in text and get_pack_service_hint(message or "", client_slug=client_slug):
        return True
    return False


def _has_parking_signal(normalized: str, *, client_slug: str | None = None) -> bool:
    return _contains_any(normalized, ["парков", "паркинг", "стоян", "тұрақ"])


def _has_guest_waiting_signal(normalized: str, *, client_slug: str | None = None) -> bool:
    return _contains_any(normalized, ["ожид", "гост", "сопровожд", "күту"])


def _has_contact_signal(
    normalized: str,
    raw_text: str | None = None,
    *,
    client_slug: str | None = None,
) -> bool:
    text = normalized or _normalize_text(raw_text or "")
    return _contains_any(text, ["тел", "номер", "whatsapp", "wa", "instagram", "инст"])


def _matches_service_request_lexicon(normalized: str, client_slug: str) -> bool:
    return _contains_any(normalized, get_signal_lexicon_list(client_slug, "service_question_keywords"))


def _detect_promotion_intent(normalized: str, *, client_slug: str | None = None) -> str | None:
    if _contains_any(normalized, list(_PROMO_MARKERS)):
        return "promotions"
    return None


def _service_entries(truth: dict | None) -> list[dict[str, Any]]:
    if not isinstance(truth, dict):
        return []
    containers = [
        truth.get("services_catalog"),
        (truth.get("client_pack") or {}).get("services_catalog")
        if isinstance(truth.get("client_pack"), dict)
        else None,
    ]
    for container in containers:
        if isinstance(container, list):
            return [item for item in container if isinstance(item, dict)]
        if isinstance(container, dict):
            items = container.get("items") or container.get("services")
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
    return []


def _match_service(normalized: str, client_slug: str) -> dict | None:
    truth = load_yaml_truth(client_slug)
    if not normalized:
        return None
    query_tokens = set(normalized.split())
    if not query_tokens:
        return None
    best: tuple[int, dict[str, Any]] | None = None
    for item in _service_entries(truth):
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        name_tokens = set(_normalize_text(name).split())
        overlap = len(query_tokens & name_tokens)
        if overlap <= 0:
            continue
        if best is None or overlap > best[0]:
            best = (overlap, item)
    return best[1] if best else None


def _build_fact_meta(
    *,
    fact_source: str,
    fact_intents: list[str] | None = None,
    meta: dict[str, Any] | None = None,
    service_query_meta: dict[str, Any] | None = None,
    info_sections: list[str] | None = None,
    price_item: dict[str, Any] | None = None,
    duration_item: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = dict(meta or {})
    payload["fact_source"] = fact_source
    if fact_intents:
        payload["fact_intents"] = [item for item in fact_intents if isinstance(item, str)]
    if service_query_meta:
        payload.update({k: v for k, v in service_query_meta.items() if v is not None})
    if info_sections:
        payload["info_sections"] = [item for item in info_sections if isinstance(item, str)]
    if price_item is not None:
        payload["price_item"] = price_item
    if duration_item is not None:
        payload["duration_item"] = duration_item
    return payload


def _format_service_not_found_reply(truth: dict) -> str | None:
    return format_reply_from_truth("service_clarify", truth=truth)


def _format_hours_line(salon: dict[str, Any]) -> str | None:
    hours = salon.get("hours")
    if not isinstance(hours, dict):
        return None
    open_at = hours.get("open")
    close_at = hours.get("close")
    days = hours.get("days")
    if isinstance(open_at, str) and isinstance(close_at, str):
        days_part = f" ({days})" if isinstance(days, str) and days.strip() else ""
        return f"Мы работаем с {open_at} до {close_at}{days_part}."
    return None


def format_reply_from_truth(
    intent: str,
    slots: dict | None = None,
    *,
    client_slug: str | None = _DEFAULT_CLIENT_SLUG,
    truth: dict | None = None,
) -> str | None:
    source_truth = truth if isinstance(truth, dict) else load_yaml_truth(client_slug)
    if not isinstance(source_truth, dict):
        return None
    normalized_intent = str(intent or "").strip().lower()
    salon = source_truth.get("salon") if isinstance(source_truth.get("salon"), dict) else {}
    system_messages = (
        source_truth.get("system_messages")
        if isinstance(source_truth.get("system_messages"), dict)
        else {}
    )
    if normalized_intent == "location":
        address = salon.get("address")
        return address.strip() if isinstance(address, str) and address.strip() else None
    if normalized_intent == "hours":
        return _format_hours_line(salon)
    if normalized_intent == "parking":
        parking = salon.get("parking")
        if isinstance(parking, str) and parking.strip():
            return parking.strip()
        return None
    if normalized_intent == "services_overview":
        summary = salon.get("services_summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
        names = [
            str(item.get("name")).strip()
            for item in _service_entries(source_truth)
            if isinstance(item.get("name"), str) and str(item.get("name")).strip()
        ]
        if names:
            return f"Мы предлагаем: {', '.join(names[:8])}."
        return None
    if normalized_intent == "service_clarify":
        clarify = source_truth.get("service_clarify")
        if isinstance(clarify, str) and clarify.strip():
            return clarify.strip()
        if isinstance(clarify, dict):
            reply = clarify.get("reply") or clarify.get("text")
            if isinstance(reply, str) and reply.strip():
                return reply.strip()
        return "Уточните, пожалуйста, какая услуга интересует."
    if normalized_intent == "duration_or_price_clarify":
        reply = source_truth.get("duration_or_price_clarify")
        if isinstance(reply, str) and reply.strip():
            return reply.strip()
        if isinstance(reply, dict):
            text = reply.get("reply") or reply.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
        return "Подскажите услугу, и я уточню цену и длительность."
    if normalized_intent == "promotions":
        promotions = source_truth.get("promotions")
        if isinstance(promotions, str) and promotions.strip():
            return promotions.strip()
        if isinstance(promotions, dict):
            for key in ("reply", "summary", "text"):
                value = promotions.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None
    if normalized_intent == "off_topic":
        reply = system_messages.get("off_topic")
        if isinstance(reply, str) and reply.strip():
            return reply.strip()
        return "Подскажу по услугам, времени записи и контактам."
    if normalized_intent == "system_error":
        reply = system_messages.get("system_error")
        if isinstance(reply, str) and reply.strip():
            return reply.strip()
        return "Не удалось обработать запрос. Попробуйте уточнить формулировку."
    if normalized_intent == "service_duration":
        service_name = (slots or {}).get("service") if isinstance(slots, dict) else None
        if isinstance(service_name, str) and service_name.strip():
            return f"Длительность {service_name.strip()} зависит от мастера. Уточню после выбора времени."
        return None
    return None


def build_info_combined_reply(
    *,
    include_parking: bool = False,
    include_guest: bool = False,
    client_slug: str | None = _DEFAULT_CLIENT_SLUG,
) -> tuple[str | None, dict[str, Any]]:
    sections: list[str] = []
    parts: list[str] = []
    for intent in ("location", "hours"):
        reply = format_reply_from_truth(intent, client_slug=client_slug)
        if isinstance(reply, str) and reply.strip():
            parts.append(reply.strip())
            sections.append(intent)
    if include_parking:
        parking = format_reply_from_truth("parking", client_slug=client_slug)
        if isinstance(parking, str) and parking.strip():
            parts.append(parking.strip())
            sections.append("parking")
    if include_guest:
        sections.append("guest_policy")
    if not parts:
        return None, {"info_sections": sections}
    return " ".join(parts), {"info_sections": sections}


def build_quiet_hours_notice(
    *,
    now_utc: datetime | None = None,
    now_local: datetime | None = None,
    client_slug: str | None = _DEFAULT_CLIENT_SLUG,
) -> str | None:
    del now_utc, now_local, client_slug
    return None


def build_evening_greeting(
    *,
    now_utc: datetime | None = None,
    now_local: datetime | None = None,
    client_slug: str | None = _DEFAULT_CLIENT_SLUG,
) -> str | None:
    reference = now_local
    if reference is None:
        reference = now_utc or datetime.now(timezone.utc)
    hour = reference.hour
    if 18 <= hour <= 23:
        return "Добрый вечер!"
    return None


def semantic_question_type(
    text: str,
    *,
    include_kinds: set[str] | None = None,
    return_multi: bool = False,
    client_slug: str | None = _DEFAULT_CLIENT_SLUG,
) -> SemanticQuestionType | list[SemanticQuestionType] | None:
    normalized = _normalize_text(text)
    kinds = include_kinds or {"pricing", "duration"}
    matched: list[SemanticQuestionType] = []
    if "pricing" in kinds and _has_price_signal(normalized, text, client_slug=client_slug):
        matched.append(SemanticQuestionType(kind="pricing", score=1.0, second_score=0.0))
    if "duration" in kinds and _has_duration_signal(normalized, text, client_slug=client_slug):
        matched.append(SemanticQuestionType(kind="duration", score=1.0, second_score=0.0))
    if return_multi:
        return matched
    return matched[0] if matched else None


def semantic_service_match(text: str, client_slug: str) -> SemanticServiceMatch | None:
    normalized = _normalize_text(text)
    match = _match_service(normalized, client_slug)
    if not isinstance(match, dict):
        return None
    name = match.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    return SemanticServiceMatch(
        action="reply",
        response=f"Да, услуга {name.strip()} доступна.",
        score=1.0,
        canonical_name=name.strip(),
        suggestions=None,
    )


def compose_multi_truth_reply(
    message: str,
    client_slug: str | None,
    intent_decomp: dict | None = None,
    *,
    return_meta: bool = False,
):
    normalized = _normalize_text(message)
    intents: list[str] = []
    replies: list[str] = []
    if _has_price_signal(normalized, message, client_slug=client_slug):
        intents.append("pricing")
    if _has_duration_signal(normalized, message, client_slug=client_slug):
        intents.append("duration")
    if _contains_any(normalized, get_signal_lexicon_list(client_slug, "hours_keywords")):
        intents.append("hours")
    if _contains_any(normalized, get_signal_lexicon_list(client_slug, "location_keywords")):
        intents.append("location")
    for intent in intents:
        reply = format_reply_from_truth(intent, client_slug=client_slug)
        if isinstance(reply, str) and reply.strip():
            replies.append(reply.strip())
    if not replies and isinstance(intent_decomp, dict):
        primary = intent_decomp.get("primary_intent")
        if isinstance(primary, str):
            reply = format_reply_from_truth(primary, client_slug=client_slug)
            if isinstance(reply, str) and reply.strip():
                replies.append(reply.strip())
                intents.append(primary)
    result = " ".join(dict.fromkeys(replies)) if replies else None
    meta = _build_fact_meta(
        fact_source="neutral_pack",
        fact_intents=list(dict.fromkeys(intents)),
        info_sections=list(dict.fromkeys(intents)),
    )
    if return_meta:
        return result, meta
    return result


def get_pack_decision(
    message: str,
    *,
    client_slug: str | None = None,
    intent_decomp: dict | None = None,
) -> PackDecision:
    reply, meta = compose_multi_truth_reply(
        message,
        client_slug,
        intent_decomp,
        return_meta=True,
    )
    if isinstance(reply, str) and reply.strip():
        intents = meta.get("fact_intents") if isinstance(meta, dict) else None
        intent = intents[0] if isinstance(intents, list) and intents else None
        return PackDecision(action="reply", response=reply, intent=intent, meta=meta)
    fallback = format_reply_from_truth("off_topic", client_slug=client_slug)
    response = fallback or "Подскажу по услугам салона и записи."
    return PackDecision(action="reply", response=response, intent="other", meta={"fact_source": "neutral_pack"})


def get_pack_service_decision(
    message: str,
    *,
    client_slug: str | None = None,
    intent_decomp: dict | None = None,
) -> PackDecision:
    normalized = _normalize_text(message)
    match = _match_service(normalized, _normalize_client_slug(client_slug))
    if isinstance(match, dict):
        name = match.get("name")
        if isinstance(name, str) and name.strip():
            return PackDecision(
                action="reply",
                response=f"{name.strip()} доступна. Подскажите удобные дату и время.",
                intent="service_query",
                meta={"service_query": name.strip(), "fact_source": "neutral_pack"},
            )
    return PackDecision(
        action="reply",
        response=format_reply_from_truth("service_clarify", client_slug=client_slug)
        or "Уточните, пожалуйста, какую услугу хотите выбрать.",
        intent="service_clarify",
        meta={"fact_source": "neutral_pack"},
    )


def get_pack_price_reply(message: str, *, client_slug: str | None = None) -> str | None:
    del message
    return format_reply_from_truth("pricing", client_slug=client_slug)


def get_pack_price_item(message: str, *, client_slug: str | None = None) -> str | None:
    del message, client_slug
    return None


def get_pack_service_hint(message: str, *, client_slug: str | None = None) -> str | None:
    normalized = _normalize_text(message)
    match = _match_service(normalized, _normalize_client_slug(client_slug))
    if isinstance(match, dict):
        name = match.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def phrase_match_intent(text: str, client_slug: str | None = _DEFAULT_CLIENT_SLUG) -> set[str]:
    normalized = _normalize_text(text)
    intents: set[str] = set()
    if _has_price_signal(normalized, text, client_slug=client_slug):
        intents.add("pricing")
    if _has_duration_signal(normalized, text, client_slug=client_slug):
        intents.add("duration")
    if _contains_any(normalized, get_signal_lexicon_list(client_slug, "hours_keywords")):
        intents.add("hours")
    if _contains_any(normalized, get_signal_lexicon_list(client_slug, "location_keywords")):
        intents.add("location")
    return intents


__all__ = [
    "SemanticQuestionType",
    "SemanticServiceMatch",
    "_build_fact_meta",
    "_detect_promotion_intent",
    "_format_service_not_found_reply",
    "_has_contact_signal",
    "_has_duration_signal",
    "_has_guest_waiting_signal",
    "_has_parking_signal",
    "_has_price_signal",
    "_match_service",
    "_matches_service_request_lexicon",
    "_normalize_client_slug",
    "_normalize_text",
    "build_evening_greeting",
    "build_info_combined_reply",
    "build_quiet_hours_notice",
    "compose_multi_truth_reply",
    "format_reply_from_truth",
    "get_pack_decision",
    "get_pack_price_item",
    "get_pack_price_reply",
    "get_pack_service_decision",
    "get_pack_service_hint",
    "get_signal_lexicon_list",
    "get_system_anchor_groups",
    "get_system_lexicon_list",
    "load_policy_pack",
    "load_system_lexicons",
    "load_yaml_truth",
    "phrase_match_intent",
    "semantic_question_type",
    "semantic_service_match",
]
