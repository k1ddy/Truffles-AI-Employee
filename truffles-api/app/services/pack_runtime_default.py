"""Default runtime pack adapter with explicit per-pack routing."""

from __future__ import annotations

import importlib
import re
from functools import lru_cache
from types import ModuleType
from typing import Any

_DEFAULT_ADAPTER_MODULE = "app.services.pack_runtime_generic_adapter"


@lru_cache(maxsize=None)
def _load_adapter(module_path: str) -> ModuleType:
    return importlib.import_module(module_path)


def _normalize_slug(client_slug: str | None) -> str:
    return (client_slug or "").strip().lower()


def _slug_to_module_token(client_slug: str | None) -> str:
    normalized = _normalize_slug(client_slug)
    if not normalized:
        return ""
    return re.sub(r"[^a-z0-9_]+", "_", normalized).strip("_")


def _load_adapter_if_present(module_path: str) -> ModuleType | None:
    try:
        return _load_adapter(module_path)
    except ModuleNotFoundError as exc:
        if exc.name == module_path:
            return None
        raise


def _resolve_adapter(client_slug: str | None = None) -> ModuleType:
    module_token = _slug_to_module_token(client_slug)
    if module_token:
        pack_adapter_module = f"app.services.pack_runtime_{module_token}_adapter"
        pack_adapter = _load_adapter_if_present(pack_adapter_module)
        if pack_adapter is not None:
            return pack_adapter
    return _load_adapter(_DEFAULT_ADAPTER_MODULE)


def get_pack_adapter(client_slug: str | None = None) -> ModuleType:
    return _resolve_adapter(client_slug)


def _normalize_text(text: str) -> str:
    return _resolve_adapter()._normalize_text(text)


def load_system_lexicons() -> dict:
    return _resolve_adapter().load_system_lexicons()


def get_system_lexicon_list(key: str) -> list[str]:
    return _resolve_adapter().get_system_lexicon_list(key)


def get_signal_lexicon_list(client_slug: str | None, key: str) -> list[str]:
    return _resolve_adapter(client_slug).get_signal_lexicon_list(client_slug, key)


def get_system_anchor_groups(intent: str) -> list[tuple[str, ...]]:
    return _resolve_adapter().get_system_anchor_groups(intent)


def load_yaml_truth(client_slug: str | None = "generic") -> dict:
    return _resolve_adapter(client_slug).load_yaml_truth(client_slug)


def load_policy_pack(client_slug: str | None = "generic") -> dict:
    return _resolve_adapter(client_slug).load_policy_pack(client_slug)


def build_quiet_hours_notice(
    *,
    now_utc=None,
    now_local=None,
    client_slug: str | None = "generic",
) -> str | None:
    return _resolve_adapter(client_slug).build_quiet_hours_notice(
        now_utc=now_utc,
        now_local=now_local,
        client_slug=client_slug,
    )


def build_evening_greeting(
    *,
    now_utc=None,
    now_local=None,
    client_slug: str | None = "generic",
) -> str | None:
    return _resolve_adapter(client_slug).build_evening_greeting(
        now_utc=now_utc,
        now_local=now_local,
        client_slug=client_slug,
    )


def _match_service(normalized: str, client_slug: str) -> dict | None:
    return _resolve_adapter(client_slug)._match_service(normalized, client_slug)


def _matches_service_request_lexicon(normalized: str, client_slug: str) -> bool:
    return _resolve_adapter(client_slug)._matches_service_request_lexicon(normalized, client_slug)


def _has_price_signal(
    normalized: str,
    raw_text: str | None = None,
    *,
    client_slug: str | None = None,
) -> bool:
    return _resolve_adapter(client_slug)._has_price_signal(
        normalized,
        raw_text,
        client_slug=client_slug,
    )


def _has_duration_signal(
    normalized: str,
    raw_text: str | None = None,
    *,
    client_slug: str | None = None,
) -> bool:
    return _resolve_adapter(client_slug)._has_duration_signal(
        normalized,
        raw_text,
        client_slug=client_slug,
    )


def _has_parking_signal(normalized: str, *, client_slug: str | None = None) -> bool:
    return _resolve_adapter(client_slug)._has_parking_signal(
        normalized,
        client_slug=client_slug,
    )


def _has_guest_waiting_signal(normalized: str, *, client_slug: str | None = None) -> bool:
    return _resolve_adapter(client_slug)._has_guest_waiting_signal(
        normalized,
        client_slug=client_slug,
    )


def _has_contact_signal(
    normalized: str,
    raw_text: str | None = None,
    *,
    client_slug: str | None = None,
) -> bool:
    return _resolve_adapter(client_slug)._has_contact_signal(
        normalized,
        raw_text,
        client_slug=client_slug,
    )


def semantic_question_type(
    text: str,
    *,
    include_kinds: set[str] | None = None,
    return_multi: bool = False,
    client_slug: str | None = "generic",
):
    return _resolve_adapter(client_slug).semantic_question_type(
        text,
        include_kinds=include_kinds,
        return_multi=return_multi,
        client_slug=client_slug,
    )


def semantic_service_match(text: str, client_slug: str):
    return _resolve_adapter(client_slug).semantic_service_match(text, client_slug)


def compose_multi_truth_reply(
    message: str,
    client_slug: str | None,
    intent_decomp: dict | None = None,
    *,
    return_meta: bool = False,
):
    return _resolve_adapter(client_slug).compose_multi_truth_reply(
        message,
        client_slug,
        intent_decomp,
        return_meta=return_meta,
    )


def build_info_combined_reply(
    *,
    include_parking: bool = False,
    include_guest: bool = False,
    client_slug: str | None = "generic",
) -> tuple[str | None, dict[str, Any]]:
    return _resolve_adapter(client_slug).build_info_combined_reply(
        include_parking=include_parking,
        include_guest=include_guest,
        client_slug=client_slug,
    )


def format_reply_from_truth(
    intent: str,
    slots: dict | None = None,
    *,
    client_slug: str | None = "generic",
    truth: dict | None = None,
) -> str | None:
    return _resolve_adapter(client_slug).format_reply_from_truth(
        intent,
        slots=slots,
        client_slug=client_slug,
        truth=truth,
    )


def _format_service_not_found_reply(
    truth: dict,
    *,
    client_slug: str | None = None,
) -> str | None:
    return _resolve_adapter(client_slug)._format_service_not_found_reply(truth)


def _build_fact_meta(
    *,
    fact_source: str,
    fact_intents: list[str] | None = None,
    meta: dict[str, Any] | None = None,
    service_query_meta: dict[str, Any] | None = None,
    info_sections: list[str] | None = None,
    price_item: dict[str, Any] | None = None,
    duration_item: str | None = None,
    client_slug: str | None = None,
) -> dict[str, Any]:
    return _resolve_adapter(client_slug)._build_fact_meta(
        fact_source=fact_source,
        fact_intents=fact_intents,
        meta=meta,
        service_query_meta=service_query_meta,
        info_sections=info_sections,
        price_item=price_item,
        duration_item=duration_item,
    )


def _detect_promotion_intent(normalized: str, *, client_slug: str | None = None) -> str | None:
    return _resolve_adapter(client_slug)._detect_promotion_intent(
        normalized,
        client_slug=client_slug,
    )


def get_pack_decision(
    message: str,
    *,
    client_slug: str | None = None,
    intent_decomp: dict | None = None,
):
    return _resolve_adapter(client_slug).get_pack_decision(
        message,
        client_slug=client_slug,
        intent_decomp=intent_decomp,
    )


def get_pack_service_decision(
    message: str,
    *,
    client_slug: str | None = None,
    intent_decomp: dict | None = None,
):
    return _resolve_adapter(client_slug).get_pack_service_decision(
        message,
        client_slug=client_slug,
        intent_decomp=intent_decomp,
    )


def get_pack_price_reply(message: str, *, client_slug: str | None = None) -> str | None:
    return _resolve_adapter(client_slug).get_pack_price_reply(message, client_slug=client_slug)


def get_pack_price_item(message: str, *, client_slug: str | None = None) -> str | None:
    return _resolve_adapter(client_slug).get_pack_price_item(message, client_slug=client_slug)


def get_pack_service_hint(message: str, *, client_slug: str | None = None) -> str | None:
    return _resolve_adapter(client_slug).get_pack_service_hint(message, client_slug=client_slug)


def phrase_match_intent(text: str, client_slug: str | None = "generic") -> set[str]:
    return _resolve_adapter(client_slug).phrase_match_intent(
        text,
        client_slug=client_slug,
    )


__all__ = [
    "_build_fact_meta",
    "_detect_promotion_intent",
    "_format_service_not_found_reply",
    "_has_guest_waiting_signal",
    "_has_duration_signal",
    "_has_parking_signal",
    "_has_price_signal",
    "_match_service",
    "_matches_service_request_lexicon",
    "_normalize_text",
    "build_evening_greeting",
    "build_info_combined_reply",
    "build_quiet_hours_notice",
    "compose_multi_truth_reply",
    "format_reply_from_truth",
    "get_pack_adapter",
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
