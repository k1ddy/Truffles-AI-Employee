from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, time, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import yaml

from app.logging_config import get_logger
from app.services.knowledge_service import get_embedding
from app.services.pack_compiler_service import compile_pack_payload

_KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parents[1] / "knowledge"
_DEFAULT_CLIENT_SLUG = "demo_salon"


def _normalize_client_slug(client_slug: str | None) -> str:
    slug = str(client_slug or _DEFAULT_CLIENT_SLUG).strip()
    return slug or _DEFAULT_CLIENT_SLUG


def _client_knowledge_dir(client_slug: str | None) -> Path:
    return _KNOWLEDGE_BASE_DIR / _normalize_client_slug(client_slug)


def _truth_path(client_slug: str | None) -> Path:
    return _client_knowledge_dir(client_slug) / "SALON_TRUTH.yaml"


def _intents_path(client_slug: str | None) -> Path:
    base = _client_knowledge_dir(client_slug)
    slug = _normalize_client_slug(client_slug)
    candidates = [
        base / f"INTENTS_PHRASES_{slug.upper()}.yaml",
        base / f"INTENTS_PHRASES_{slug}.yaml",
        base / "INTENTS_PHRASES.yaml",
        base / "INTENTS_PHRASES_DEMO_SALON.yaml",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[-1]
_SERVICES_COLLECTION = "services_index"

_SERVICE_MATCH_THRESHOLD = float(os.environ.get("SERVICE_SEMANTIC_MATCH_THRESHOLD", "0.40"))
_SERVICE_SUGGEST_THRESHOLD = float(os.environ.get("SERVICE_SEMANTIC_SUGGEST_THRESHOLD", "0.25"))
_SERVICE_SUGGEST_LIMIT = int(os.environ.get("SERVICE_SEMANTIC_SUGGEST_LIMIT", "3"))
_SERVICE_QUERY_SEMANTIC_THRESHOLD = float(os.environ.get("SERVICE_QUERY_SEMANTIC_THRESHOLD", "0.72"))
_QUESTION_TYPE_THRESHOLD = float(os.environ.get("QUESTION_TYPE_SEMANTIC_THRESHOLD", "0.55"))
_QUESTION_TYPE_MARGIN = float(os.environ.get("QUESTION_TYPE_SEMANTIC_MARGIN", "0.08"))
_QDRANT_HOST = os.environ.get("QDRANT_HOST", "http://qdrant:6333")
_QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
CONSULT_CLARIFY_TEXT = "Я могу помочь по услугам салона. Какая услуга интересует?"

logger = get_logger("demo_salon_knowledge")


@dataclass(frozen=True)
class DemoSalonDecision:
    action: str
    response: str
    intent: str | None = None
    collect: list[str] | None = None
    meta: dict[str, Any] | None = None


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


FACT_META_KEYS = (
    "fact_source",
    "fact_intents",
    "service_query",
    "service_query_source",
    "price_item",
    "duration_item",
    "info_sections",
)

INFO_SECTION_INTENT_MAP = {
    "address": "location",
    "hours": "hours",
    "parking": "parking",
    "guest_policy": "guest_policy",
}


def _normalize_fact_intents(
    fact_intents: list[str] | None,
    info_sections: list[str] | None,
) -> list[str] | None:
    intents: list[str] = []
    if isinstance(fact_intents, list):
        for item in fact_intents:
            if not isinstance(item, str):
                continue
            cleaned = item.strip()
            if cleaned and cleaned not in intents:
                intents.append(cleaned)
    if isinstance(info_sections, list):
        for section in info_sections:
            if not isinstance(section, str):
                continue
            key = section.strip().casefold()
            if not key:
                continue
            intent = INFO_SECTION_INTENT_MAP.get(key, key)
            if intent and intent not in intents:
                intents.append(intent)
    return intents or None


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
    combined: dict[str, Any] = {}
    if isinstance(meta, dict):
        combined.update(meta)
    existing_intents = (
        combined.get("fact_intents") if isinstance(combined.get("fact_intents"), list) else []
    )
    merged_intents: list[str] = []
    if isinstance(existing_intents, list):
        merged_intents.extend(existing_intents)
    if isinstance(fact_intents, list):
        merged_intents.extend(fact_intents)
    if isinstance(service_query_meta, dict):
        for key in ("service_query", "service_query_source", "service_query_score"):
            if key in service_query_meta and combined.get(key) is None:
                combined[key] = service_query_meta.get(key)
    if info_sections is None and isinstance(combined.get("info_sections"), list):
        info_sections = combined.get("info_sections")
    if info_sections is not None:
        combined["info_sections"] = [item for item in info_sections if isinstance(item, str)]
    combined["fact_source"] = fact_source
    combined["fact_intents"] = _normalize_fact_intents(
        merged_intents,
        combined.get("info_sections") if isinstance(combined.get("info_sections"), list) else None,
    )
    if price_item is not None:
        combined["price_item"] = price_item
    if duration_item is not None:
        combined["duration_item"] = duration_item
    for key in FACT_META_KEYS:
        if key not in combined:
            combined[key] = None
    return combined


def _build_truth_decision(
    *,
    response: str,
    intent: str,
    meta: dict[str, Any] | None = None,
    service_query_meta: dict[str, Any] | None = None,
    price_item: dict[str, Any] | None = None,
    duration_item: str | None = None,
) -> DemoSalonDecision:
    fact_meta = _build_fact_meta(
        meta=meta,
        fact_source="truth",
        fact_intents=[intent],
        service_query_meta=service_query_meta,
        price_item=price_item,
        duration_item=duration_item,
    )
    return DemoSalonDecision(
        action="reply",
        response=response,
        intent=intent,
        meta=fact_meta,
    )


def _price_item_payload(price_item: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(price_item, dict):
        return None
    item = price_item.get("item")
    return item if isinstance(item, dict) else None


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    normalized = text.casefold().replace("ё", "е")
    normalized = re.sub(r"\[.*?\]", " ", normalized)
    normalized = normalized.replace("гель-лак", "гель лак").replace("гельлак", "гель лак")
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _split_question_segments(text: str) -> list[str]:
    if not text:
        return []
    segments = [segment.strip() for segment in re.split(r"[?!\.,;]+", text) if segment.strip()]
    if segments:
        return segments
    cleaned = text.strip()
    return [cleaned] if cleaned else []


def _normalize_consult_label(value: str) -> str:
    cleaned = str(value or "").replace("_", " ").strip()
    return _normalize_text(cleaned)


def _clean_consult_value(value: Any, max_words: int) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned:
        return None
    tokens = cleaned.split()
    if len(tokens) > max_words:
        cleaned = " ".join(tokens[:max_words])
    return cleaned or None


@lru_cache(maxsize=4)
def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


_SYSTEM_LEXICONS_PATH = _KNOWLEDGE_BASE_DIR / "generic" / "SYSTEM_LEXICONS.yaml"


def load_system_lexicons() -> dict:
    return _load_yaml(_SYSTEM_LEXICONS_PATH)


def _coerce_string_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        items = value
    elif isinstance(value, str):
        items = [value]
    else:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, str):
            item = str(item)
        cleaned = item.strip()
        if not cleaned:
            continue
        normalized_value = _normalize_text(cleaned)
        if not normalized_value:
            continue
        key = normalized_value.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(normalized_value)
    return normalized


def _merge_lang_map(value: Any) -> list[str]:
    if isinstance(value, dict):
        merged: list[str] = []
        for items in value.values():
            merged.extend(_coerce_string_list(items))
        return _coerce_string_list(merged)
    return _coerce_string_list(value)


@lru_cache(maxsize=128)
def get_system_lexicon_list(key: str) -> list[str]:
    lexicons = load_system_lexicons()
    if not isinstance(lexicons, dict):
        return []
    return _merge_lang_map(lexicons.get(key))


def _load_signal_lexicons(truth: dict | None) -> dict[str, Any]:
    if not isinstance(truth, dict):
        return {}
    domain_pack = truth.get("domain_pack")
    if not isinstance(domain_pack, dict):
        return {}
    signal_lexicons = domain_pack.get("signal_lexicons")
    return signal_lexicons if isinstance(signal_lexicons, dict) else {}


@lru_cache(maxsize=256)
def _signal_lexicon_list_cached(client_slug: str, key: str) -> list[str]:
    truth = load_yaml_truth(client_slug)
    signal_lexicons = _load_signal_lexicons(truth)
    if key in signal_lexicons:
        return _merge_lang_map(signal_lexicons.get(key))
    return get_system_lexicon_list(key)


def get_signal_lexicon_list(client_slug: str | None, key: str) -> list[str]:
    slug = _normalize_client_slug(client_slug)
    return _signal_lexicon_list_cached(slug, key)


def _normalize_anchor_groups(value: Any) -> list[tuple[str, ...]]:
    groups: list[tuple[str, ...]] = []

    def _add_group(group: Any) -> None:
        if isinstance(group, (list, tuple, set)):
            prefixes = _coerce_string_list(list(group))
            if prefixes:
                groups.append(tuple(prefixes))
            return
        if isinstance(group, str):
            prefixes = _coerce_string_list(group)
            if prefixes:
                groups.append(tuple(prefixes))

    if isinstance(value, dict):
        for lang_groups in value.values():
            if isinstance(lang_groups, list):
                for group in lang_groups:
                    _add_group(group)
        return groups
    if isinstance(value, list):
        for group in value:
            _add_group(group)
    return groups


@lru_cache(maxsize=64)
def get_system_anchor_groups(intent: str) -> list[tuple[str, ...]]:
    lexicons = load_system_lexicons()
    if not isinstance(lexicons, dict):
        return []
    groups = lexicons.get("info_anchor_groups")
    if not isinstance(groups, dict):
        return []
    return _normalize_anchor_groups(groups.get(intent))

@lru_cache(maxsize=8)
def load_yaml_truth(client_slug: str | None = _DEFAULT_CLIENT_SLUG) -> dict:
    raw = _load_yaml(_truth_path(client_slug))
    if not raw:
        return {}
    compiled = compile_pack_payload(raw)
    effective = compiled.get("effective_pack") if isinstance(compiled, dict) else None
    return effective if isinstance(effective, dict) else raw


def load_policy_pack(client_slug: str | None = _DEFAULT_CLIENT_SLUG) -> dict:
    truth = load_yaml_truth(client_slug)
    client_pack = truth.get("client_pack") if isinstance(truth, dict) else None
    policy = client_pack.get("policy") if isinstance(client_pack, dict) else None
    return policy if isinstance(policy, dict) else {}


_TIME_PATTERN = re.compile(r"^(\d{1,2})[:.](\d{2})$")


def get_salon_timezone(
    truth: dict | None = None,
    *,
    client_slug: str | None = _DEFAULT_CLIENT_SLUG,
) -> str | None:
    truth = truth if isinstance(truth, dict) else load_yaml_truth(client_slug)
    salon = truth.get("salon") if isinstance(truth, dict) else None
    if not isinstance(salon, dict):
        return None
    timezone_name = salon.get("timezone")
    if isinstance(timezone_name, str) and timezone_name.strip():
        timezone_name = timezone_name.strip()
        try:
            ZoneInfo(timezone_name)
        except Exception:
            return None
        return timezone_name
    return None


def _parse_hours_time(value: str | None) -> time | None:
    if not isinstance(value, str):
        return None
    match = _TIME_PATTERN.match(value.strip())
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour > 23 or minute > 59:
        return None
    return time(hour=hour, minute=minute)


def _resolve_local_now(
    *,
    timezone_name: str | None,
    now_utc: datetime | None = None,
    now_local: datetime | None = None,
) -> datetime:
    tz = timezone.utc
    if isinstance(timezone_name, str) and timezone_name.strip():
        try:
            tz = ZoneInfo(timezone_name.strip())
        except Exception:
            tz = timezone.utc
    if now_local is not None:
        return now_local.replace(tzinfo=tz) if now_local.tzinfo is None else now_local
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    return now_utc.astimezone(tz)


def build_quiet_hours_notice(
    *,
    now_utc: datetime | None = None,
    now_local: datetime | None = None,
    client_slug: str | None = _DEFAULT_CLIENT_SLUG,
) -> str | None:
    truth = load_yaml_truth(client_slug)
    salon = truth.get("salon") if isinstance(truth, dict) else None
    if not isinstance(salon, dict):
        return None
    hours = salon.get("hours") if isinstance(salon, dict) else None
    if not isinstance(hours, dict):
        return None
    open_time = _parse_hours_time(hours.get("open"))
    close_time = _parse_hours_time(hours.get("close"))
    if not open_time or not close_time:
        return None
    timezone_name = get_salon_timezone(truth, client_slug=client_slug)
    if not timezone_name:
        return None
    now_local = _resolve_local_now(
        timezone_name=timezone_name,
        now_utc=now_utc,
        now_local=now_local,
    )
    current_time = now_local.time()
    if open_time <= close_time:
        is_quiet = current_time < open_time or current_time >= close_time
    else:
        is_quiet = close_time <= current_time < open_time
    if not is_quiet:
        return None
    days = hours.get("days") or ""
    open_label = hours.get("open") or ""
    close_label = hours.get("close") or ""
    days_text = f"{days}, " if days else ""
    return (
        f"Сейчас салон закрыт. Работаем {days_text}с {open_label} до {close_label}. "
        "Оставьте вопрос — отвечу в рабочее время."
    )


def build_evening_greeting(
    *,
    now_utc: datetime | None = None,
    now_local: datetime | None = None,
    client_slug: str | None = _DEFAULT_CLIENT_SLUG,
) -> str | None:
    truth = load_yaml_truth(client_slug)
    timezone_name = get_salon_timezone(truth, client_slug=client_slug)
    if not timezone_name:
        return None
    now_local = _resolve_local_now(
        timezone_name=timezone_name,
        now_utc=now_utc,
        now_local=now_local,
    )
    if now_local.hour < 18:
        return None
    return "Добрый вечер. Это виртуальный ассистент салона."


def build_info_combined_reply(
    *,
    include_parking: bool = False,
    include_guest: bool = False,
    client_slug: str | None = _DEFAULT_CLIENT_SLUG,
) -> tuple[str | None, dict[str, Any]]:
    truth = load_yaml_truth(client_slug)
    salon = truth.get("salon") if isinstance(truth, dict) else None
    if not isinstance(salon, dict):
        return None, {}

    address = salon.get("address") if isinstance(salon, dict) else None
    hours = salon.get("hours") if isinstance(salon, dict) else None
    parking = salon.get("parking") if isinstance(salon, dict) else None
    guest_policy = truth.get("guest_policy") if isinstance(truth, dict) else None

    parts: list[str] = []
    sections: list[str] = []

    if isinstance(address, dict):
        full = address.get("full")
        entrance = address.get("entrance")
        address_parts = []
        if full:
            address_parts.append(f"Адрес: {full}.")
        if entrance:
            address_parts.append(str(entrance).strip())
        address_text = " ".join(address_parts).strip()
        if address_text:
            parts.append(address_text)
            sections.append("address")

    if isinstance(hours, dict):
        days = hours.get("days")
        open_label = hours.get("open")
        close_label = hours.get("close")
        hours_parts = ["Работаем"]
        if days:
            hours_parts.append(str(days).strip())
        if open_label or close_label:
            window = ""
            if open_label and close_label:
                window = f"с {open_label} до {close_label}"
            elif open_label:
                window = f"с {open_label}"
            elif close_label:
                window = f"до {close_label}"
            if window:
                hours_parts.append(window)
        hours_text = " ".join(hours_parts).strip()
        if hours_text:
            parts.append(hours_text if hours_text.endswith(".") else f"{hours_text}.")
            sections.append("hours")

    if include_parking and isinstance(parking, dict):
        details = parking.get("details")
        parking_text = details or "Есть парковка рядом с салоном."
        if parking_text:
            parts.append(f"Парковка: {parking_text if parking_text.endswith('.') else f'{parking_text}.'}")
            sections.append("parking")

    if include_guest and isinstance(guest_policy, dict):
        guest_parts = [
            guest_policy.get("allowed_guests"),
            guest_policy.get("animals"),
            guest_policy.get("guest_limit"),
            guest_policy.get("early_arrival"),
            guest_policy.get("children_rules"),
            guest_policy.get("alcohol_policy"),
            guest_policy.get("food_drink_policy"),
        ]
        guest_text = " ".join([str(item).strip() for item in guest_parts if isinstance(item, str) and item.strip()])
        if guest_text:
            parts.append(guest_text if guest_text.endswith(".") else f"{guest_text}.")
            sections.append("guest_policy")

    if not parts:
        return None, {}
    reply = " ".join(parts)
    meta = _build_fact_meta(
        meta={"info_combined": True, "info_sections": sections},
        fact_source="truth",
        info_sections=sections,
    )
    return reply, meta


def load_intents_phrases(client_slug: str | None = _DEFAULT_CLIENT_SLUG) -> dict:
    data = _load_yaml(_intents_path(client_slug))
    if not isinstance(data, dict):
        return {}
    slug = _normalize_client_slug(client_slug)
    for key in (f"{slug}_intents", "intents", "demo_salon_intents"):
        intents = data.get(key)
        if isinstance(intents, dict):
            return intents
    return {}


def _load_consult_playbooks(client_slug: str | None = _DEFAULT_CLIENT_SLUG) -> list[dict[str, Any]]:
    truth = load_yaml_truth(client_slug)
    domain_pack = truth.get("domain_pack") if isinstance(truth, dict) else None
    playbooks = domain_pack.get("consult_playbooks") if isinstance(domain_pack, dict) else None
    if not isinstance(playbooks, list):
        return []
    return [item for item in playbooks if isinstance(item, dict)]


@lru_cache(maxsize=16)
def _build_phrase_index(client_slug: str) -> dict[str, list[str]]:
    intents = load_intents_phrases(client_slug)
    index: dict[str, list[str]] = {}
    for intent, phrases in intents.items():
        if isinstance(phrases, list):
            normalized = [_normalize_text(str(phrase)) for phrase in phrases if str(phrase).strip()]
            index[intent] = [p for p in normalized if p]
    return index


def phrase_match_intent(text: str, client_slug: str | None = _DEFAULT_CLIENT_SLUG) -> set[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return set()
    matches: set[str] = set()
    slug = _normalize_client_slug(client_slug)
    for intent, phrases in _build_phrase_index(slug).items():
        for phrase in phrases:
            if not phrase:
                continue
            if len(phrase) <= 3:
                if re.search(rf"\b{re.escape(phrase)}\b", normalized):
                    matches.add(intent)
                    break
                continue
            if phrase in normalized:
                matches.add(intent)
                break
    return matches


def _flatten_offtopic_phrases(client_slug: str | None) -> list[str]:
    intents = load_intents_phrases(client_slug)
    offtopic = intents.get("offtopic_examples") if isinstance(intents, dict) else None
    if not isinstance(offtopic, dict):
        return []
    phrases: list[str] = []
    for group in offtopic.values():
        if isinstance(group, list):
            phrases.extend(group)
    normalized = [_normalize_text(str(item)) for item in phrases if str(item).strip()]
    return [p for p in normalized if p]


@lru_cache(maxsize=16)
def _offtopic_phrases(client_slug: str) -> list[str]:
    return _flatten_offtopic_phrases(client_slug)


def _format_money(value: Any) -> str:
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{amount:,}".replace(",", " ")


def _tokenize(text: str) -> list[str]:
    normalized = _normalize_text(text)
    return [token for token in normalized.split() if token]


_SERVICE_STOPWORDS = {
    "и",
    "или",
    "на",
    "по",
    "за",
    "до",
    "от",
    "для",
    "у",
    "в",
    "во",
    "к",
    "с",
    "со",
}


def _normalize_alias_tokens(text: str) -> list[str]:
    tokens = _tokenize(text)
    return [token for token in tokens if token and token not in _SERVICE_STOPWORDS]


@lru_cache(maxsize=16)
def _build_price_index(client_slug: str) -> list[dict[str, Any]]:
    truth = load_yaml_truth(client_slug)
    items: list[dict[str, Any]] = []
    for category in truth.get("price_list", []) if isinstance(truth, dict) else []:
        for item in category.get("items", []) if isinstance(category, dict) else []:
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            tokens = _tokenize(name)
            if not tokens:
                continue
            items.append(
                {
                    "name": name,
                    "tokens": tokens,
                    "item": item,
                }
            )
    return items


@lru_cache(maxsize=16)
def _build_price_name_index(client_slug: str) -> dict[str, dict[str, Any]]:
    truth = load_yaml_truth(client_slug)
    index: dict[str, dict[str, Any]] = {}
    for category in truth.get("price_list", []) if isinstance(truth, dict) else []:
        for item in category.get("items", []) if isinstance(category, dict) else []:
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            index[_normalize_text(name)] = item
    return index


@lru_cache(maxsize=16)
def _build_service_index(client_slug: str) -> list[dict[str, Any]]:
    truth = load_yaml_truth(client_slug)
    catalog = truth.get("services_catalog") if isinstance(truth, dict) else None
    services = catalog.get("services") if isinstance(catalog, dict) else None
    if not isinstance(services, list):
        return []

    index: list[dict[str, Any]] = []
    for service in services:
        if not isinstance(service, dict):
            continue
        name = str(service.get("name", "")).strip()
        if not name:
            continue
        aliases: list[str] = [name]
        extra_aliases = service.get("aliases")
        if isinstance(extra_aliases, list):
            aliases.extend([str(alias) for alias in extra_aliases if str(alias).strip()])

        alias_tokens: list[list[str]] = []
        for alias in aliases:
            tokens = _normalize_alias_tokens(alias)
            if tokens:
                alias_tokens.append(tokens)

        price_items = service.get("price_items")
        index.append(
            {
                "name": name,
                "aliases": alias_tokens,
                "quick_price_key": str(service.get("quick_price_key")).strip()
                if service.get("quick_price_key")
                else None,
                "price_items": [str(item) for item in price_items if str(item).strip()]
                if isinstance(price_items, list)
                else [],
                "description": str(service.get("description", "")).strip() or None,
                "duration_text": str(service.get("duration_text", "")).strip() or None,
            }
        )
    return index


@lru_cache(maxsize=16)
def _service_tokens(client_slug: str) -> set[str]:
    tokens: set[str] = set()
    for entry in _build_service_index(client_slug):
        for alias in entry.get("aliases", []):
            tokens.update(alias)
    return tokens


def _message_has_service_token(normalized: str, client_slug: str) -> bool:
    if not normalized:
        return False
    message_tokens = normalized.split()
    for token in _service_tokens(client_slug):
        if _token_matches(token, message_tokens):
            return True
    return False


def _is_offtopic_message(normalized: str, client_slug: str) -> bool:
    if not normalized:
        return False
    if any(phrase and phrase in normalized for phrase in _offtopic_phrases(client_slug)):
        return True
    return _signal_contains_any(normalized, client_slug, "offtopic_keywords")


def _match_service(normalized: str, client_slug: str) -> dict[str, Any] | None:
    if not normalized:
        return None
    message_tokens = normalized.split()
    best = None
    best_len = 0
    for entry in _build_service_index(client_slug):
        for alias_tokens in entry.get("aliases", []):
            if not alias_tokens:
                continue
            if all(_token_matches(token, message_tokens) for token in alias_tokens):
                if len(alias_tokens) > best_len:
                    best = entry
                    best_len = len(alias_tokens)
    return best


def _token_matches(token: str, message_tokens: list[str]) -> bool:
    for msg in message_tokens:
        if msg == token:
            return True
        if len(token) >= 4 and len(msg) >= 4:
            if msg.startswith(token) or token.startswith(msg):
                return True
        if len(token) >= 6 and len(msg) >= 6:
            common = 0
            for a, b in zip(token, msg):
                if a != b:
                    break
                common += 1
            if common >= 5:
                return True
    return False


def _find_best_price_item(message: str, client_slug: str) -> dict[str, Any] | None:
    normalized = _normalize_text(message)
    if not normalized:
        return None
    message_tokens = normalized.split()
    best = None
    best_len = 0
    for entry in _build_price_index(client_slug):
        tokens = entry["tokens"]
        if not tokens:
            continue
        if all(_token_matches(token, message_tokens) for token in tokens):
            if len(tokens) > best_len:
                best = entry
                best_len = len(tokens)
    return best


def _contains_any(normalized: str, keywords: list[str]) -> bool:
    return any(keyword in normalized for keyword in keywords)


def _signal_contains_any(normalized: str, client_slug: str | None, key: str) -> bool:
    phrases = get_signal_lexicon_list(client_slug, key)
    return bool(phrases) and _contains_any(normalized, phrases)


def _signal_contains_any_words(normalized: str, client_slug: str | None, key: str) -> bool:
    words = get_signal_lexicon_list(client_slug, key)
    return bool(words) and _contains_any_words(normalized, words)


def _signal_contains_all(normalized: str, client_slug: str | None, key: str) -> bool:
    terms = get_signal_lexicon_list(client_slug, key)
    return bool(terms) and all(term in normalized for term in terms)


def _has_services_overview_signal(normalized: str, truth: dict | None) -> bool:
    if not normalized or not isinstance(truth, dict):
        return False
    domain_pack = truth.get("domain_pack")
    lexicon = domain_pack.get("services_overview_lexicon") if isinstance(domain_pack, dict) else None
    if not isinstance(lexicon, dict):
        return False
    for lang_key in ("ru", "kk"):
        phrases = lexicon.get(lang_key)
        if not isinstance(phrases, list):
            continue
        for phrase in phrases:
            if not isinstance(phrase, str):
                continue
            candidate = _normalize_text(phrase)
            if candidate and candidate in normalized:
                return True
    return False


def _contains_word(normalized: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", normalized) is not None


def _matches_service_request_lexicon(normalized: str, client_slug: str) -> bool:
    if not normalized:
        return False
    truth = load_yaml_truth(_normalize_client_slug(client_slug))
    domain_pack = truth.get("domain_pack") if isinstance(truth, dict) else None
    lexicon = domain_pack.get("service_request_lexicon") if isinstance(domain_pack, dict) else None
    if not isinstance(lexicon, dict):
        return False
    for lang_key in ("ru", "kk"):
        phrases = lexicon.get(lang_key)
        if not isinstance(phrases, list):
            continue
        for phrase in phrases:
            if not isinstance(phrase, str):
                continue
            candidate = _normalize_text(phrase)
            if candidate and candidate in normalized:
                return True
    return False


def _matches_guest_policy_lexicon(normalized: str, client_slug: str) -> bool:
    if not normalized:
        return False
    truth = load_yaml_truth(_normalize_client_slug(client_slug))
    domain_pack = truth.get("domain_pack") if isinstance(truth, dict) else None
    lexicon = domain_pack.get("guest_policy_lexicon") if isinstance(domain_pack, dict) else None
    if not isinstance(lexicon, dict):
        return False
    for lang_key in ("ru", "kk"):
        phrases = lexicon.get(lang_key)
        if not isinstance(phrases, list):
            continue
        for phrase in phrases:
            if not isinstance(phrase, str):
                continue
            candidate = _normalize_text(phrase)
            if candidate and candidate in normalized:
                return True
    return False


def _contains_any_words(normalized: str, words: list[str]) -> bool:
    return any(_contains_word(normalized, word) for word in words)


def _collect_consult_triggers(playbook: dict[str, Any]) -> list[str]:
    raw = playbook.get("triggers")
    items: list[str] = []
    if isinstance(raw, list):
        items.extend(raw)
    elif isinstance(raw, dict):
        for key in ("ru", "kk", "any", "all"):
            values = raw.get(key)
            if isinstance(values, list):
                items.extend(values)
    aliases = playbook.get("aliases")
    if isinstance(aliases, list):
        items.extend(aliases)
    normalized = [_normalize_text(str(item)) for item in items if str(item).strip()]
    return [item for item in normalized if item]


def _consult_topic_matches(playbook: dict[str, Any], consult_topic: str) -> bool:
    if not consult_topic:
        return False
    target = _normalize_consult_label(consult_topic)
    if not target:
        return False
    for key in ("id", "topic"):
        value = playbook.get(key)
        if isinstance(value, str) and _normalize_consult_label(value) == target:
            return True
    aliases = playbook.get("aliases")
    if isinstance(aliases, list):
        for alias in aliases:
            if isinstance(alias, str) and _normalize_consult_label(alias) == target:
                return True
    return False


def _select_consult_playbook(
    message: str,
    consult_topic: str | None,
    playbooks: list[dict[str, Any]],
    *,
    allow_fallback: bool,
) -> dict[str, Any] | None:
    normalized = _normalize_text(message)
    if consult_topic:
        for playbook in playbooks:
            if _consult_topic_matches(playbook, consult_topic):
                return playbook
    if normalized:
        for playbook in playbooks:
            triggers = _collect_consult_triggers(playbook)
            if triggers and _contains_any(normalized, triggers):
                return playbook
    if allow_fallback:
        for playbook in playbooks:
            if playbook.get("fallback") is True:
                return playbook
    return None


def _ensure_question_mark(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""
    if cleaned.endswith("?"):
        return cleaned
    return f"{cleaned}?"


def _format_consult_reply(
    playbook: dict[str, Any],
    variant_seed: int | None = None,
) -> tuple[str, list[str], list[str]]:
    lead = str(playbook.get("lead") or "").strip()
    next_step = str(playbook.get("next_step") or "").strip()
    questions_raw = playbook.get("questions")
    options_raw = playbook.get("options")

    questions_items = questions_raw if isinstance(questions_raw, list) else []
    options_items = options_raw if isinstance(options_raw, list) else []

    questions = [
        _ensure_question_mark(str(item))
        for item in questions_items
        if isinstance(item, str) and item.strip()
    ]
    options = [
        str(item).strip()
        for item in options_items
        if isinstance(item, str) and item.strip()
    ]

    def _select_variants(items: list[str], limit: int, seed: int | None, offset: int = 0) -> list[str]:
        if not items or limit <= 0:
            return []
        if len(items) <= limit:
            return list(items)
        if seed is None:
            return items[:limit]
        start = (seed + offset) % len(items)
        return [items[(start + idx) % len(items)] for idx in range(limit)]

    selected_questions = _select_variants(questions, 2, variant_seed, offset=0)
    selected_options = _select_variants(options, 3, variant_seed, offset=7)

    lines: list[str] = []
    if lead:
        lines.append(lead)
    if selected_questions:
        lines.append(" ".join(selected_questions))
    if selected_options:
        lines.extend([f"- {option}" for option in selected_options])
    if next_step:
        lines.append(next_step)

    reply = "\n".join(line for line in lines if line)
    return reply, selected_questions, selected_options


def _should_skip_consult(
    normalized: str,
    raw_text: str | None = None,
    *,
    client_slug: str | None = None,
) -> bool:
    if not normalized:
        return True
    if _has_price_signal(normalized, raw_text, client_slug=client_slug):
        return True
    if _has_duration_signal(normalized, raw_text, client_slug=client_slug):
        return True
    if _looks_like_hours_question(normalized, client_slug=client_slug):
        return True
    if _signal_contains_any(normalized, client_slug, "consult_skip_address_phrases"):
        return True
    return False


def _looks_like_hours_question(normalized: str, *, client_slug: str | None = None) -> bool:
    if not normalized:
        return False
    if _signal_contains_any(normalized, client_slug, "hours_question_phrases"):
        return True
    if _signal_contains_any_words(normalized, client_slug, "hours_question_words"):
        return not _message_has_service_token(normalized, _normalize_client_slug(client_slug))
    if _signal_contains_any(normalized, client_slug, "hours_question_work_verbs"):
        return True
    if _signal_contains_any(normalized, client_slug, "hours_question_work_singular") and _signal_contains_any(
        normalized,
        client_slug,
        "hours_question_subject_phrases",
    ):
        if _signal_contains_any(normalized, client_slug, "hours_question_time_phrases"):
            return True
    return False


def _has_parking_signal(normalized: str, *, client_slug: str | None = None) -> bool:
    if not normalized:
        return False
    if _signal_contains_any(normalized, client_slug, "parking_direct_phrases"):
        return True
    machine_prefixes = get_signal_lexicon_list(client_slug, "parking_machine_prefixes")
    if machine_prefixes and any(prefix in normalized for prefix in machine_prefixes):
        exclude_phrases = get_signal_lexicon_list(client_slug, "parking_exclude_phrases")
        if exclude_phrases and not _contains_any(normalized, exclude_phrases):
            return False
    vehicle_words = get_signal_lexicon_list(client_slug, "parking_vehicle_words")
    if vehicle_words and _contains_any(normalized, vehicle_words):
        return True
    return False


def _has_address_hint(normalized: str, truth: dict | None) -> bool:
    if not normalized or not isinstance(truth, dict):
        return False
    address_full = truth.get("salon", {}).get("address", {}).get("full")
    if not isinstance(address_full, str) or not address_full.strip():
        return False
    for token in _normalize_text(address_full).split():
        if len(token) < 4 or token.isdigit():
            continue
        if token in normalized:
            return True
    return False


def _has_guest_waiting_signal(normalized: str, *, client_slug: str | None = None) -> bool:
    if not normalized:
        return False
    tokens = normalized.split()
    prefixes = get_signal_lexicon_list(client_slug, "guest_waiting_prefixes")
    if prefixes and any(token.startswith(prefix) for token in tokens for prefix in prefixes):
        return True
    return _signal_contains_any_words(normalized, client_slug, "guest_waiting_words")


def _has_price_signal(
    normalized: str,
    raw_text: str | None = None,
    *,
    client_slug: str | None = None,
) -> bool:
    if _signal_contains_any(normalized, client_slug, "price_keywords"):
        return True
    if _signal_contains_any(normalized, client_slug, "price_currency_words"):
        return True
    if raw_text and re.search(r"[₸$€₽]", raw_text):
        return True
    return False


def _has_duration_signal(
    normalized: str,
    raw_text: str | None = None,
    *,
    client_slug: str | None = None,
) -> bool:
    if not normalized:
        return False
    if _signal_contains_any(normalized, client_slug, "duration_keywords"):
        return True
    if re.search(r"\bзанимает\b", normalized):
        return True
    if raw_text:
        if _extract_minutes(raw_text) is not None:
            return True
        if re.search(r"\b(\d{1,2})\s*(?:час|часа|часов|ч)\b", raw_text, flags=re.IGNORECASE):
            return True
    return False


def _extract_minutes(text: str) -> int | None:
    match = re.search(r"\b(\d{1,3})\s*(?:мин|минут|м)\b", text, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def _format_price_reply(item: dict[str, Any]) -> str:
    name = item.get("name", "Услуга")
    if "price" in item:
        price = _format_money(item.get("price"))
        return f"{name} — {price} ₸."
    if "price_from" in item:
        price = _format_money(item.get("price_from"))
        return f"{name} — от {price} ₸."
    return f"{name} — уточните цену у администратора."


def _format_service_price_items(item_names: list[str], client_slug: str) -> str | None:
    if not item_names:
        return None
    index = _build_price_name_index(client_slug)
    replies: list[str] = []
    for name in item_names:
        item = index.get(_normalize_text(name))
        if item:
            replies.append(_format_price_reply(item))
    if replies:
        return " ".join(replies)
    return None


def _format_service_reply(service: dict[str, Any], truth: dict, client_slug: str) -> str | None:
    quick_key = service.get("quick_price_key")
    if quick_key:
        quick_answer = truth.get("price_quick_answers", {}).get(quick_key)
        if quick_answer:
            return quick_answer
    price_items = service.get("price_items") if isinstance(service, dict) else None
    reply = _format_service_price_items(price_items or [], client_slug)
    if reply:
        service_name = service.get("name") if isinstance(service, dict) else None
        if isinstance(service_name, str) and service_name.strip():
            if _normalize_text(service_name) not in _normalize_text(reply):
                reply = f"{service_name}: {reply}"
        return reply
    description = service.get("description") if isinstance(service, dict) else None
    if description:
        return description
    return None


def _format_service_not_found_reply(truth: dict) -> str | None:
    catalog = truth.get("services_catalog") if isinstance(truth, dict) else None
    template = None
    suggestions: list[str] = []
    if isinstance(catalog, dict):
        template = catalog.get("not_found_reply")
        suggestion_items = catalog.get("suggestions")
        if isinstance(suggestion_items, list):
            suggestions = [str(item) for item in suggestion_items if str(item).strip()]
    if not template:
        template = "В списке услуг нет такой позиции. Могу уточнить или предложить: {suggestions}."
    suggestions_text = ", ".join(suggestions)
    if "{suggestions}" in template:
        return template.format(suggestions=suggestions_text)
    if suggestions_text:
        return f"{template} {suggestions_text}."
    return template


def _format_service_suggestions_reply(suggestions: list[str], truth: dict) -> str | None:
    catalog = truth.get("services_catalog") if isinstance(truth, dict) else None
    template = None
    if isinstance(catalog, dict):
        template = catalog.get("not_found_reply")
    if not template:
        template = "В списке услуг нет такой позиции. Возможно, вы имели в виду: {suggestions}."
    suggestions_text = ", ".join(suggestions)
    if "{suggestions}" in template:
        return template.format(suggestions=suggestions_text)
    if suggestions_text:
        return f"{template} {suggestions_text}."
    return template


@lru_cache(maxsize=16)
def _question_type_examples(client_slug: str) -> dict[str, list[str]]:
    truth = load_yaml_truth(client_slug)
    domain_pack = truth.get("domain_pack") if isinstance(truth, dict) else None
    typical = domain_pack.get("typical_questions") if isinstance(domain_pack, dict) else None
    if not isinstance(typical, dict):
        return {}

    examples: dict[str, list[str]] = {}
    for kind in ("pricing", "duration", "hours"):
        phrases: list[str] = []
        block = typical.get(kind)
        if isinstance(block, dict):
            for items in block.values():
                if isinstance(items, list):
                    for phrase in items:
                        text = str(phrase).strip()
                        if text:
                            phrases.append(text)
        elif isinstance(block, list):
            for phrase in block:
                text = str(phrase).strip()
                if text:
                    phrases.append(text)
        examples[kind] = phrases
    return examples


def _coerce_embedding(raw: Any) -> list[float] | None:
    if not isinstance(raw, list) or not raw:
        return None
    try:
        return [float(value) for value in raw]
    except (TypeError, ValueError):
        return None


def _local_text_embedding(text: str, dim: int = 64) -> list[float]:
    normalized = _normalize_text(text)
    if not normalized:
        return []
    grams: list[str] = []
    if len(normalized) >= 3:
        for index in range(len(normalized) - 2):
            grams.append(normalized[index : index + 3])
    else:
        grams.append(normalized)
    vector = [0.0] * dim
    for gram in grams:
        digest = hashlib.sha256(gram.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector


@lru_cache(maxsize=32)
def _question_type_embeddings(client_slug: str, use_fallback: bool) -> dict[str, list[list[float]]]:
    examples = _question_type_examples(client_slug)
    embeddings: dict[str, list[list[float]]] = {}
    for kind, phrases in examples.items():
        vectors: list[list[float]] = []
        for phrase in phrases:
            vector: list[float] | None = None
            if use_fallback:
                vector = _local_text_embedding(phrase)
            else:
                try:
                    vector = _coerce_embedding(get_embedding(phrase))
                except Exception:
                    vector = None
            if vector:
                vectors.append(vector)
        if vectors:
            embeddings[kind] = vectors
    return embeddings


def _cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    if not vector_a or not vector_b:
        return 0.0
    dot = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_question_type(
    text: str,
    *,
    include_kinds: set[str] | None = None,
    return_multi: bool = False,
    client_slug: str | None = _DEFAULT_CLIENT_SLUG,
) -> SemanticQuestionType | list[SemanticQuestionType] | None:
    normalized = _normalize_text(text)
    if not normalized or len(normalized) < 3:
        return [] if return_multi else None

    slug = _normalize_client_slug(client_slug)
    if include_kinds is None:
        include_kinds = {"pricing", "duration"}

    if "duration" in include_kinds and _message_has_service_token(normalized, slug):
        duration_hint = _has_duration_signal(normalized, text, client_slug=slug)
        if not duration_hint and _signal_contains_any(normalized, slug, "duration_question_lead_terms"):
            duration_hint = _signal_contains_any_words(normalized, slug, "duration_time_units")
        if duration_hint:
            return SemanticQuestionType(kind="duration", score=1.0, second_score=0.0)

    query_vector = None
    use_fallback = False
    error_detail = None
    try:
        query_vector = _coerce_embedding(get_embedding(text))
    except Exception as exc:
        error_detail = str(exc)
        query_vector = None
    if not query_vector:
        use_fallback = True
        query_vector = _local_text_embedding(text)
        logger.warning(
            "question_type fallback to local embedding",
            extra={"context": {"error": error_detail or "embedding_unavailable"}},
        )

    examples = _question_type_embeddings(slug, use_fallback)
    if not examples and not use_fallback:
        use_fallback = True
        query_vector = _local_text_embedding(text)
        examples = _question_type_embeddings(slug, True)
        logger.warning(
            "question_type fallback to local embedding",
            extra={"context": {"error": "no_examples_with_bge"}},
        )
    if not examples:
        return None

    scores: dict[str, float] = {}
    for kind, vectors in examples.items():
        if kind not in include_kinds:
            continue
        best = 0.0
        for vector in vectors:
            score = _cosine_similarity(query_vector, vector)
            if score > best:
                best = score
        scores[kind] = best

    if not scores:
        return [] if return_multi else None

    def _pick_types(score_map: dict[str, float]) -> list[SemanticQuestionType]:
        if not score_map:
            return []
        sorted_scores = sorted(score_map.items(), key=lambda item: item[1], reverse=True)
        top_kind, top_score = sorted_scores[0]
        second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0
        if top_score < _QUESTION_TYPE_THRESHOLD:
            return []
        if return_multi:
            if len(sorted_scores) > 1 and (top_score - second_score) <= _QUESTION_TYPE_MARGIN:
                picked = sorted_scores[:2]
            else:
                picked = sorted_scores[:1]
        else:
            if (top_score - second_score) >= _QUESTION_TYPE_MARGIN:
                picked = sorted_scores[:1]
            else:
                return []
        return [
            SemanticQuestionType(kind=kind, score=score, second_score=second_score) for kind, score in picked
        ]

    picked = _pick_types(scores)
    if picked:
        return picked if return_multi else picked[0]

    if not use_fallback:
        fallback_vector = _local_text_embedding(text)
        fallback_examples = _question_type_embeddings(slug, True)
        fallback_scores: dict[str, float] = {}
        for kind, vectors in fallback_examples.items():
            if kind not in include_kinds:
                continue
            best = 0.0
            for vector in vectors:
                score = _cosine_similarity(fallback_vector, vector)
                if score > best:
                    best = score
            fallback_scores[kind] = best
        picked_fallback = _pick_types(fallback_scores)
        if return_multi:
            return picked_fallback
        return picked_fallback[0] if picked_fallback else None

    return [] if return_multi else None


def _format_service_duration_reply(
    service: dict[str, Any] | None,
    *,
    message: str | None = None,
    service_label: str | None = None,
    client_slug: str | None = _DEFAULT_CLIENT_SLUG,
) -> str:
    truth = load_yaml_truth(client_slug)
    catalog = truth.get("services_catalog") if isinstance(truth, dict) else None
    if service:
        duration_text = service.get("duration_text") if isinstance(service, dict) else None
        if isinstance(duration_text, str) and duration_text.strip():
            duration_text = duration_text.strip()
            name_override = None
            if message:
                price_items = service.get("price_items")
                if isinstance(price_items, list) and price_items:
                    price_item = _find_best_price_item(message, _normalize_client_slug(client_slug))
                    if isinstance(price_item, dict):
                        candidate = price_item.get("name")
                        if isinstance(candidate, str) and candidate.strip():
                            candidate = candidate.strip()
                            normalized_items = {
                                _normalize_text(str(item))
                                for item in price_items
                                if isinstance(item, str) and item.strip()
                            }
                            if _normalize_text(candidate) in normalized_items:
                                name_override = candidate
            label = service_label.strip() if isinstance(service_label, str) and service_label.strip() else None
            name = label or name_override or service.get("name") or "Услуга"
            suffix = "" if duration_text.endswith((".", "!", "?")) else "."
            return f"{name} — {duration_text}{suffix}"

    if isinstance(catalog, dict):
        clarify = catalog.get("duration_clarify")
        if isinstance(clarify, str) and clarify.strip():
            return clarify.strip()

    return "По времени зависит от услуги. Какая именно?"


def _select_presence_service_name(
    message: str,
    candidates: list[str],
    client_slug: str,
) -> str | None:
    if not message or not candidates:
        return None
    query_vector = _local_text_embedding(message)
    if not query_vector:
        return None
    best_name = None
    best_score = 0.0
    for candidate in candidates:
        service = _find_catalog_service_by_name(candidate, client_slug)
        if not service:
            continue
        name = service.get("name") if isinstance(service, dict) else None
        if not isinstance(name, str) or not name.strip():
            continue
        score = _cosine_similarity(query_vector, _local_text_embedding(name))
        if score > best_score:
            best_score = score
            best_name = name.strip()
    return best_name


def _format_service_presence_reply(
    message: str,
    match: SemanticServiceMatch | None,
    client_slug: str,
) -> str | None:
    if not message or not match:
        return None
    candidates: list[str] = []
    seen: set[str] = set()
    if isinstance(match.canonical_name, str) and match.canonical_name.strip():
        cleaned = match.canonical_name.strip()
        candidates.append(cleaned)
        seen.add(cleaned)
    if isinstance(match.suggestions, list):
        for suggestion in match.suggestions:
            if isinstance(suggestion, str):
                cleaned = suggestion.strip()
                if cleaned and cleaned not in seen:
                    candidates.append(cleaned)
                    seen.add(cleaned)
    service_name = _select_presence_service_name(message, candidates, client_slug)
    if not service_name:
        return None
    truth = load_yaml_truth(client_slug)
    catalog = truth.get("services_catalog") if isinstance(truth, dict) else None
    template = catalog.get("service_presence_reply") if isinstance(catalog, dict) else None
    if not isinstance(template, str) or not template.strip():
        return None
    template = template.strip()
    if "{service}" in template:
        return template.format(service=service_name)
    return f"{template} {service_name}."


def _format_service_presence_reply_for_name(
    service_name: str,
    client_slug: str,
) -> str | None:
    if not isinstance(service_name, str) or not service_name.strip():
        return None
    truth = load_yaml_truth(client_slug)
    catalog = truth.get("services_catalog") if isinstance(truth, dict) else None
    template = catalog.get("service_presence_reply") if isinstance(catalog, dict) else None
    if not isinstance(template, str) or not template.strip():
        return None
    template = template.strip()
    cleaned = service_name.strip()
    if "{service}" in template:
        return template.format(service=cleaned)
    return f"{template} {cleaned}."


def _find_catalog_service_by_name(name: str, client_slug: str) -> dict[str, Any] | None:
    if not name:
        return None
    needle = _normalize_text(name)
    for entry in _build_service_index(client_slug):
        if _normalize_text(entry.get("name") or "") == needle:
            return entry
    return None


def _format_semantic_service_reply(payload: dict, client_slug: str) -> str | None:
    canonical_name = payload.get("canonical_name") if isinstance(payload, dict) else None
    if isinstance(canonical_name, str) and canonical_name.strip():
        service = _find_catalog_service_by_name(canonical_name, client_slug)
        if service:
            reply = _format_service_reply(service, load_yaml_truth(client_slug), client_slug)
            if reply:
                return reply
        price_item = _build_price_name_index(client_slug).get(_normalize_text(canonical_name))
        if price_item:
            return _format_price_reply(price_item)

    price_item_payload = payload.get("price_item") if isinstance(payload, dict) else None
    if isinstance(price_item_payload, dict):
        return _format_price_reply(price_item_payload)
    return None


def _should_attempt_semantic_match(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    return len(normalized) >= 3


def _search_services_index(text: str, client_slug: str, limit: int) -> list[dict[str, Any]]:
    if not text or not client_slug:
        return []
    try:
        embedding = get_embedding(text)
    except Exception as exc:
        logger.warning("services_index embedding failed", extra={"context": {"error": str(exc)}})
        return []

    headers = {}
    if _QDRANT_API_KEY:
        headers["api-key"] = _QDRANT_API_KEY

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f"{_QDRANT_HOST}/collections/{_SERVICES_COLLECTION}/points/search",
                headers=headers,
                json={
                    "vector": embedding,
                    "limit": limit,
                    "score_threshold": 0.0,
                    "filter": {"must": [{"key": "client_slug", "match": {"value": client_slug}}]},
                    "with_payload": True,
                },
            )
    except Exception as exc:
        logger.warning("services_index search failed", extra={"context": {"error": str(exc)}})
        return []

    if response.status_code == 404:
        return []
    if response.status_code != 200:
        logger.warning(
            "services_index search failed",
            extra={"context": {"status": response.status_code, "body": response.text[:200]}},
        )
        return []

    data = response.json()
    results: list[dict[str, Any]] = []
    for point in data.get("result", []):
        payload = point.get("payload") if isinstance(point, dict) else None
        if not isinstance(payload, dict):
            continue
        results.append(
            {
                "score": float(point.get("score") or 0.0),
                "payload": payload,
            }
        )
    return results


def semantic_service_match(text: str, client_slug: str) -> SemanticServiceMatch | None:
    if not _should_attempt_semantic_match(text):
        return None
    results = _search_services_index(text, client_slug, _SERVICE_SUGGEST_LIMIT)
    if not results:
        return None

    top = results[0]
    score = float(top.get("score") or 0.0)
    normalized = _normalize_text(text)
    raw_text = text or ""
    if len(normalized.split()) <= 2 and "?" not in raw_text and score < 0.55:
        return None
    payload = top.get("payload") if isinstance(top.get("payload"), dict) else {}
    suggestions: list[str] = []
    for item in results:
        payload_item = item.get("payload") if isinstance(item.get("payload"), dict) else None
        name = payload_item.get("canonical_name") if isinstance(payload_item, dict) else None
        if isinstance(name, str) and name.strip():
            cleaned = name.strip()
            if cleaned not in suggestions:
                suggestions.append(cleaned)

    if score >= _SERVICE_MATCH_THRESHOLD:
        reply = _format_semantic_service_reply(payload, client_slug)
        if reply:
            return SemanticServiceMatch(
                action="match",
                response=reply,
                score=score,
                canonical_name=payload.get("canonical_name"),
                suggestions=suggestions,
            )

    if score >= _SERVICE_SUGGEST_THRESHOLD:
        reply = _format_service_suggestions_reply(suggestions or [], load_yaml_truth(client_slug))
        if reply:
            return SemanticServiceMatch(
                action="suggest",
                response=reply,
                score=score,
                canonical_name=payload.get("canonical_name"),
                suggestions=suggestions,
            )

    return None


def _extract_intent_decomp(intent_decomp: dict | None) -> tuple[set[str], str | None]:
    if not isinstance(intent_decomp, dict):
        return set(), None
    allowed = {"booking", "pricing", "duration", "location", "hours", "other"}
    intents: list[str] = []
    raw_intents = intent_decomp.get("intents")
    if isinstance(raw_intents, list):
        for item in raw_intents:
            if not isinstance(item, str):
                continue
            intent = item.strip().casefold()
            if intent in allowed and intent not in intents:
                intents.append(intent)
    if not intents:
        primary = intent_decomp.get("primary_intent")
        if isinstance(primary, str):
            primary = primary.strip().casefold()
            if primary in allowed:
                intents.append(primary)
        secondary = intent_decomp.get("secondary_intents")
        if isinstance(secondary, list):
            for item in secondary:
                if not isinstance(item, str):
                    continue
                intent = item.strip().casefold()
                if intent in allowed and intent not in intents:
                    intents.append(intent)
    service_query = intent_decomp.get("service_query")
    if isinstance(service_query, str):
        service_query = service_query.strip()
        if not service_query:
            service_query = None
    else:
        service_query = None
    return set(intents), service_query


def _clean_service_query(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned or len(cleaned) < 2:
        return None
    tokens = cleaned.split()
    if len(tokens) > 6:
        cleaned = " ".join(tokens[:6])
    return cleaned or None


def _resolve_service_query_meta(
    message: str,
    client_slug: str | None,
    intent_decomp: dict | None,
    *,
    require_query: bool,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "service_query": None,
        "service_query_source": "none",
        "service_query_score": 0.0,
    }

    def _explicit_service_query_from_message() -> str | None:
        if not message or not client_slug:
            return None
        slug = _normalize_client_slug(client_slug)
        normalized_message = _normalize_text(message)
        if not normalized_message:
            return None
        service = _match_service(normalized_message, slug)
        if isinstance(service, dict):
            name = _clean_service_query(service.get("name"))
            if name:
                return name
        price_item = _find_best_price_item(message, slug)
        if isinstance(price_item, dict):
            name = _clean_service_query(price_item.get("name"))
            if name:
                normalized_name = _normalize_text(name)
                if normalized_name and normalized_name in normalized_message:
                    return name
        return None

    if isinstance(intent_decomp, dict):
        cleaned = _clean_service_query(intent_decomp.get("service_query"))
        if cleaned:
            source_override = intent_decomp.get("service_query_source")
            score_override = intent_decomp.get("service_query_score")
            source = "intent_decomp"
            if isinstance(source_override, str) and source_override in {"intent_decomp", "context"}:
                source = source_override
            if source == "context":
                explicit_query = _explicit_service_query_from_message()
                if explicit_query:
                    meta["service_query"] = explicit_query
                    meta["service_query_source"] = "explicit_text"
                    meta["service_query_score"] = 1.0
                    return meta
            meta["service_query"] = cleaned
            meta["service_query_source"] = source
            if isinstance(score_override, (int, float)):
                meta["service_query_score"] = float(score_override)
            else:
                meta["service_query_score"] = 1.0
            return meta
    if require_query and message and client_slug:
        match = semantic_service_match(message, client_slug)
        if match and match.action == "match" and match.score >= _SERVICE_QUERY_SEMANTIC_THRESHOLD:
            candidate = match.canonical_name
            if not candidate and match.suggestions:
                candidate = match.suggestions[0]
            cleaned = _clean_service_query(candidate)
            if cleaned:
                meta["service_query"] = cleaned
                meta["service_query_source"] = "semantic_match"
                meta["service_query_score"] = match.score
        if not meta.get("service_query"):
            fallback_service = _match_service(
                _normalize_text(message),
                _normalize_client_slug(client_slug),
            )
            if isinstance(fallback_service, dict):
                fallback_name = _clean_service_query(fallback_service.get("name"))
                if fallback_name:
                    meta["service_query"] = fallback_name
                    meta["service_query_source"] = "semantic_match"
                    meta["service_query_score"] = 1.0
        price_item = _find_best_price_item(message, _normalize_client_slug(client_slug))
        if isinstance(price_item, dict):
            fallback_name = _clean_service_query(price_item.get("name"))
            if fallback_name:
                normalized_message = _normalize_text(message)
                normalized_candidate = _normalize_text(fallback_name)
                candidate_in_message = bool(
                    normalized_message
                    and normalized_candidate
                    and normalized_candidate in normalized_message
                )
                current_query = meta.get("service_query")
                current_tokens = _normalize_text(current_query).split() if current_query else []
                candidate_tokens = _normalize_text(fallback_name).split()
                if candidate_in_message or not current_query or len(candidate_tokens) > len(current_tokens):
                    meta["service_query"] = fallback_name
                    meta["service_query_source"] = "semantic_match"
                    meta["service_query_score"] = 1.0
    return meta


def _resolve_service_from_query(
    service_query: str | None,
    client_slug: str | None = _DEFAULT_CLIENT_SLUG,
) -> dict[str, Any] | None:
    if not service_query:
        return None
    normalized = _normalize_text(service_query)
    if not normalized:
        return None
    return _match_service(normalized, _normalize_client_slug(client_slug))


def compose_multi_truth_reply(
    message: str,
    client_slug: str | None,
    intent_decomp: dict | None = None,
    *,
    return_meta: bool = False,
) -> str | tuple[str, dict[str, Any]] | None:
    if not message or not client_slug:
        return None
    slug = _normalize_client_slug(client_slug)
    segments = _split_question_segments(message)
    if not segments:
        return None
    replies: list[str] = []
    seen: set[str] = set()
    resolved_intents: list[str] = []
    truth = load_yaml_truth(slug)
    intent_kinds, service_query = _extract_intent_decomp(intent_decomp)
    intent_kinds = {kind for kind in intent_kinds if kind in {"hours", "pricing", "duration"}}
    normalized_message = _normalize_text(message)
    if not intent_kinds and len(segments) < 2:
        signal_count = 0
        if _looks_like_hours_question(normalized_message, client_slug=slug):
            signal_count += 1
        if _has_price_signal(normalized_message, message):
            signal_count += 1
        if _has_duration_signal(normalized_message, message):
            signal_count += 1
        if signal_count < 2:
            return None
    if intent_kinds:
        if "hours" in intent_kinds:
            hours_like = any(
                _looks_like_hours_question(_normalize_text(seg), client_slug=slug) for seg in segments
            )
            if not hours_like:
                intent_kinds.discard("hours")
        if "pricing" in intent_kinds and not _has_price_signal(normalized_message, message):
            intent_kinds.discard("pricing")
        if "duration" in intent_kinds and not _has_duration_signal(normalized_message, message):
            intent_kinds.discard("duration")
    info_detected = bool(intent_kinds)
    needs_service_query = _has_price_signal(normalized_message, message) or _has_duration_signal(
        normalized_message, message
    )
    service_query_meta = _resolve_service_query_meta(
        message,
        slug,
        intent_decomp,
        require_query=needs_service_query,
    )
    service_query = service_query_meta.get("service_query")
    service_match_from_query = None
    service_from_query = None
    fallback_service_name_from_query = None
    if service_query:
        service_match_from_query = semantic_service_match(service_query, slug)
        service_from_query = _resolve_service_from_query(service_query, slug)
        if isinstance(service_from_query, dict):
            name = service_from_query.get("name")
            if isinstance(name, str) and name.strip():
                fallback_service_name_from_query = name.strip()
    for segment in segments:
        normalized_segment = _normalize_text(segment)
        if not normalized_segment:
            continue
        question_types = semantic_question_type(
            segment,
            include_kinds={"hours", "pricing", "duration"},
            return_multi=True,
            client_slug=slug,
        )
        if question_types is None:
            question_types = []
        elif not isinstance(question_types, list):
            question_types = [question_types]
        kinds = {
            question.kind
            for question in question_types
            if hasattr(question, "kind") and isinstance(getattr(question, "kind"), str)
        }
        if intent_kinds:
            kinds |= intent_kinds
        if "hours" in kinds and not _looks_like_hours_question(normalized_segment, client_slug=slug):
            kinds.discard("hours")
        if "pricing" in kinds and not _has_price_signal(normalized_segment, segment):
            kinds.discard("pricing")
        if "duration" in kinds and not _has_duration_signal(normalized_segment, segment):
            kinds.discard("duration")
        if _looks_like_hours_question(normalized_segment, client_slug=slug):
            kinds.add("hours")
        if _has_price_signal(normalized_segment, segment):
            kinds.add("pricing")
        if _has_duration_signal(normalized_segment, segment):
            kinds.add("duration")
        service_match = semantic_service_match(segment, slug)
        fallback_service = _match_service(normalized_segment, slug) if not service_match else None
        fallback_service_name = None
        if isinstance(fallback_service, dict):
            name = fallback_service.get("name")
            if isinstance(name, str) and name.strip():
                fallback_service_name = name.strip()
        if not fallback_service_name and fallback_service_name_from_query:
            fallback_service_name = fallback_service_name_from_query
        if kinds:
            info_detected = True

        def _mark_intent(intent_name: str) -> None:
            if intent_name not in resolved_intents:
                resolved_intents.append(intent_name)

        def _add_reply(text: str | None) -> None:
            if not text:
                return
            cleaned = text.strip()
            if not cleaned or cleaned in seen:
                return
            replies.append(cleaned)
            seen.add(cleaned)

        if "hours" in kinds:
            _add_reply(format_reply_from_truth("hours", client_slug=slug, truth=truth))
            _mark_intent("hours")
        if len(replies) >= 2:
            break
        if "pricing" in kinds:
            if not service_query:
                _add_reply(format_reply_from_truth("service_clarify", client_slug=slug, truth=truth))
            elif service_match_from_query and service_match_from_query.action == "match":
                _add_reply(service_match_from_query.response)
            else:
                fallback_reply = None
                if isinstance(service_from_query, dict):
                    fallback_reply = _format_service_reply(service_from_query, truth, slug)
                if fallback_reply:
                    _add_reply(fallback_reply)
                else:
                    _add_reply(format_reply_from_truth("service_clarify", client_slug=slug, truth=truth))
            _mark_intent("pricing")
        if len(replies) >= 2:
            break
        if "duration" in kinds:
            if not service_query:
                _add_reply(_format_service_duration_reply(None, message=segment, client_slug=slug))
            else:
                _add_reply(
                    _format_service_duration_reply(
                        service_from_query,
                        message=segment,
                        service_label=service_query,
                        client_slug=slug,
                    )
                )
            _mark_intent("duration")
        if len(replies) >= 2:
            break
        if (
            not needs_service_query
            and service_match
            and service_match.action == "match"
            and not {"pricing", "duration"} & kinds
        ):
            _add_reply(_format_service_presence_reply(segment, service_match, slug))
        elif not needs_service_query and fallback_service_name and not {"pricing", "duration"} & kinds:
            _add_reply(_format_service_presence_reply_for_name(fallback_service_name, slug))
        if len(replies) >= 2:
            break

    if not info_detected or len(replies) < 2:
        return None
    reply = "\n\n".join(replies[:2])
    if return_meta:
        info_sections = [
            intent
            for intent in resolved_intents
            if intent in {"address", "hours", "parking", "guest_policy"}
        ]
        meta = _build_fact_meta(
            meta=service_query_meta,
            fact_source="multi_truth",
            fact_intents=resolved_intents,
            service_query_meta=service_query_meta,
            info_sections=info_sections,
        )
        return reply, meta
    return reply


def _looks_like_service_question(
    normalized: str,
    raw_text: str | None = None,
    client_slug: str | None = _DEFAULT_CLIENT_SLUG,
) -> bool:
    if not normalized:
        return False
    slug = _normalize_client_slug(client_slug)
    if not _message_has_service_token(normalized, slug):
        if _signal_contains_any(normalized, slug, "booking_keywords"):
            return False
        if _looks_like_hours_question(normalized, client_slug=slug):
            return False
        if _has_parking_signal(normalized, client_slug=slug):
            return False
        if _signal_contains_any(normalized, slug, "service_question_location_phrases"):
            return False
        if _matches_service_request_lexicon(normalized, slug):
            return True
        return False
    if _has_price_signal(normalized, raw_text, client_slug=slug):
        return True
    if _signal_contains_any(normalized, slug, "service_question_keywords"):
        return True
    if _matches_service_request_lexicon(normalized, slug):
        return True
    if raw_text and "?" in raw_text:
        return True
    if _signal_contains_all(normalized, slug, "hair_color_terms"):
        return True
    return False


def _format_promotions(truth: dict, intent: str | None = None) -> str:
    promotions = truth.get("promotions") if isinstance(truth, dict) else {}
    items = promotions.get("items") if isinstance(promotions, dict) else []
    if not isinstance(items, list):
        items = []

    def _stacking_text() -> str:
        stacking = promotions.get("stacking")
        stacking_notes = promotions.get("stacking_notes")
        parts = [
            str(item).strip().rstrip(".")
            for item in (stacking, stacking_notes)
            if isinstance(item, str) and item.strip()
        ]
        if not parts:
            return " Скидки не суммируются."
        return " " + ". ".join(parts) + "."

    if intent == "promotion_first_visit":
        for promo in items:
            if "перв" in str(promo.get("name", "")).casefold():
                return (
                    f"На первое посещение действует скидка {promo.get('discount_percent')}% "
                    f"на услуги.{_stacking_text()}"
                )
    if intent == "promotion_birthday":
        for promo in items:
            if "именин" in str(promo.get("name", "")).casefold():
                return (
                    f"Именинникам скидка {promo.get('discount_percent')}% — "
                    "7 дней до/после даты рождения при документе."
                )
    if intent == "promotion_student":
        for promo in items:
            if "студент" in str(promo.get("name", "")).casefold() or "пенсион" in str(promo.get("name", "")).casefold():
                return (
                    f"Студентам/пенсионерам скидка {promo.get('discount_percent')}% "
                    "по будням 11:00–16:00 при документе."
                )

    parts = []
    for promo in items:
        name = promo.get("name")
        percent = promo.get("discount_percent")
        if name and percent:
            parts.append(f"{name}: {percent}%")
    if parts:
        return "Официальные акции: " + "; ".join(parts) + "." + _stacking_text()
    return "Скидки действуют только по официальным акциям."


def build_consult_reply(
    message: str,
    *,
    client_slug: str | None = "demo_salon",
    intent_decomp: dict | None = None,
    conversation_id: str | None = None,
    allow_service_query: bool = False,
) -> DemoSalonDecision | None:
    normalized = _normalize_text(message)
    slug = _normalize_client_slug(client_slug)
    consult_intent = False
    consult_topic = None
    consult_question = None
    intent_service_query = None
    if isinstance(intent_decomp, dict):
        consult_intent = intent_decomp.get("consult_intent") is True
        consult_topic = _clean_consult_value(intent_decomp.get("consult_topic"), 4)
        consult_question = _clean_consult_value(intent_decomp.get("consult_question"), 12)
        service_query = intent_decomp.get("service_query")
        if isinstance(service_query, str):
            intent_service_query = service_query.strip() or None

    has_service_query = bool(intent_service_query) or allow_service_query
    if not normalized or (
        _should_skip_consult(normalized, message, client_slug=slug) and not has_service_query
    ):
        return None

    if not consult_intent or not consult_topic:
        return None

    playbooks = _load_consult_playbooks(client_slug)
    if not playbooks:
        return None

    playbook = None
    for candidate in playbooks:
        if _consult_topic_matches(candidate, consult_topic):
            playbook = candidate
            break
    if not playbook:
        return None

    action_raw = playbook.get("action")
    action = str(action_raw).strip().lower() if isinstance(action_raw, str) else "reply"
    if action not in {"reply", "escalate"}:
        action = "reply"

    playbook_id = str(playbook.get("id") or playbook.get("topic") or "general").strip()
    consult_question_final = consult_question or _clean_consult_value(message, 12) or ""

    variant_key = f"{conversation_id}:{playbook_id}" if conversation_id else playbook_id
    variant_key = variant_key or "consult"
    variant_hash = hashlib.sha256(variant_key.encode("utf-8")).hexdigest()
    variant_id = variant_hash[:8]
    variant_seed = int(variant_id, 16)

    meta: dict[str, Any] = {
        "consult_intent": True,
        "consult_topic": playbook_id or "general",
        "consult_question": consult_question_final,
        "consult_playbook_id": playbook_id,
        "consult_variant_id": variant_id,
        "source": "pack",
    }

    if action == "escalate":
        escalation_message = str(playbook.get("escalation_message") or "").strip()
        return DemoSalonDecision(
            action="escalate",
            response=escalation_message,
            intent="consult_escalate",
            meta=meta,
        )

    reply, consult_questions, consult_options = _format_consult_reply(
        playbook,
        variant_seed=variant_seed,
    )
    if not reply:
        return None
    meta["consult_questions"] = consult_questions
    meta["consult_options"] = consult_options
    meta["tips_used"] = consult_options
    return DemoSalonDecision(
        action="reply",
        response=reply,
        intent="consult_reply",
        meta=meta,
    )


def format_reply_from_truth(
    intent: str,
    slots: dict | None = None,
    *,
    client_slug: str | None = _DEFAULT_CLIENT_SLUG,
    truth: dict | None = None,
) -> str | None:
    truth = truth if isinstance(truth, dict) else load_yaml_truth(client_slug)
    slots = slots or {}

    if intent in {"location", "hours", "parking"}:
        include_parking = intent == "parking"
        reply, _meta = build_info_combined_reply(
            include_parking=include_parking,
            client_slug=client_slug,
        )
        if reply:
            return reply
        # Fallback to legacy shape if combined reply is not available.
        address = truth.get("salon", {}).get("address", {})
        hours = truth.get("salon", {}).get("hours", {})
        if intent == "location":
            return (
                f"Адрес: {address.get('full')}. "
                f"{address.get('entrance') or ''}".strip()
            )
        if intent == "hours":
            days = hours.get("days")
            open_time = hours.get("open")
            close_time = hours.get("close")
            return f"Работаем {days}, с {open_time} до {close_time}."
        if intent == "parking":
            parking = truth.get("salon", {}).get("parking", {})
            details = parking.get("details") or ""
            return details or "Есть парковка рядом с салоном."
    if intent == "location_directions":
        address = truth.get("salon", {}).get("address", {})
        full_address = address.get("full")
        entrance = address.get("entrance")
        landmarks = address.get("landmarks") or []
        parts: list[str] = []
        if full_address:
            parts.append(f"Адрес: {full_address}")
        if entrance:
            parts.append(str(entrance))
        if landmarks:
            parts.append(str(landmarks[0]))
        if parts:
            return " ".join(part.strip() for part in parts if str(part).strip())
        return "Подскажите, откуда вам удобнее добираться?"
    if intent == "location_signage":
        signage = truth.get("salon", {}).get("address", {}).get("signage")
        if signage:
            return f"Да, есть {signage}."
        return "Да, вывеска есть."
    if intent == "services_overview":
        summary = truth.get("salon", {}).get("services_summary")
        if summary:
            return summary
        categories = [
            str(item.get("category", "")).strip()
            for item in (truth.get("price_list", []) if isinstance(truth, dict) else [])
            if isinstance(item, dict) and item.get("category")
        ]
        categories = [item for item in categories if item]
        if categories:
            return "Мы оказываем услуги: " + ", ".join(categories) + "."
        return "Мы салон красоты. Подскажите, какая услуга интересует?"
    if intent == "aftercare_gel_lac":
        aftercare = truth.get("aftercare", {}).get("gel_lac")
        return aftercare or "Подскажите, пожалуйста, какую услугу нужно подсказать по уходу?"
    if intent == "prep_brows_lashes":
        prep = truth.get("preparation", {}).get("brows_lashes")
        return prep or "Подскажите, пожалуйста, какую именно процедуру планируете?"
    if intent == "procedure_combo":
        combo = truth.get("procedure_compatibility", {}).get("face_cleaning_peel_same_day")
        return combo or "Такое сочетание лучше уточнить у администратора."
    if intent == "style_reference":
        reference = truth.get("style_reference", {}).get("ask_photo")
        return reference or "Пришлите, пожалуйста, фото-пример желаемого результата."
    if intent == "service_clarify":
        clarify = truth.get("service_clarify", {}).get("classic_interest")
        return clarify or "Уточните, пожалуйста, какую именно услугу вы имеете в виду?"
    if intent == "duration_or_price_clarify":
        clarify = truth.get("duration_or_price_clarify")
        if clarify:
            return str(clarify).strip()
        return "Вас интересует цена или длительность? Какая услуга?"
    if intent == "price_manicure":
        quick_price = truth.get("price_quick_answers", {}).get("manicure")
        return quick_price or "Подскажите, какой именно маникюр интересует?"
    if intent == "system_error":
        system_msg = truth.get("system_messages", {}).get("webhook_error")
        return system_msg or "Похоже, была техническая ошибка. Напишите вопрос ещё раз, я на связи."
    if intent == "last_appointment":
        last_time = truth.get("salon", {}).get("hours", {}).get("last_appointment")
        if last_time:
            return f"Последняя запись обычно на {last_time}."
        return "Последняя запись обычно за 30–60 минут до закрытия."
    if intent == "price_query":
        item = slots.get("price_item")
        if item:
            return _format_price_reply(item)
        return "Подскажите, какая услуга интересует? Сориентирую по цене."
    if intent == "why_price_from":
        reason = truth.get("pricing", {}).get("price_from_reason")
        return reason or "Цена «от» зависит от деталей услуги."
    if intent == "promotions_rules":
        stacking = truth.get("promotions", {}).get("stacking")
        stacking_notes = truth.get("promotions", {}).get("stacking_notes")
        if stacking and stacking_notes:
            return f"{stacking}. {stacking_notes}"
        return stacking or stacking_notes or "Скидки не суммируются."
    if intent == "promotions":
        return _format_promotions(truth, slots.get("promotion_intent"))
    if intent == "objection_price":
        hygiene = truth.get("hygiene", {}).get("instrument_processing")
        if hygiene:
            return (
                "Понимаю вопрос. У нас строгая стерилизация инструментов — это про безопасность, "
                "поэтому цена может быть выше."
            )
        return "Цена зависит от качества и безопасности процедур."
    if intent == "booking_intake":
        return (
            "Могу передать администратору запрос на запись. "
            "На какую услугу и на какое время удобно? "
            "Напишите, пожалуйста: точную дату, точное время, имя, контактный номер."
        )
    if intent == "cancel_policy":
        notice = truth.get("booking", {}).get("cancel_policy", {}).get("notice", {})
        standard = notice.get("standard_services_min_hours")
        long_services = notice.get("long_services_min_hours")
        return (
            f"Для стандартных услуг — минимум за {standard} часа, "
            f"для длительных (3+ часа) — за {long_services} часа."
        )
    if intent == "lateness_ok":
        notes = truth.get("booking", {}).get("lateness_policy", {}).get("notes")
        return notes or "Если опоздание до 10–15 минут — постараемся принять."
    if intent == "guest_child" or intent == "guest_partner":
        guest = truth.get("guest_policy", {}).get("allowed_guests")
        return guest or "Можно, есть зона ожидания."
    if intent == "guest_animals":
        animals = truth.get("guest_policy", {}).get("animals")
        return animals or "С животными нельзя по гигиене."
    if intent == "guest_early":
        early = truth.get("guest_policy", {}).get("early_arrival")
        return early or "Можно прийти на 10–15 минут раньше и подождать."
    if intent == "hygiene":
        hygiene = truth.get("hygiene", {})
        parts = [
            hygiene.get("instrument_processing"),
            hygiene.get("dry_heat"),
            hygiene.get("disposables"),
        ]
        return " ".join([p for p in parts if p])
    if intent == "hygiene_dry_heat":
        return "Да, есть сухожарный шкаф."
    if intent == "hygiene_disposables":
        return "Да, пилки и бафы одноразовые."
    if intent == "brands":
        brands = truth.get("brands", {})
        hair = ", ".join(brands.get("hair", []) if isinstance(brands, dict) else [])
        nails = ", ".join(brands.get("nails", []) if isinstance(brands, dict) else [])
        face = ", ".join(brands.get("face", []) if isinstance(brands, dict) else [])
        return f"Волосы: {hair}. Ногти: {nails}. Лицо: {face}."
    if intent == "amenities_wifi":
        wifi = truth.get("salon", {}).get("amenities", {}).get("wifi")
        return f"{wifi or 'Бесплатный Wi‑Fi'}."
    if intent == "amenities_drinks":
        drinks = truth.get("salon", {}).get("amenities", {}).get("drinks")
        return f"{drinks or 'Чай/кофе бесплатно'}."
    if intent == "amenities_toilet":
        toilet = truth.get("salon", {}).get("amenities", {}).get("toilet")
        return toilet or "Есть туалет для клиентов."
    if intent == "gift_certificate":
        gift = truth.get("salon", {}).get("amenities", {}).get("gift_certificates")
        return gift or "Можно купить сертификат на любую сумму."
    if intent == "off_topic":
        return "Я помогаю только с вопросами о наших услугах салона — цены, запись, адрес."
    return None


def _detect_promotion_intent(normalized: str, *, client_slug: str | None = None) -> str | None:
    if _signal_contains_any(normalized, client_slug, "promotion_first_visit_terms"):
        return "promotion_first_visit"
    if _signal_contains_any(normalized, client_slug, "promotion_birthday_terms"):
        return "promotion_birthday"
    if _signal_contains_any(
        normalized,
        client_slug,
        "promotion_birthday_before_after_phrases",
    ) and _signal_contains_any_words(
        normalized,
        client_slug,
        "promotion_birthday_day_words",
    ):
        return "promotion_birthday"
    if _signal_contains_any(normalized, client_slug, "promotion_student_terms"):
        return "promotion_student"
    if _signal_contains_any(
        normalized,
        client_slug,
        "promotion_student_weekday_terms",
    ) and _signal_contains_any(normalized, client_slug, "promotion_student_discount_terms"):
        return "promotion_student"
    return None


_SELF_RESOLVE_PAYMENT_PATTERNS = (
    re.compile(r"\bпо оплате\b.*\b(уточню|спрошу|узнаю|разберусь|позже)\b"),
    re.compile(r"\b(уточню|спрошу|узнаю|разберусь|позже)\b.*\bпо оплате\b"),
    re.compile(r"\bс оплатой\b.*\b(разберусь|позже)\b"),
    re.compile(r"\b(разберусь|позже)\b.*\bс оплатой\b"),
    re.compile(r"\bоплат\w*\b.*\b(уточню|спрошу|узнаю|разберусь|позже)\b"),
    re.compile(r"\b(уточню|спрошу|узнаю|разберусь|позже)\b.*\bоплат\w*\b"),
)


def _is_self_resolve_payment(normalized: str) -> bool:
    if "оплат" not in normalized:
        return False
    return any(pattern.search(normalized) for pattern in _SELF_RESOLVE_PAYMENT_PATTERNS)


def _policy_str_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for item in values:
        if not isinstance(item, str):
            item = str(item)
        item = item.strip()
        if item:
            cleaned.append(item)
    return cleaned


def _get_policy_section(policy_pack: dict | None, key: str) -> dict[str, Any] | None:
    if not isinstance(policy_pack, dict):
        return None
    section = policy_pack.get(key)
    return section if isinstance(section, dict) else None


def _matches_policy_keywords(normalized: str, keywords: list[str]) -> bool:
    for keyword in keywords:
        if not keyword:
            continue
        if len(keyword) <= 3:
            if re.search(rf"\b{re.escape(keyword)}\b", normalized):
                return True
            continue
        if keyword in normalized:
            return True
    return False


def _matches_policy_section(normalized: str, phrase_intents: set[str], section: dict | None) -> bool:
    if not section:
        return False
    phrase_keys = _policy_str_list(section.get("phrase_intents"))
    if phrase_keys and phrase_intents.intersection(phrase_keys):
        return True
    keywords = _policy_str_list(section.get("keywords"))
    if keywords and _matches_policy_keywords(normalized, keywords):
        return True
    return False


def _build_policy_meta(section_key: str, section: dict | None) -> dict[str, Any]:
    meta: dict[str, Any] = {"policy_gate": section_key}
    if section:
        risk_level = section.get("risk_level")
        if isinstance(risk_level, str) and risk_level.strip():
            meta["risk_level"] = risk_level.strip()
    return meta


def _build_policy_decision(
    policy_pack: dict | None,
    section_key: str,
    *,
    default_intent: str,
    default_response: str,
    default_action: str = "escalate",
    default_collect: list[str] | None = None,
) -> DemoSalonDecision:
    section = _get_policy_section(policy_pack, section_key)
    action = section.get("action") if isinstance(section, dict) else None
    if not isinstance(action, str) or not action.strip():
        action = default_action
    response = section.get("response") if isinstance(section, dict) else None
    if not isinstance(response, str) or not response.strip():
        response = default_response
    intent = section.get("intent") if isinstance(section, dict) else None
    if not isinstance(intent, str) or not intent.strip():
        intent = default_intent
    collect = _policy_str_list(section.get("collect") if isinstance(section, dict) else None)
    if not collect and default_collect:
        collect = list(default_collect)
    meta = _build_policy_meta(section_key, section)
    return DemoSalonDecision(
        action=action,
        response=response,
        intent=intent,
        collect=collect or None,
        meta=meta,
    )


def _build_payment_info_decision(policy_pack: dict | None) -> DemoSalonDecision:
    default_response = "По оплате уточню у администратора — передам администратору ваш вопрос."
    section = _get_policy_section(policy_pack, "payment_info")
    allow = bool(section.get("allow")) if isinstance(section, dict) else False
    allowed_phrases = _policy_str_list(section.get("allowed_phrases") if isinstance(section, dict) else None)
    response = None
    action = section.get("action") if isinstance(section, dict) else None
    if allow and allowed_phrases:
        response = allowed_phrases[0]
        action = "reply"
    if not isinstance(response, str) or not response.strip():
        response = section.get("response") if isinstance(section, dict) else None
    if not isinstance(response, str) or not response.strip():
        response = default_response
    if not isinstance(action, str) or not action.strip():
        action = "escalate"
    intent = section.get("intent") if isinstance(section, dict) else None
    if not isinstance(intent, str) or not intent.strip():
        intent = "payment"
    meta = _build_policy_meta("payment_info", section)
    return DemoSalonDecision(
        action=action,
        response=response,
        intent=intent,
        meta=meta,
    )


def _detect_policy_intent(
    normalized: str,
    phrase_intents: set[str],
    *,
    policy_pack: dict | None = None,
    client_slug: str | None = _DEFAULT_CLIENT_SLUG,
) -> str | None:
    policy_pack = policy_pack if isinstance(policy_pack, dict) else load_policy_pack(client_slug)
    if not policy_pack:
        return None

    skip_payment = _is_self_resolve_payment(normalized)
    if not skip_payment and _matches_policy_section(
        normalized,
        phrase_intents,
        _get_policy_section(policy_pack, "payment_info"),
    ):
        return "policy_payment"

    if _matches_policy_section(
        normalized,
        phrase_intents,
        _get_policy_section(policy_pack, "reschedule"),
    ):
        return "policy_reschedule"

    if _matches_policy_section(
        normalized,
        phrase_intents,
        _get_policy_section(policy_pack, "cancel"),
    ):
        return "policy_cancel"

    if _matches_policy_section(
        normalized,
        phrase_intents,
        _get_policy_section(policy_pack, "medical"),
    ):
        return "policy_medical"

    if _matches_policy_section(
        normalized,
        phrase_intents,
        _get_policy_section(policy_pack, "legal"),
    ):
        return "policy_legal"

    hours_like = _looks_like_hours_question(normalized, client_slug=client_slug)
    if (
        _matches_policy_section(
            normalized,
            phrase_intents,
            _get_policy_section(policy_pack, "complaint"),
        )
        and not hours_like
    ):
        return "policy_complaint"

    if _matches_policy_section(
        normalized,
        phrase_intents,
        _get_policy_section(policy_pack, "discounts"),
    ):
        return "policy_discount"

    return None


def get_demo_salon_service_decision(
    message: str,
    client_slug: str | None = "demo_salon",
    intent_decomp: dict | None = None,
) -> DemoSalonDecision | None:
    normalized = _normalize_text(message)
    if not normalized:
        return None
    slug = _normalize_client_slug(client_slug)
    segments = _split_question_segments(message)
    has_hours_signal = any(
        _looks_like_hours_question(_normalize_text(segment), client_slug=slug) for segment in segments
    )
    has_price_signal = any(_has_price_signal(_normalize_text(segment), segment) for segment in segments)
    has_duration_signal = any(_has_duration_signal(_normalize_text(segment), segment) for segment in segments)
    price_or_duration_signal = has_price_signal or has_duration_signal
    if has_hours_signal and (has_price_signal or has_duration_signal):
        return None
    consult_intent = False
    service_query_meta = None
    if isinstance(intent_decomp, dict):
        consult_intent = intent_decomp.get("consult_intent") is True
    allow_consult_short_circuit = False
    if consult_intent:
        service_query_meta = _resolve_service_query_meta(
            message,
            slug,
            intent_decomp,
            require_query=True,
        )
        allow_consult_short_circuit = bool(service_query_meta.get("service_query"))
    if not _looks_like_service_question(normalized, message, slug) and not allow_consult_short_circuit:
        return None

    if service_query_meta is None:
        service_query_meta = _resolve_service_query_meta(
            message,
            slug,
            intent_decomp,
            require_query=True,
        )
    service = _match_service(normalized, slug)
    truth = load_yaml_truth(slug)
    if service:
        reply = None
        if consult_intent and not price_or_duration_signal:
            service_name = service.get("name") if isinstance(service, dict) else None
            if isinstance(service_name, str) and service_name.strip():
                reply = _format_service_presence_reply_for_name(service_name, slug)
            if not reply:
                description = service.get("description") if isinstance(service, dict) else None
                if isinstance(description, str) and description.strip():
                    reply = description.strip()
        if not reply:
            reply = _format_service_reply(service, truth, slug)
        if reply:
            meta = _build_fact_meta(
                meta=service_query_meta,
                fact_source="service_matcher",
                fact_intents=["service_match"],
                service_query_meta=service_query_meta,
            )
            return DemoSalonDecision(
                action="reply",
                response=reply,
                intent="service_match",
                meta=meta,
            )

    reply = _format_service_not_found_reply(truth)
    if reply:
        meta = _build_fact_meta(
            meta=service_query_meta,
            fact_source="service_matcher",
            fact_intents=["service_not_found"],
            service_query_meta=service_query_meta,
        )
        return DemoSalonDecision(
            action="reply",
            response=reply,
            intent="service_not_found",
            meta=meta,
        )
    return None


def get_demo_salon_decision(
    message: str,
    client_slug: str | None = "demo_salon",
    intent_decomp: dict | None = None,
) -> DemoSalonDecision | None:
    normalized = _normalize_text(message)
    if not normalized:
        return None

    slug = _normalize_client_slug(client_slug)
    truth = load_yaml_truth(slug)
    phrase_intents = phrase_match_intent(message, slug)
    policy_pack = load_policy_pack(slug)
    hygiene_keywords = get_signal_lexicon_list(slug, "hygiene_keywords")
    parking_signal = _has_parking_signal(normalized, client_slug=slug)
    guest_signal = _has_guest_waiting_signal(normalized, client_slug=slug)
    if not guest_signal and _matches_guest_policy_lexicon(normalized, slug):
        guest_signal = True
    location_signal = _signal_contains_any(normalized, slug, "location_phrases")
    if not location_signal and _has_address_hint(normalized, truth):
        location_signal = True
    hygiene_signal = bool(hygiene_keywords) and _contains_any(normalized, hygiene_keywords)
    if not hygiene_signal and _signal_contains_all(normalized, slug, "hygiene_friend_inflammation_terms"):
        hygiene_signal = True
    price_signal = _has_price_signal(normalized, message, client_slug=slug)
    duration_signal = _has_duration_signal(normalized, message, client_slug=slug)
    price_item = _find_best_price_item(message, slug)
    if (
        price_item is None
        and price_signal
        and _signal_contains_any(normalized, slug, "mens_service_phrases")
        and _signal_contains_any(normalized, slug, "mens_service_context_phrases")
    ):
        price_item = _build_price_name_index(slug).get(_normalize_text("Мужская стрижка"))
    price_item_payload = _price_item_payload(price_item)
    if _signal_contains_all(normalized, slug, "cancel_fee_terms"):
        reply = format_reply_from_truth("cancel_policy", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="cancel_policy")

    policy_intent = _detect_policy_intent(
        normalized,
        phrase_intents,
        policy_pack=policy_pack,
        client_slug=slug,
    )

    if policy_intent == "policy_complaint" and _signal_contains_any(
        normalized,
        slug,
        "policy_complaint_exclusions",
    ):
        policy_intent = None

    if policy_intent == "policy_payment":
        return _build_payment_info_decision(policy_pack)
    if policy_intent == "policy_reschedule":
        return _build_policy_decision(
            policy_pack,
            "reschedule",
            default_intent="reschedule",
            default_response="Перенос записи подтверждает администратор. Передам ваш запрос.",
        )
    if policy_intent == "policy_cancel":
        return _build_policy_decision(
            policy_pack,
            "cancel",
            default_intent="cancel_request",
            default_response=(
                "Администратор подтвердит отмену. "
                "Напишите, пожалуйста: имя, услуга, контактный номер."
            ),
            default_collect=["имя", "услуга", "контактный номер"],
        )
    if policy_intent == "policy_medical" and hygiene_signal:
        policy_intent = None
    if policy_intent == "policy_medical":
        return _build_policy_decision(
            policy_pack,
            "medical",
            default_intent="medical",
            default_response=(
                "По таким вопросам нужна консультация мастера или администратора — "
                "передам ваш вопрос."
            ),
        )
    if policy_intent == "policy_legal":
        return _build_policy_decision(
            policy_pack,
            "legal",
            default_intent="legal",
            default_response="По юридическим вопросам подключу администратора — передам ваш запрос.",
        )
    if policy_intent == "policy_complaint":
        return _build_policy_decision(
            policy_pack,
            "complaint",
            default_intent="complaint",
            default_response="Жаль, что так вышло. Передам администратору, чтобы разобрались.",
        )

    if _signal_contains_any(normalized, slug, "same_day_terms"):
        if _signal_contains_any(normalized, slug, "same_day_booking_request_terms"):
            return DemoSalonDecision(
                action="escalate",
                response=(
                    "На сегодня уточню у администратора. Подскажите, пожалуйста: услуга и удобное время — передам."
                ),
                intent="same_day_booking",
                collect=["услуга", "время"],
            )

    if "aftercare_gel_lac" in phrase_intents or (
        _signal_contains_any(normalized, slug, "aftercare_gel_lac_terms")
        and _signal_contains_any(normalized, slug, "aftercare_gel_lac_care_terms")
    ):
        reply = format_reply_from_truth("aftercare_gel_lac", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="aftercare_gel_lac")

    consult_decision = build_consult_reply(
        message,
        client_slug=slug,
        intent_decomp=intent_decomp,
    )
    if consult_decision:
        if price_signal or duration_signal:
            service_decision = get_demo_salon_service_decision(
                message,
                client_slug=slug,
                intent_decomp=intent_decomp,
            )
            if service_decision and service_decision.intent == "service_match":
                return service_decision
        return consult_decision

    if _signal_contains_any(normalized, slug, "promotions_stacking_phrases") or _signal_contains_all(
        normalized,
        slug,
        "promotions_stacking_terms",
    ):
        reply = format_reply_from_truth("promotions_rules", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="promotions_rules")

    promotion_intent = _detect_promotion_intent(normalized, client_slug=slug)
    if promotion_intent:
        reply = format_reply_from_truth(
            "promotions",
            {"promotion_intent": promotion_intent},
            client_slug=slug,
            truth=truth,
        )
        if reply:
            return _build_truth_decision(response=reply, intent="promotions")

    if policy_intent == "policy_discount":
        return None

    if _signal_contains_all(normalized, slug, "why_price_from_required_terms") and _signal_contains_any(
        normalized,
        slug,
        "why_price_from_price_terms",
    ):
        reply = format_reply_from_truth("why_price_from", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="why_price_from")

    if _signal_contains_any(normalized, slug, "price_objection_direct_terms") or (
        _signal_contains_any(normalized, slug, "price_objection_root_terms")
        and not _signal_contains_any(normalized, slug, "price_objection_exclude_terms")
    ):
        reply = format_reply_from_truth("objection_price", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="objection_price")

    if location_signal and not guest_signal and (not price_signal or (price_signal and not price_item)):
        reply, meta = build_info_combined_reply(
            include_parking=parking_signal,
            include_guest=guest_signal,
            client_slug=slug,
        )
        intent_name = "location"
        if price_signal:
            clarify = format_reply_from_truth("duration_or_price_clarify", client_slug=slug, truth=truth)
            if clarify:
                reply = f"{reply} {clarify}".strip() if reply else clarify
            intent_name = "duration_or_price_clarify"
        if reply:
            return _build_truth_decision(response=reply, intent=intent_name, meta=meta)

    if _signal_contains_any(normalized, slug, "location_directions_phrases"):
        reply = format_reply_from_truth("location_directions", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="location_directions")

    if _signal_contains_any(normalized, slug, "location_signage_phrases"):
        reply = format_reply_from_truth("location_signage", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="location_signage")

    if parking_signal:
        reply, meta = build_info_combined_reply(
            include_parking=True,
            include_guest=guest_signal,
            client_slug=slug,
        )
        if reply:
            return _build_truth_decision(response=reply, intent="parking", meta=meta)

    if _signal_contains_any(normalized, slug, "last_appointment_phrases"):
        reply = format_reply_from_truth("last_appointment", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="last_appointment")

    multi_result = compose_multi_truth_reply(
        message,
        slug,
        intent_decomp=intent_decomp,
        return_meta=True,
    )
    if multi_result:
        multi_reply, multi_meta = multi_result
        return DemoSalonDecision(
            action="reply",
            response=multi_reply,
            intent="multi_truth",
            meta=multi_meta if isinstance(multi_meta, dict) else None,
        )

    if _signal_contains_any(normalized, slug, "lateness_phrases"):
        minutes = _extract_minutes(message)
        tolerated = truth.get("booking", {}).get("lateness_policy", {}).get("tolerated_minutes", 15)
        try:
            tolerated = int(tolerated)
        except (TypeError, ValueError):
            tolerated = 15
        if minutes is not None and minutes > tolerated:
            return DemoSalonDecision(
                action="escalate",
                response="Если опоздание больше 15 минут — передам администратору, чтобы уточнить.",
                intent="lateness_over",
            )
        reply = format_reply_from_truth("lateness_ok", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="lateness_ok")

    hours_like = _looks_like_hours_question(normalized, client_slug=slug) or _signal_contains_any(
        normalized,
        slug,
        "hours_extra_phrases",
    )
    if hours_like and not _signal_contains_any(normalized, slug, "hours_exclude_phrases"):
        reply, meta = build_info_combined_reply(
            include_parking=parking_signal,
            include_guest=guest_signal,
            client_slug=slug,
        )
        if reply:
            return _build_truth_decision(response=reply, intent="hours", meta=meta)

    if _signal_contains_any(normalized, slug, "services_terms") and _signal_contains_any(
        normalized,
        slug,
        "services_mens_terms",
    ):
        mens_price_items = get_signal_lexicon_list(slug, "mens_service_price_items")
        reply = _format_service_price_items(
            mens_price_items,
            slug,
        )
        if reply:
            meta = _build_fact_meta(
                fact_source="service_matcher",
                fact_intents=["service_match"],
            )
            return DemoSalonDecision(
                action="reply",
                response=reply,
                intent="service_match",
                meta=meta,
            )

    if "services_overview" in phrase_intents or _signal_contains_any(
        normalized,
        slug,
        "services_overview_phrases",
    ) or _has_services_overview_signal(normalized, truth):
        reply = format_reply_from_truth("services_overview", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="services_overview")

    if "prep_brows_lashes" in phrase_intents or (
        _signal_contains_any(normalized, slug, "prep_brows_lashes_prepare_terms")
        and _signal_contains_any(normalized, slug, "prep_brows_lashes_focus_terms")
    ) or _signal_contains_any(normalized, slug, "prep_brows_lashes_extra_terms"):
        reply = format_reply_from_truth("prep_brows_lashes", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="prep_brows_lashes")

    if "procedure_combo" in phrase_intents or (
        _signal_contains_any(normalized, slug, "procedure_combo_require_any")
        and _signal_contains_any(normalized, slug, "procedure_combo_require_all")
    ):
        reply = format_reply_from_truth("procedure_combo", client_slug=slug, truth=truth)
        if reply:
            return DemoSalonDecision(action="escalate", response=reply, intent="procedure_combo")

    if "style_reference" in phrase_intents:
        reply = format_reply_from_truth("style_reference", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="style_reference")

    if "system_error" in phrase_intents or _signal_contains_any(normalized, slug, "system_error_phrases"):
        reply = format_reply_from_truth("system_error", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="system_error")

    if "service_clarify" in phrase_intents or _signal_contains_all(normalized, slug, "service_clarify_terms"):
        reply = format_reply_from_truth("service_clarify", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="service_clarify")

    if _signal_contains_any(normalized, slug, "guest_animals_terms"):
        reply = format_reply_from_truth("guest_animals", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="guest_policy")

    if guest_signal and not price_signal:
        reply, meta = build_info_combined_reply(
            include_parking=parking_signal,
            include_guest=True,
            client_slug=slug,
        )
        if reply:
            return _build_truth_decision(response=reply, intent="guest_policy", meta=meta)

    hours_like = _looks_like_hours_question(normalized, client_slug=slug)
    question_type = semantic_question_type(message, client_slug=slug)
    if hours_like and not price_signal and not duration_signal:
        question_type = None
    question_meta: dict[str, Any] | None = None
    duration_meta: dict[str, Any] | None = None
    if question_type:
        question_meta = {
            "question_type": question_type.kind,
            "question_type_score": question_type.score,
        }
        if question_type.kind == "duration":
            duration_meta = question_meta
    if duration_signal and not price_signal and duration_meta is None:
        duration_meta = {"question_type": "duration"}
    if duration_meta:
        service_query_meta = _resolve_service_query_meta(
            message,
            slug,
            intent_decomp,
            require_query=True,
        )
        service = _resolve_service_from_query(service_query_meta.get("service_query"), slug)
        reply = _format_service_duration_reply(
            service,
            message=message,
            service_label=service_query_meta.get("service_query"),
            client_slug=slug,
        )
        duration_item = service_query_meta.get("service_query")
        meta = {**duration_meta, **service_query_meta} if duration_meta else service_query_meta
        return _build_truth_decision(
            response=reply,
            intent="service_duration",
            meta=meta,
            duration_item=duration_item if isinstance(duration_item, str) else None,
        )

    if not price_item and isinstance(intent_decomp, dict):
        price_service_meta = _resolve_service_query_meta(
            message,
            slug,
            intent_decomp,
            require_query=False,
        )
        service_query = price_service_meta.get("service_query") if isinstance(price_service_meta, dict) else None
        if isinstance(service_query, str) and service_query.strip():
            price_item = _find_best_price_item(service_query, slug)
            price_item_payload = _price_item_payload(price_item)
    if question_type is None and price_signal and not price_item:
        if not location_signal and not parking_signal and not guest_signal:
            service_query_meta = _resolve_service_query_meta(
                message,
                slug,
                intent_decomp,
                require_query=True,
            )
            service_query_value = service_query_meta.get("service_query")
            if service_query_value:
                service = _resolve_service_from_query(service_query_value, slug)
                if service:
                    service_reply = _format_service_reply(service, truth, slug)
                    if service_reply:
                        return _build_truth_decision(
                            response=service_reply,
                            intent="price_query",
                            meta=service_query_meta,
                            price_item=price_item_payload,
                        )
                price_item = _find_best_price_item(service_query_value, slug)
                price_item_payload = _price_item_payload(price_item)
                if price_item:
                    reply = format_reply_from_truth(
                        "price_query",
                        {"price_item": price_item["item"]},
                        client_slug=slug,
                        truth=truth,
                    )
                    if reply:
                        return _build_truth_decision(
                            response=reply,
                            intent="price_query",
                            meta=service_query_meta,
                            price_item=price_item_payload,
                        )
        info_reply: str | None = None
        info_meta: dict[str, Any] = {}
        if location_signal or parking_signal or guest_signal:
            info_reply, info_meta = build_info_combined_reply(
                include_parking=parking_signal,
                include_guest=guest_signal,
                client_slug=slug,
            )
        if _is_offtopic_message(normalized, slug):
            reply = format_reply_from_truth("off_topic", client_slug=slug, truth=truth)
            if reply:
                return _build_truth_decision(response=reply, intent="off_topic")
        clarify_reply = format_reply_from_truth("duration_or_price_clarify", client_slug=slug, truth=truth)
        reply_parts = [part for part in [info_reply, clarify_reply] if part]
        reply_text = " ".join(reply_parts) if reply_parts else clarify_reply
        if reply_text:
            return _build_truth_decision(
                response=reply_text,
                intent="duration_or_price_clarify",
                meta=info_meta or None,
            )

    question_meta_for_price = question_meta if question_type and question_type.kind == "pricing" else None
    if "price_manicure" in phrase_intents or (
        _signal_contains_any(normalized, slug, "price_manicure_terms") and price_signal and not price_item
    ):
        service_query_meta = _resolve_service_query_meta(
            message,
            slug,
            intent_decomp,
            require_query=True,
        )
        if service_query_meta.get("service_query"):
            reply = format_reply_from_truth("price_manicure", client_slug=slug, truth=truth)
            if reply:
                meta = {**question_meta_for_price, **service_query_meta} if question_meta_for_price else service_query_meta
                return _build_truth_decision(
                    response=reply,
                    intent="price_manicure",
                    meta=meta,
                    price_item=price_item_payload,
                )

    if hygiene_signal:
        reply = format_reply_from_truth("hygiene", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="hygiene")

    if _signal_contains_any(normalized, slug, "hygiene_dry_heat_terms"):
        reply = format_reply_from_truth("hygiene_dry_heat", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="hygiene")

    if _signal_contains_any(normalized, slug, "hygiene_disposables_terms"):
        reply = format_reply_from_truth("hygiene_disposables", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="hygiene")

    if _signal_contains_any(normalized, slug, "brands_terms"):
        reply = format_reply_from_truth("brands", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="brands")

    if _signal_contains_any(normalized, slug, "amenities_wifi_terms"):
        reply = format_reply_from_truth("amenities_wifi", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="amenities")

    if _signal_contains_any(normalized, slug, "amenities_drinks_terms"):
        reply = format_reply_from_truth("amenities_drinks", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="amenities")

    if _signal_contains_any(normalized, slug, "amenities_toilet_terms") and not _matches_service_request_lexicon(
        normalized, slug
    ):
        reply = format_reply_from_truth("amenities_toilet", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="amenities")

    if _signal_contains_any(normalized, slug, "gift_certificate_terms"):
        reply = format_reply_from_truth("gift_certificate", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="gift_certificate")

    if (
        "order_booking" in phrase_intents
        or _signal_contains_any(normalized, slug, "booking_intake_terms")
    ):
        reply = format_reply_from_truth("booking_intake", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="booking_intake")

    if price_item and price_signal:
        reply = _format_price_reply(price_item_payload or price_item)
        if reply:
            meta = _build_fact_meta(
                fact_source="price_list",
                fact_intents=["price_query"],
                price_item=price_item_payload,
            )
            return DemoSalonDecision(
                action="reply",
                response=reply,
                intent="price_query",
                meta=meta,
            )

    service_decision = get_demo_salon_service_decision(
        message,
        client_slug=slug,
        intent_decomp=intent_decomp,
    )
    if service_decision:
        return service_decision

    if _is_offtopic_message(normalized, slug):
        reply = format_reply_from_truth("off_topic", client_slug=slug, truth=truth)
        if reply:
            return _build_truth_decision(response=reply, intent="off_topic")

    if price_item or price_signal:
        service_query_meta = _resolve_service_query_meta(
            message,
            slug,
            intent_decomp,
            require_query=True,
        )
        service_query_value = service_query_meta.get("service_query")
        if not service_query_value:
            reply = format_reply_from_truth("service_clarify", client_slug=slug, truth=truth)
            if reply:
                meta = (
                    {**question_meta_for_price, **service_query_meta}
                    if question_meta_for_price
                    else service_query_meta
                )
                return _build_truth_decision(
                    response=reply,
                    intent="service_clarify",
                    meta=meta,
                )
        if not price_item and isinstance(service_query_value, str):
            service = _resolve_service_from_query(service_query_value, slug)
            if service:
                service_reply = _format_service_reply(service, truth, slug)
                if service_reply:
                    meta = (
                        {**question_meta_for_price, **service_query_meta}
                        if question_meta_for_price
                        else service_query_meta
                    )
                    return _build_truth_decision(
                        response=service_reply,
                        intent="price_query",
                        meta=meta,
                        price_item=price_item_payload,
                    )
        reply = format_reply_from_truth(
            "price_query",
            {"price_item": price_item["item"]} if price_item else {},
            client_slug=slug,
            truth=truth,
        )
        if reply:
            meta = {**question_meta_for_price, **service_query_meta} if question_meta_for_price else service_query_meta
            return _build_truth_decision(
                response=reply,
                intent="price_query",
                meta=meta,
                price_item=price_item_payload,
            )

    return None


def get_demo_salon_price_reply(message: str, client_slug: str | None = "demo_salon") -> str | None:
    normalized = _normalize_text(message)
    if not normalized:
        return None
    slug = _normalize_client_slug(client_slug)
    service_query_meta = _resolve_service_query_meta(
        message,
        slug,
        intent_decomp=None,
        require_query=True,
    )
    if not service_query_meta.get("service_query"):
        return None
    price_item = _find_best_price_item(message, slug)
    if not price_item:
        return None
    return format_reply_from_truth(
        "price_query",
        {"price_item": price_item["item"]},
        client_slug=slug,
    )


def get_demo_salon_price_item(message: str, client_slug: str | None = "demo_salon") -> str | None:
    price_item = _find_best_price_item(message, _normalize_client_slug(client_slug))
    if not price_item:
        return None
    item = price_item.get("item")
    if not item:
        return None
    return str(item).strip() or None


def get_demo_salon_service_hint(message: str, client_slug: str | None = "demo_salon") -> str | None:
    normalized = _normalize_text(message)
    if not normalized:
        return None
    slug = _normalize_client_slug(client_slug)
    service = _match_service(normalized, slug)
    if isinstance(service, dict):
        name = service.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    price_item = _find_best_price_item(message, slug)
    if isinstance(price_item, dict):
        name = price_item.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def get_truth_reply(message: str, client_slug: str | None = "demo_salon") -> str | None:
    decision = get_demo_salon_decision(message, client_slug=client_slug)
    if decision and decision.action == "reply":
        return decision.response
    return None
