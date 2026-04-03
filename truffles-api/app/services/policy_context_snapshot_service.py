from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.services.capabilities_runtime import get_runtime_capabilities
from app.services.capability_manifest_service import (
    resolve_fact_scope_decision,
    resolve_tool_protocol_decision,
)
from app.services.tool_registry_snapshot_service import list_declared_tool_actions

POLICY_CORE_MEMORY_SUMMARY_MAX_CHARS = max(
    int(os.environ.get("LLM_POLICY_CORE_MEMORY_SUMMARY_MAX_CHARS", "360")),
    120,
)
POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS = max(
    int(os.environ.get("LLM_POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS", "120")),
    48,
)
POLICY_CORE_COMPACT_PROFILE_ITEMS_MAX = max(
    int(os.environ.get("LLM_POLICY_CORE_COMPACT_PROFILE_ITEMS_MAX", "3")),
    1,
)
POLICY_CORE_CONTEXT_CARD_LIMIT = max(
    int(os.environ.get("LLM_POLICY_CORE_CONTEXT_CARD_LIMIT", "6")),
    1,
)

_DEFAULT_INFO_REFS_V1 = (
    "pricing",
    "hours",
    "duration",
    "location",
    "parking",
    "promotions",
    "master",
    "contact",
)
_GENERIC_TOOL_ACTIONS_V1 = ("info", "consult", "booking", "handoff", "collect")


class PolicyCoreContextSnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "policy_core_context_snapshot.v1"
    recipe_version: str = "v1"
    client_slug: str | None = None
    tool_actions: tuple[str, ...] = ()
    info_refs: tuple[str, ...] = ()
    consult_refs: tuple[str, ...] = ()
    capability_cards: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    policy_cards: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    service_cards: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    consult_cards: tuple[dict[str, Any], ...] = Field(default_factory=tuple)

    def as_allowed_payload(self) -> dict[str, Any]:
        return {
            "tool_actions": list(self.tool_actions),
            "info_refs": list(self.info_refs),
            "consult_refs": list(self.consult_refs),
        }

    def as_context_payload(self) -> dict[str, Any] | None:
        payload: dict[str, Any] = {}
        if self.capability_cards:
            payload["capability_cards"] = [dict(card) for card in self.capability_cards]
        if self.policy_cards:
            payload["policy_cards"] = [dict(card) for card in self.policy_cards]
        if self.service_cards:
            payload["service_cards"] = [dict(card) for card in self.service_cards]
        if self.consult_cards:
            payload["consult_cards"] = [dict(card) for card in self.consult_cards]
        return payload or None


def _trim_policy_core_context_text(
    value: Any,
    *,
    max_chars: int = POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS,
) -> str | None:
    if not isinstance(value, str):
        return None
    compact = " ".join(value.split())
    if not compact:
        return None
    return compact[:max_chars]


def _normalize_policy_core_ref_candidates(refs: list[str] | None) -> list[str]:
    if not isinstance(refs, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_ref in refs:
        if not isinstance(raw_ref, str):
            continue
        token = raw_ref.strip().casefold()
        if not token or token in seen:
            continue
        seen.add(token)
        normalized.append(token)
    return normalized


def _build_policy_cards(runtime: Any) -> list[dict[str, Any]]:
    if runtime is None:
        return []
    policy_overrides = runtime.payload.policy_overrides.model_dump(exclude_none=True)
    source = str(getattr(runtime, "source", "") or "runtime")
    cards: list[dict[str, Any]] = []
    for section_name, section_payload in policy_overrides.items():
        if not isinstance(section_payload, dict):
            continue
        response = _trim_policy_core_context_text(
            section_payload.get("response"),
            max_chars=POLICY_CORE_MEMORY_SUMMARY_MAX_CHARS,
        )
        if response is None:
            continue
        cards.append(
            {
                "section": section_name,
                "response": response,
                "source": source,
            }
        )
    return cards[:POLICY_CORE_CONTEXT_CARD_LIMIT]


def _build_capability_cards(runtime: Any) -> list[dict[str, Any]]:
    if runtime is None:
        return []
    source = str(getattr(runtime, "source", "") or "runtime")
    payload = getattr(runtime, "payload", None)
    if payload is None:
        return []

    cards: list[dict[str, Any]] = []
    domain_slug = _trim_policy_core_context_text(getattr(payload, "domain_slug", None), max_chars=48)
    if domain_slug:
        cards.append({"kind": "domain", "source": source, "domain_slug": domain_slug})

    providers = payload.providers.model_dump(exclude_none=True)
    if providers:
        cards.append({"kind": "providers", "source": source, **providers})

    features = payload.features.model_dump(exclude_none=True)
    if features:
        cards.append({"kind": "features", "source": source, **features})

    tools = payload.tools.model_dump(exclude_none=True)
    if tools:
        cards.append({"kind": "tool_policy", "source": source, **tools})

    allowed_fact_scopes = [
        scope.strip().casefold()
        for scope in getattr(payload, "allowed_fact_scopes", None) or []
        if isinstance(scope, str) and scope.strip()
    ]
    if allowed_fact_scopes:
        cards.append(
            {
                "kind": "fact_scope",
                "source": source,
                "allowed_scopes": allowed_fact_scopes[:POLICY_CORE_CONTEXT_CARD_LIMIT],
            }
        )

    handoff_policy = _trim_policy_core_context_text(
        getattr(payload, "handoff_policy", None),
        max_chars=40,
    )
    if handoff_policy:
        cards.append(
            {
                "kind": "handoff_policy",
                "source": source,
                "policy": handoff_policy.casefold(),
            }
        )

    return cards[:POLICY_CORE_CONTEXT_CARD_LIMIT]


def _load_consult_catalog(client_slug: str | None) -> tuple[list[str], dict[str, dict[str, Any]]]:
    normalized_client_slug = _trim_policy_core_context_text(client_slug, max_chars=64)
    if not normalized_client_slug:
        return [], {}

    from app.services.consult_pack_service import load_consult_playbook

    playbook, error = load_consult_playbook(normalized_client_slug)
    if error or playbook is None:
        return [], {}

    refs: list[str] = []
    cards: dict[str, dict[str, Any]] = {}
    for topic in getattr(playbook, "topics", []):
        topic_id = _trim_policy_core_context_text(getattr(topic, "id", None), max_chars=64)
        if topic_id is None:
            continue
        normalized_topic_id = topic_id.casefold()
        refs.append(normalized_topic_id)
        card: dict[str, Any] = {"id": normalized_topic_id}

        title = _trim_policy_core_context_text(getattr(topic, "title", None), max_chars=96)
        if title:
            card["title"] = title

        summary = _trim_policy_core_context_text(getattr(topic, "summary", None), max_chars=160)
        if summary:
            card["summary"] = summary

        risk_tags = [
            str(tag).strip().casefold()
            for tag in getattr(topic, "risk_tags", []) or []
            if str(tag).strip()
        ]
        if risk_tags:
            card["risk_tags"] = risk_tags[:POLICY_CORE_COMPACT_PROFILE_ITEMS_MAX]

        fact_requirements = [
            str(item).strip().casefold()
            for item in getattr(topic, "fact_requirements", []) or []
            if str(item).strip()
        ]
        if fact_requirements:
            card["fact_requirements"] = fact_requirements[:POLICY_CORE_COMPACT_PROFILE_ITEMS_MAX]

        next_step = _trim_policy_core_context_text(getattr(topic, "next_step", None), max_chars=160)
        if next_step:
            card["next_step"] = next_step

        cards[normalized_topic_id] = card
    return refs, cards


def _filter_fact_refs(namespace: str, refs: list[str]) -> list[str]:
    filtered: list[str] = []
    for ref in refs:
        decision = resolve_fact_scope_decision(f"{namespace}.{ref}")
        if decision.allowed:
            filtered.append(ref)
    return filtered


def _build_service_cards(client_slug: str | None) -> list[dict[str, Any]]:
    normalized_client_slug = _trim_policy_core_context_text(client_slug, max_chars=64)
    if not normalized_client_slug:
        return []

    from app.services.pack_runtime_service import get_pack_runtime

    try:
        truth = get_pack_runtime(normalized_client_slug).load_yaml_truth()
    except Exception:
        return []

    domain_pack = truth.get("domain_pack") if isinstance(truth, dict) else None
    taxonomy = domain_pack.get("service_taxonomy") if isinstance(domain_pack, dict) else None
    categories = taxonomy.get("categories") if isinstance(taxonomy, dict) else None
    if not isinstance(categories, list):
        return []

    cards: list[dict[str, Any]] = []
    for raw_category in categories:
        if not isinstance(raw_category, dict):
            continue
        card: dict[str, Any] = {
            "kind": "service_taxonomy",
            "source": "pack_runtime",
        }
        category_id = _trim_policy_core_context_text(raw_category.get("id"), max_chars=32)
        if category_id:
            card["id"] = category_id.casefold()
        label = (
            _trim_policy_core_context_text(raw_category.get("label_ru"), max_chars=64)
            or _trim_policy_core_context_text(raw_category.get("label_kk"), max_chars=64)
            or _trim_policy_core_context_text(raw_category.get("label"), max_chars=64)
        )
        if label:
            card["label"] = label

        includes: list[str] = []
        seen_includes: set[str] = set()
        for raw_value in list(raw_category.get("includes_ru") or []) + list(
            raw_category.get("includes_kk") or []
        ):
            token = _trim_policy_core_context_text(raw_value, max_chars=40)
            if not token:
                continue
            fingerprint = token.casefold()
            if fingerprint in seen_includes:
                continue
            seen_includes.add(fingerprint)
            includes.append(token)
            if len(includes) >= POLICY_CORE_COMPACT_PROFILE_ITEMS_MAX:
                break
        if includes:
            card["includes"] = includes

        synonyms: list[str] = []
        seen_synonyms: set[str] = set()
        for raw_value in list(raw_category.get("synonyms_ru") or []) + list(
            raw_category.get("synonyms_kk") or []
        ):
            token = _trim_policy_core_context_text(raw_value, max_chars=40)
            if not token:
                continue
            fingerprint = token.casefold()
            if fingerprint in seen_synonyms:
                continue
            seen_synonyms.add(fingerprint)
            synonyms.append(token)
            if len(synonyms) >= POLICY_CORE_COMPACT_PROFILE_ITEMS_MAX:
                break
        if synonyms:
            card["synonyms"] = synonyms

        if len(card) <= 2:
            continue
        cards.append(card)
        if len(cards) >= POLICY_CORE_CONTEXT_CARD_LIMIT:
            break
    return cards


def build_policy_core_context_snapshot(
    *,
    client_slug: str | None,
    info_refs: list[str] | None,
    consult_refs: list[str] | None,
) -> PolicyCoreContextSnapshotV1:
    runtime = get_runtime_capabilities()
    policy_cards = _build_policy_cards(runtime)

    if info_refs is None:
        candidate_info_refs = list(_DEFAULT_INFO_REFS_V1)
    else:
        candidate_info_refs = _normalize_policy_core_ref_candidates(info_refs)
    allowed_info_refs = _filter_fact_refs("info", candidate_info_refs)

    consult_card_catalog: dict[str, dict[str, Any]] = {}
    if consult_refs is None:
        candidate_consult_refs, consult_card_catalog = _load_consult_catalog(client_slug)
    else:
        candidate_consult_refs = _normalize_policy_core_ref_candidates(consult_refs)
        if candidate_consult_refs:
            _, consult_card_catalog = _load_consult_catalog(client_slug)
    allowed_consult_refs = _filter_fact_refs("consult", candidate_consult_refs)

    tool_actions: list[str] = []
    info_context_available = bool(allowed_info_refs or policy_cards)
    consult_context_available = bool(allowed_consult_refs)
    for action in _GENERIC_TOOL_ACTIONS_V1:
        if action == "info" and not info_context_available:
            continue
        if action == "consult" and not consult_context_available:
            continue
        tool_actions.append(action)

    for tool_action in sorted(list_declared_tool_actions()):
        if tool_action.startswith("catalog.") and not allowed_info_refs:
            continue
        if resolve_tool_protocol_decision(tool_action).allowed:
            tool_actions.append(tool_action)

    capability_cards = _build_capability_cards(runtime)
    service_cards = _build_service_cards(client_slug)
    consult_cards = [
        consult_card_catalog[ref]
        for ref in allowed_consult_refs
        if ref in consult_card_catalog
    ][:POLICY_CORE_CONTEXT_CARD_LIMIT]

    return PolicyCoreContextSnapshotV1(
        client_slug=_trim_policy_core_context_text(client_slug, max_chars=64),
        tool_actions=tuple(tool_actions),
        info_refs=tuple(allowed_info_refs),
        consult_refs=tuple(allowed_consult_refs),
        capability_cards=tuple(dict(card) for card in capability_cards),
        policy_cards=tuple(dict(card) for card in policy_cards),
        service_cards=tuple(dict(card) for card in service_cards),
        consult_cards=tuple(dict(card) for card in consult_cards),
    )


__all__ = [
    "PolicyCoreContextSnapshotV1",
    "build_policy_core_context_snapshot",
]
