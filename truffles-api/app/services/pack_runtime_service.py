"""Neutral pack runtime facade.

Runtime callers depend on this module instead of concrete pack implementation.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.services.pack_runtime_default import (
    _build_fact_meta,
    _detect_promotion_intent,
    _format_service_not_found_reply,
    _has_contact_signal,
    _has_duration_signal,
    _has_guest_waiting_signal,
    _has_parking_signal,
    _has_price_signal,
    _match_service,
    _matches_service_request_lexicon,
    _normalize_text,
    build_evening_greeting,
    build_info_combined_reply,
    build_quiet_hours_notice,
    compose_multi_truth_reply,
    format_reply_from_truth,
    get_pack_adapter,
    get_pack_price_item,
    get_pack_price_reply,
    get_pack_service_hint,
    get_signal_lexicon_list,
    get_system_anchor_groups,
    get_system_lexicon_list,
    load_policy_pack,
    load_system_lexicons,
    load_yaml_truth,
    phrase_match_intent,
    semantic_question_type,
    semantic_service_match,
)
from app.services.pack_runtime_default import (
    get_pack_decision as _runtime_get_pack_decision,
)
from app.services.pack_runtime_default import (
    get_pack_service_decision as _runtime_get_pack_service_decision,
)
from app.services.pack_runtime_types import PackDecision

# Backward compatibility alias for existing imports.
DemoSalonDecision = PackDecision

_RESOLVER_CONTRACT_VERSION = "v1"
_RESOLVER_DEFAULT_VERSION = "2026-02-23"
_FACT_BUNDLE_VERSION = "v1"
_RESOLVER_FACT_CONFIDENCE = 0.92
_RESOLVER_COLLECT_CONFIDENCE = 0.42
_RESOLVER_HANDOFF_CONFIDENCE = 0.35
_FACT_FALLBACK_MIN_CONFIDENCE = 0.58
_ACTION_CLASS_BY_ACTION = {
    "collect": "COLLECT",
    "booking_prompt": "COLLECT",
    "booking_confirm": "COLLECT",
    "reply": "FACT",
    "smalltalk": "FACT",
    "fact": "FACT",
    "escalate": "HANDOFF",
    "handoff": "HANDOFF",
    "pending_wait": "HANDOFF",
    "manager_active": "HANDOFF",
}
_WALKIN_WITHOUT_BOOKING_FALLBACK_TERMS = (
    "без записи",
    "без предварительной записи",
    "без очереди",
)
_MASTER_INTENT_RESOLVER_ID = "pack.master_intent"
_MASTER_INTENT_RESOLVER_VERSION = "2026-02-27"
_MASTER_QUERY_DIRECT_TERMS_KEY = "master_query_direct_terms"
_MASTER_QUERY_PERSON_TERMS_KEY = "master_query_person_terms"
_MASTER_QUERY_ACTION_TERMS_KEY = "master_query_action_terms"
_MASTER_QUERY_EXPERIENCE_TERMS_KEY = "master_query_experience_terms"
_MASTER_QUERY_MISSING_SERVICE_REPLY = (
    "Podskazhite, po kakoy usluge nuzhno podobrat mastera?"
)
_MASTER_QUERY_UNKNOWN_SERVICE_REPLY = (
    "Po usluge \"{service}\" utochnu dostupnyh masterov u administratora."
)
_MASTER_QUERY_REPLY_TEMPLATE = "Po usluge \"{service}\" rabotayut: {specialists}."
_MASTER_QUERY_COLLECTION_ACTION = "collect"
_MASTER_QUERY_FACT_ACTION = "reply"
_MASTER_QUERY_FACT_INTENT = "master"
_MASTER_QUERY_SERVICE_CLARIFY_REASON = "missing_service_query"


@dataclass(frozen=True)
class MasterIntentResolution:
    explicit: bool
    service_query: str | None
    service_query_source: str
    needs_service_clarify: bool
    reason: str | None
    matched_signals: list[str]
    resolver_id: str = _MASTER_INTENT_RESOLVER_ID
    resolver_version: str = _MASTER_INTENT_RESOLVER_VERSION


@dataclass(frozen=True)
class MasterReplyDecision:
    response: str | None
    action: str
    intent: str
    meta: dict[str, Any]


def _coerce_text_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned


def _coerce_text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        source = value
    elif isinstance(value, tuple):
        source = list(value)
    elif isinstance(value, str):
        source = [value]
    else:
        return []
    values: list[str] = []
    seen: set[str] = set()
    for item in source:
        token = _coerce_text_token(item)
        if not token:
            continue
        key = token.casefold()
        if key in seen:
            continue
        seen.add(key)
        values.append(token)
    return values


def _first_signal_hit(normalized_message: str, terms: list[str]) -> str | None:
    if not normalized_message:
        return None
    for term in terms:
        normalized_term = _normalize_text(term)
        if normalized_term and normalized_term in normalized_message:
            return normalized_term
    return None


def _normalize_optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip()
    return token or None


def _resolve_master_service_query(
    *,
    message_text: str | None,
    client_slug: str | None,
    service_query: str | None,
    intent_decomp: dict[str, Any] | None,
) -> tuple[str | None, str]:
    explicit_query = _normalize_optional_text(service_query)
    if explicit_query:
        return explicit_query, "input"
    if isinstance(intent_decomp, dict):
        decomp_query = _normalize_optional_text(intent_decomp.get("service_query"))
        if decomp_query:
            return decomp_query, "intent_decomp"
    if message_text:
        semantic_query = get_pack_service_hint(message_text, client_slug=client_slug)
        semantic_query = _normalize_optional_text(semantic_query)
        if semantic_query:
            return semantic_query, "semantic_match"
    return None, "none"


def _master_signal_terms(client_slug: str | None, key: str) -> list[str]:
    return _coerce_text_list(get_signal_lexicon_list(client_slug, key))


def resolve_master_intent(
    *,
    message_text: str | None,
    client_slug: str | None,
    service_query: str | None = None,
    intent_decomp: dict[str, Any] | None = None,
    force_master_intent: bool = False,
) -> MasterIntentResolution:
    normalized_message = _normalize_text(message_text or "")
    direct_terms = _master_signal_terms(client_slug, _MASTER_QUERY_DIRECT_TERMS_KEY)
    person_terms = _master_signal_terms(client_slug, _MASTER_QUERY_PERSON_TERMS_KEY)
    action_terms = _master_signal_terms(client_slug, _MASTER_QUERY_ACTION_TERMS_KEY)
    experience_terms = _master_signal_terms(client_slug, _MASTER_QUERY_EXPERIENCE_TERMS_KEY)

    direct_hit = _first_signal_hit(normalized_message, direct_terms)
    person_hit = _first_signal_hit(normalized_message, person_terms)
    action_hit = _first_signal_hit(normalized_message, action_terms)
    experience_hit = _first_signal_hit(normalized_message, experience_terms)

    explicit = bool(force_master_intent)
    reason: str | None = "forced_master_intent" if force_master_intent else None
    matched_signals: list[str] = []
    if direct_hit:
        matched_signals.append(direct_hit)
    if person_hit:
        matched_signals.append(person_hit)
    if action_hit:
        matched_signals.append(action_hit)
    if experience_hit:
        matched_signals.append(experience_hit)

    if not explicit:
        if direct_hit:
            explicit = True
            reason = "direct_signal"
        elif person_hit and (action_hit or experience_hit):
            explicit = True
            reason = "person_action_signal"

    resolved_service_query, service_query_source = _resolve_master_service_query(
        message_text=message_text,
        client_slug=client_slug,
        service_query=service_query,
        intent_decomp=intent_decomp,
    )
    return MasterIntentResolution(
        explicit=explicit,
        service_query=resolved_service_query,
        service_query_source=service_query_source,
        needs_service_clarify=bool(explicit and not resolved_service_query),
        reason=reason,
        matched_signals=matched_signals,
    )


def _load_master_catalog(truth: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(truth, dict):
        return {}
    catalog = truth.get("masters_catalog")
    if isinstance(catalog, dict):
        return catalog
    return {}


def _format_experience_label(value: Any) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        years = int(value)
        if years <= 0:
            return None
        return f"{years} let opyta"
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return None


def _normalize_service_key(value: str) -> str:
    return _normalize_text(value)


def _service_match(target_service: str, candidate_service: str) -> bool:
    target = _normalize_service_key(target_service)
    candidate = _normalize_service_key(candidate_service)
    if not target or not candidate:
        return False
    return target == candidate or target in candidate or candidate in target


def _extract_master_profiles(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    entries = catalog.get("specialists")
    if not isinstance(entries, list):
        return []
    profiles: list[dict[str, Any]] = []
    for row in entries:
        if not isinstance(row, dict):
            continue
        name = _normalize_optional_text(row.get("name"))
        services = _coerce_text_list(row.get("services"))
        if not name or not services:
            continue
        profile: dict[str, Any] = {
            "name": name,
            "services": services,
        }
        experience_label = _format_experience_label(
            row.get("experience_years") if "experience_years" in row else row.get("experience")
        )
        if experience_label:
            profile["experience_label"] = experience_label
        highlight = _normalize_optional_text(row.get("highlight"))
        if highlight:
            profile["highlight"] = highlight
        profiles.append(profile)
    return profiles


def _render_specialist_line(profile: dict[str, Any]) -> str:
    name = str(profile.get("name") or "").strip()
    if not name:
        return ""
    parts = [name]
    experience_label = _normalize_optional_text(profile.get("experience_label"))
    if experience_label:
        parts.append(experience_label)
    highlight = _normalize_optional_text(profile.get("highlight"))
    if highlight:
        parts.append(highlight)
    return " - ".join(parts)


def build_master_reply_from_pack(
    *,
    client_slug: str | None,
    message_text: str | None,
    resolution: MasterIntentResolution,
) -> MasterReplyDecision | None:
    if not resolution.explicit and not resolution.service_query:
        return None
    truth = load_yaml_truth(client_slug)
    catalog = _load_master_catalog(truth if isinstance(truth, dict) else {})
    query_contract = catalog.get("query_contract") if isinstance(catalog, dict) else {}
    if not isinstance(query_contract, dict):
        query_contract = {}
    missing_service_reply = _normalize_optional_text(query_contract.get("missing_service_reply"))
    if not missing_service_reply:
        missing_service_reply = _MASTER_QUERY_MISSING_SERVICE_REPLY
    service_not_found_reply = _normalize_optional_text(query_contract.get("service_not_found_reply"))
    if not service_not_found_reply:
        service_not_found_reply = _MASTER_QUERY_UNKNOWN_SERVICE_REPLY
    reply_template = _normalize_optional_text(query_contract.get("service_reply_template"))
    if not reply_template:
        reply_template = _MASTER_QUERY_REPLY_TEMPLATE
    max_specialists = query_contract.get("max_specialists")
    if isinstance(max_specialists, bool):
        max_specialists = None
    if not isinstance(max_specialists, int) or max_specialists <= 0:
        max_specialists = 3

    resolved_service = resolution.service_query
    if not resolved_service and message_text:
        resolved_service = get_pack_service_hint(message_text, client_slug=client_slug)
    resolved_service = _normalize_optional_text(resolved_service)
    if not resolved_service:
        meta = _build_fact_meta(
            fact_source="truth",
            fact_intents=[_MASTER_QUERY_FACT_INTENT],
            info_sections=[_MASTER_QUERY_FACT_INTENT],
            meta={
                "master_query_contract": "masters_catalog.v1",
                "master_reply_mode": "service_clarify",
                "clarify_reason": _MASTER_QUERY_SERVICE_CLARIFY_REASON,
                "service_query": None,
                "service_query_source": resolution.service_query_source,
                "master_resolution_reason": resolution.reason,
                "master_resolution_signals": list(resolution.matched_signals),
                "master_resolver_id": resolution.resolver_id,
                "master_resolver_version": resolution.resolver_version,
            },
        )
        return MasterReplyDecision(
            response=missing_service_reply,
            action=_MASTER_QUERY_COLLECTION_ACTION,
            intent=_MASTER_QUERY_FACT_INTENT,
            meta=meta,
        )

    canonical_service = get_pack_service_hint(resolved_service, client_slug=client_slug)
    canonical_service = _normalize_optional_text(canonical_service) or resolved_service
    profiles = _extract_master_profiles(catalog)
    matched_profiles = [
        profile
        for profile in profiles
        if any(_service_match(canonical_service, service_name) for service_name in profile["services"])
    ]
    if not matched_profiles:
        fallback_reply = service_not_found_reply.format(service=canonical_service)
        meta = _build_fact_meta(
            fact_source="truth",
            fact_intents=[_MASTER_QUERY_FACT_INTENT],
            info_sections=[_MASTER_QUERY_FACT_INTENT],
            meta={
                "master_query_contract": "masters_catalog.v1",
                "master_reply_mode": "service_not_found",
                "service_query": canonical_service,
                "service_query_source": resolution.service_query_source,
                "clarify_reason": "master_service_not_found",
                "master_profiles_count": 0,
                "master_resolution_reason": resolution.reason,
                "master_resolution_signals": list(resolution.matched_signals),
                "master_resolver_id": resolution.resolver_id,
                "master_resolver_version": resolution.resolver_version,
            },
        )
        return MasterReplyDecision(
            response=fallback_reply,
            action=_MASTER_QUERY_COLLECTION_ACTION,
            intent=_MASTER_QUERY_FACT_INTENT,
            meta=meta,
        )

    visible_profiles = matched_profiles[:max_specialists]
    specialist_lines = [_render_specialist_line(profile) for profile in visible_profiles]
    specialist_lines = [line for line in specialist_lines if line]
    if not specialist_lines:
        return None
    specialists_text = ", ".join(specialist_lines)
    reply = reply_template.format(service=canonical_service, specialists=specialists_text)
    meta = _build_fact_meta(
        fact_source="truth",
        fact_intents=[_MASTER_QUERY_FACT_INTENT],
        info_sections=[_MASTER_QUERY_FACT_INTENT],
        meta={
            "master_query_contract": "masters_catalog.v1",
            "master_reply_mode": "service_match",
            "service_query": canonical_service,
            "service_query_source": resolution.service_query_source,
            "master_profiles_count": len(matched_profiles),
            "master_profiles": [profile.get("name") for profile in visible_profiles],
            "master_resolution_reason": resolution.reason,
            "master_resolution_signals": list(resolution.matched_signals),
            "master_resolver_id": resolution.resolver_id,
            "master_resolver_version": resolution.resolver_version,
        },
    )
    return MasterReplyDecision(
        response=reply,
        action=_MASTER_QUERY_FACT_ACTION,
        intent=_MASTER_QUERY_FACT_INTENT,
        meta=meta,
    )


def _action_class(action: str | None) -> str:
    token = str(action or "").strip().casefold()
    if not token:
        return "FACT"
    return _ACTION_CLASS_BY_ACTION.get(token, "FACT")


def _coerce_confidence(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        token = float(value)
    elif isinstance(value, str) and value.strip():
        try:
            token = float(value.strip())
        except (TypeError, ValueError):
            return None
    else:
        return None
    return max(0.0, min(token, 1.0))


def _normalize_identifier_token(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    normalized = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.casefold()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    if normalized:
        return normalized
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"id-{digest}"


def _dedupe_entity_refs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        item_id = row.get("id")
        if not isinstance(item_id, str) or not item_id.strip():
            continue
        token = item_id.strip()
        if token in seen:
            continue
        seen.add(token)
        unique_rows.append(row)
    return unique_rows


def _extract_entity_refs(meta: dict[str, Any], *, intent: str | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(meta, dict):
        meta = {}
    service_query = meta.get("service_query")
    if isinstance(service_query, str) and service_query.strip():
        service_id = _normalize_identifier_token(service_query) or "service"
        rows.append(
            {
                "id": f"service:{service_id}",
                "type": "service",
                "label": service_query.strip(),
            }
        )
    price_item = meta.get("price_item")
    if isinstance(price_item, dict):
        item_name = price_item.get("name")
        if isinstance(item_name, str) and item_name.strip():
            item_id = _normalize_identifier_token(item_name) or "price-item"
            rows.append(
                {
                    "id": f"price_item:{item_id}",
                    "type": "price_item",
                    "label": item_name.strip(),
                }
            )
    info_sections = meta.get("info_sections")
    if isinstance(info_sections, list):
        for section in info_sections:
            if not isinstance(section, str) or not section.strip():
                continue
            section_token = section.strip().casefold()
            rows.append(
                {
                    "id": f"info_section:{section_token}",
                    "type": "info_section",
                    "label": section.strip(),
                }
            )
    if isinstance(intent, str) and intent.strip():
        intent_token = intent.strip().casefold()
        rows.append(
            {
                "id": f"intent:{intent_token}",
                "type": "intent",
                "label": intent.strip(),
            }
        )
    return _dedupe_entity_refs(rows)


def _extract_slot_candidates(meta: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(meta, dict):
        return rows
    service_query = meta.get("service_query")
    if isinstance(service_query, str) and service_query.strip():
        rows.append(
            {
                "slot": "service",
                "value": service_query.strip(),
                "source": str(meta.get("service_query_source") or "resolver"),
            }
        )
    expected_reply_type = meta.get("expected_reply_type")
    if isinstance(expected_reply_type, str) and expected_reply_type.strip():
        rows.append(
            {
                "slot": expected_reply_type.strip(),
                "value": meta.get("expected_reply_value"),
                "source": "expected_reply",
            }
        )
    return rows


def _resolve_pack_id(meta: dict[str, Any], *, client_slug: str | None) -> str:
    if not isinstance(meta, dict):
        meta = {}
    for key in ("pack_id", "knowledge_tag", "policy_type"):
        token = meta.get(key)
        if isinstance(token, str) and token.strip():
            return token.strip()
    if isinstance(client_slug, str) and client_slug.strip():
        return client_slug.strip()
    return "neutral_pack"


def _build_fact_bundle(
    *,
    meta: dict[str, Any],
    intent: str | None,
    action_class: str,
    confidence: float,
    abstain_reason: str | None,
    entity_refs: list[dict[str, Any]],
    client_slug: str | None,
) -> dict[str, Any]:
    intent_token = intent.strip() if isinstance(intent, str) and intent.strip() else None
    entity_id = None
    if entity_refs:
        first_ref = entity_refs[0]
        if isinstance(first_ref, dict):
            ref_id = first_ref.get("id")
            if isinstance(ref_id, str) and ref_id.strip():
                entity_id = ref_id.strip()
    fact_source = meta.get("fact_source")
    if isinstance(fact_source, str) and fact_source.strip():
        source_ref = fact_source.strip()
    elif intent_token:
        source_ref = f"intent:{intent_token.casefold()}"
    else:
        source_ref = "intent:unknown"
    return {
        "version": _FACT_BUNDLE_VERSION,
        "pack_id": _resolve_pack_id(meta, client_slug=client_slug),
        "entity_id": entity_id,
        "source_ref": source_ref,
        "confidence": confidence,
        "action_class": action_class,
        "intent_class": intent_token,
        "abstain_reason": abstain_reason,
    }


def _derive_resolver_confidence(meta: dict[str, Any], *, action_class: str) -> float:
    if isinstance(meta, dict):
        for key in (
            "resolver_confidence",
            "service_query_score",
            "question_type_score",
            "semantic_score",
            "score",
        ):
            score = _coerce_confidence(meta.get(key))
            if score is not None:
                return score
    if action_class == "COLLECT":
        return _RESOLVER_COLLECT_CONFIDENCE
    if action_class == "HANDOFF":
        return _RESOLVER_HANDOFF_CONFIDENCE
    return _RESOLVER_FACT_CONFIDENCE


def _derive_abstain_reason(
    meta: dict[str, Any],
    *,
    action_class: str,
    confidence: float,
) -> str | None:
    if not isinstance(meta, dict):
        meta = {}
    explicit_reason = meta.get("abstain_reason")
    if isinstance(explicit_reason, str) and explicit_reason.strip():
        return explicit_reason.strip()
    if action_class == "COLLECT":
        for key in (
            "clarify_reason",
            "expected_reply_reason",
            "llm_policy_override_reason_code",
        ):
            value = meta.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return "low_confidence_collect"
    if action_class == "HANDOFF":
        handoff_reason = meta.get("llm_policy_override_reason_code") or meta.get("policy_section")
        if isinstance(handoff_reason, str) and handoff_reason.strip():
            return handoff_reason.strip()
        return "handoff_required"
    if confidence < 0.5:
        return "low_confidence"
    return None


def ensure_resolver_meta(
    meta: dict[str, Any] | None,
    *,
    action: str | None,
    intent: str | None,
    resolver_id: str,
    resolver_version: str | None = None,
    ruleset_version: str | None = None,
    client_slug: str | None = None,
) -> dict[str, Any]:
    payload = dict(meta) if isinstance(meta, dict) else {}
    resolver_id_token = (
        str(payload.get("resolver_id") or resolver_id or "").strip()
        or "pack_runtime"
    )
    resolver_version_token = (
        str(payload.get("resolver_version") or resolver_version or "").strip()
        or _RESOLVER_DEFAULT_VERSION
    )
    ruleset_token = (
        str(payload.get("ruleset_version") or ruleset_version or "").strip()
        or resolver_version_token
    )
    action_class = _action_class(action)
    intent_token = intent.strip().casefold() if isinstance(intent, str) and intent.strip() else ""
    if action_class == "FACT" and intent_token in {
        "service_not_found",
        "service_clarify",
        "duration_or_price_clarify",
        "info_clarify",
    }:
        action_class = "COLLECT"
    entity_refs = _extract_entity_refs(payload, intent=intent)
    slot_candidates = _extract_slot_candidates(payload)
    confidence = _derive_resolver_confidence(payload, action_class=action_class)
    abstain_reason = _derive_abstain_reason(
        payload,
        action_class=action_class,
        confidence=confidence,
    )
    intent_class = intent.strip() if isinstance(intent, str) and intent.strip() else None
    resolver_contract = {
        "intent_class": intent_class,
        "action_class": action_class,
        "entity_refs": entity_refs,
        "slot_candidates": slot_candidates,
        "confidence": confidence,
        "abstain_reason": abstain_reason,
        "resolver_id": resolver_id_token,
        "resolver_version": resolver_version_token,
        "ruleset_version": ruleset_token,
    }
    fact_bundle = _build_fact_bundle(
        meta=payload,
        intent=intent,
        action_class=action_class,
        confidence=confidence,
        abstain_reason=abstain_reason,
        entity_refs=entity_refs,
        client_slug=client_slug,
    )
    payload.update(resolver_contract)
    payload["resolver_contract_version"] = _RESOLVER_CONTRACT_VERSION
    payload["resolver_contract"] = resolver_contract
    payload["resolver_confidence"] = confidence
    payload["resolver_candidates"] = entity_refs
    payload["fact_bundle"] = fact_bundle
    payload["provenance"] = {
        "pack_id": fact_bundle["pack_id"],
        "entity_id": fact_bundle["entity_id"],
        "source_ref": fact_bundle["source_ref"],
        "confidence": fact_bundle["confidence"],
    }
    return payload


def enrich_pack_decision(
    decision: PackDecision | None,
    *,
    resolver_id: str,
    resolver_version: str | None = None,
    ruleset_version: str | None = None,
    client_slug: str | None = None,
) -> PackDecision | None:
    if not isinstance(decision, PackDecision):
        return decision
    resolved_meta = ensure_resolver_meta(
        decision.meta if isinstance(decision.meta, dict) else {},
        action=decision.action,
        intent=decision.intent,
        resolver_id=resolver_id,
        resolver_version=resolver_version,
        ruleset_version=ruleset_version,
        client_slug=client_slug,
    )
    return PackDecision(
        action=decision.action,
        response=decision.response,
        intent=decision.intent,
        collect=decision.collect,
        meta=resolved_meta,
    )


def get_pack_decision(
    message: str,
    *,
    client_slug: str | None = None,
    intent_decomp: dict | None = None,
) -> PackDecision | None:
    decision = _runtime_get_pack_decision(
        message,
        client_slug=client_slug,
        intent_decomp=intent_decomp,
    )
    return enrich_pack_decision(
        decision,
        resolver_id="pack_runtime.truth_gate",
        client_slug=client_slug,
    )


def get_pack_service_decision(
    message: str,
    *,
    client_slug: str | None = None,
    intent_decomp: dict | None = None,
) -> PackDecision | None:
    decision = _runtime_get_pack_service_decision(
        message,
        client_slug=client_slug,
        intent_decomp=intent_decomp,
    )
    return enrich_pack_decision(
        decision,
        resolver_id="pack_runtime.service_matcher",
        client_slug=client_slug,
    )


def has_consult_recommendation_signal(decision: PackDecision | None) -> bool:
    if not isinstance(decision, PackDecision):
        return False
    meta = decision.meta if isinstance(decision.meta, dict) else {}
    if bool(meta.get("consult_recommendation")):
        return True
    fact_intents = meta.get("fact_intents")
    if isinstance(fact_intents, list) and any(
        isinstance(item, str) and item.strip().casefold() == "consult_reply" for item in fact_intents
    ):
        return True
    intent_token = decision.intent.strip().casefold() if isinstance(decision.intent, str) else ""
    resolver_contract = meta.get("resolver_contract")
    if isinstance(resolver_contract, dict):
        intent_class = resolver_contract.get("intent_class")
        if isinstance(intent_class, str) and intent_class.strip().casefold() == "consult_reply":
            return True
    return intent_token == "consult_reply"


def is_timeout_fact_fallback_candidate(
    decision: PackDecision | None,
    *,
    min_confidence: float = _FACT_FALLBACK_MIN_CONFIDENCE,
) -> bool:
    if not isinstance(decision, PackDecision):
        return False
    if not isinstance(decision.response, str) or not decision.response.strip():
        return False
    action = str(decision.action or "").strip().casefold()
    if action != "reply":
        return False
    meta = decision.meta if isinstance(decision.meta, dict) else {}
    resolver_contract = meta.get("resolver_contract")
    action_class = None
    abstain_reason = None
    confidence = None
    if isinstance(resolver_contract, dict):
        action_class = resolver_contract.get("action_class")
        abstain_reason = resolver_contract.get("abstain_reason")
        confidence = _coerce_confidence(resolver_contract.get("confidence"))
    if not isinstance(action_class, str):
        action_class = meta.get("action_class")
    if not isinstance(abstain_reason, str):
        abstain_reason = meta.get("abstain_reason")
    if confidence is None:
        confidence = _coerce_confidence(meta.get("resolver_confidence"))
    if confidence is None:
        confidence = _RESOLVER_FACT_CONFIDENCE
    if not isinstance(action_class, str) or action_class.strip().upper() != "FACT":
        return False
    if isinstance(abstain_reason, str) and abstain_reason.strip():
        return False
    return confidence >= max(0.0, min(float(min_confidence), 1.0))


def has_walkin_without_booking_signal(
    message_text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    normalized = _normalize_text(message_text or "")
    if not normalized:
        return False
    terms = get_signal_lexicon_list(client_slug, "walkin_without_booking_terms")
    if not terms:
        terms = get_system_lexicon_list("walkin_without_booking_terms")
    if not terms:
        terms = list(_WALKIN_WITHOUT_BOOKING_FALLBACK_TERMS)
    normalized_terms = []
    for term in terms:
        token = _normalize_text(term) if isinstance(term, str) else ""
        if token:
            normalized_terms.append(token)
    return any(token in normalized for token in normalized_terms)


__all__ = [
    "PackDecision",
    "DemoSalonDecision",
    "_build_fact_meta",
    "_has_contact_signal",
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
    "build_master_reply_from_pack",
    "build_quiet_hours_notice",
    "compose_multi_truth_reply",
    "enrich_pack_decision",
    "ensure_resolver_meta",
    "format_reply_from_truth",
    "get_pack_adapter",
    "get_pack_decision",
    "get_pack_price_item",
    "get_pack_price_reply",
    "get_pack_service_decision",
    "get_pack_service_hint",
    "has_consult_recommendation_signal",
    "get_signal_lexicon_list",
    "get_system_anchor_groups",
    "get_system_lexicon_list",
    "has_walkin_without_booking_signal",
    "is_timeout_fact_fallback_candidate",
    "load_policy_pack",
    "load_system_lexicons",
    "load_yaml_truth",
    "phrase_match_intent",
    "resolve_master_intent",
    "semantic_question_type",
    "semantic_service_match",
    "MasterIntentResolution",
    "MasterReplyDecision",
]
