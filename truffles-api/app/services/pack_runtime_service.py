"""Neutral pack runtime facade.

Runtime callers depend on this module instead of concrete pack implementation.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.services.knowledge_runtime import get_runtime_truth
from app.services.pack_query_backend_service import (
    PackQueryBackendCandidate,
    PackQueryBackendLookup,
    get_pack_query_retrieval_mode,
    resolve_backend_candidates,
)
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
    get_signal_lexicon_list,
    get_system_anchor_groups,
    get_system_lexicon_list,
    load_policy_pack,
    load_system_lexicons,
    load_yaml_truth,
    phrase_match_intent,
    semantic_question_type,
)
from app.services.pack_runtime_default import (
    get_pack_decision as _runtime_get_pack_decision,
)
from app.services.pack_runtime_default import (
    get_pack_service_decision as _runtime_get_pack_service_decision,
)
from app.services.pack_runtime_default import (
    get_pack_service_hint as _runtime_get_pack_service_hint,
)
from app.services.pack_runtime_default import (
    semantic_service_match as _runtime_semantic_service_match,
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
_MASTER_QUERY_RELATION_TERMS_KEY = "master_query_relation_terms"
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
_PACK_QUERY_ENGINE_ID = "pack_query_engine.v2"
_PACK_QUERY_ENGINE_VERSION = "2026-03-02"
_PACK_QUERY_MATCH_MIN_SCORE = 0.56
_PACK_QUERY_HINT_MIN_SCORE = 0.48
_PACK_QUERY_SUGGEST_MIN_SCORE = 0.32
_PACK_QUERY_MAX_SUGGESTIONS = 5
_PACK_QUERY_FALLBACK_PRESENCE_REPLY = "Da, usluga {service} dostupna."
_PACK_QUERY_FALLBACK_NOT_FOUND_REPLY = (
    "V spiske uslug net takoi pozicii. Mogu predlozhit: {suggestions}."
)
_SEMANTIC_SUBJECT_REFERENT_KEY = {
    "service": "service",
    "specialist": "master",
    "booking": "booking_ref",
    "branch": "branch",
}
_CAPABILITY_INFO_REF_MAP = {
    "pricing": ["pricing"],
    "duration": ["duration"],
    "location": ["location"],
    "hours": ["hours"],
    "promotions": ["promotions"],
}


@dataclass(frozen=True)
class PackQuerySemanticMatch:
    action: str
    response: str
    score: float
    canonical_name: str | None = None
    suggestions: list[str] | None = None
    meta: dict[str, Any] | None = None


@dataclass(frozen=True)
class PackQueryCandidate:
    canonical_name: str
    sparse_score: float
    dense_score: float
    rerank_bonus: float
    final_score: float
    matched_alias: str | None = None
    service_item: dict[str, Any] | None = None


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


def _normalize_scope_token(value: Any) -> str | None:
    if value is None:
        return None
    token = str(value).strip()
    if not token:
        return None
    return token.casefold()


def _coerce_scope_values(value: Any) -> set[str]:
    if isinstance(value, (list, tuple, set)):
        source = value
    elif value is None:
        source = []
    else:
        source = [value]
    tokens: set[str] = set()
    for item in source:
        if isinstance(item, dict):
            for key in ("id", "slug", "code", "name"):
                token = _normalize_scope_token(item.get(key))
                if token:
                    tokens.add(token)
            continue
        token = _normalize_scope_token(item)
        if token:
            tokens.add(token)
    return tokens


def _resolve_runtime_scope(client_slug: str | None) -> tuple[str | None, str | None]:
    runtime_truth = get_runtime_truth()
    runtime_slug = _normalize_scope_token(runtime_truth.client_slug) if runtime_truth else None
    runtime_branch = _normalize_scope_token(runtime_truth.branch_id) if runtime_truth else None
    requested_slug = _normalize_scope_token(client_slug)
    effective_slug = requested_slug or runtime_slug
    return effective_slug, runtime_branch


def _service_entries_from_truth(truth: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(truth, dict):
        return []
    containers: list[Any] = [
        truth.get("services_catalog"),
    ]
    client_pack = truth.get("client_pack")
    if isinstance(client_pack, dict):
        containers.append(client_pack.get("services_catalog"))
    rows: list[dict[str, Any]] = []
    for container in containers:
        if isinstance(container, list):
            rows.extend(item for item in container if isinstance(item, dict))
            continue
        if not isinstance(container, dict):
            continue
        for key in ("services", "items"):
            values = container.get(key)
            if isinstance(values, list):
                rows.extend(item for item in values if isinstance(item, dict))
                break
    return rows


def _service_aliases(service_item: dict[str, Any]) -> list[str]:
    aliases = _coerce_text_list(service_item.get("aliases"))
    name = _coerce_text_token(service_item.get("name"))
    if name:
        aliases.insert(0, name)
    unique: list[str] = []
    seen: set[str] = set()
    for alias in aliases:
        normalized = _normalize_text(alias)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(alias.strip())
    return unique


def _tenant_scope_for_service(service_item: dict[str, Any]) -> set[str]:
    tenant_scope = _coerce_scope_values(service_item.get("tenant_slug"))
    tenant_scope |= _coerce_scope_values(service_item.get("tenant"))
    tenant_scope |= _coerce_scope_values(service_item.get("client_slug"))
    tenant_scope |= _coerce_scope_values(service_item.get("client"))
    return tenant_scope


def _branch_scope_for_service(service_item: dict[str, Any]) -> set[str]:
    branch_scope = _coerce_scope_values(service_item.get("branch_id"))
    branch_scope |= _coerce_scope_values(service_item.get("branch_ids"))
    branch_scope |= _coerce_scope_values(service_item.get("branches"))
    branch_scope |= _coerce_scope_values(service_item.get("branch_scope"))
    return branch_scope


def _tokenize(text: str) -> set[str]:
    normalized = _normalize_text(text)
    return {token for token in normalized.split() if token}


def _token_overlap_score(query_tokens: set[str], alias_tokens: set[str]) -> float:
    if not query_tokens or not alias_tokens:
        return 0.0
    overlap = len(query_tokens & alias_tokens)
    if overlap <= 0:
        return 0.0
    return min(1.0, overlap / float(max(len(query_tokens), len(alias_tokens))))


def _char_ngram_score(query_text: str, alias_text: str, n: int = 3) -> float:
    if not query_text or not alias_text:
        return 0.0
    query_norm = _normalize_text(query_text).replace(" ", "")
    alias_norm = _normalize_text(alias_text).replace(" ", "")
    if len(query_norm) < n or len(alias_norm) < n:
        return 1.0 if query_norm == alias_norm else 0.0
    query_grams = {query_norm[idx : idx + n] for idx in range(len(query_norm) - n + 1)}
    alias_grams = {alias_norm[idx : idx + n] for idx in range(len(alias_norm) - n + 1)}
    if not query_grams or not alias_grams:
        return 0.0
    union = len(query_grams | alias_grams)
    if union <= 0:
        return 0.0
    return len(query_grams & alias_grams) / float(union)


def _sparse_alias_score(query_text: str, alias: str) -> float:
    query_tokens = _tokenize(query_text)
    alias_tokens = _tokenize(alias)
    overlap = _token_overlap_score(query_tokens, alias_tokens)
    ngram = _char_ngram_score(query_text, alias)
    score = 0.72 * overlap + 0.28 * ngram
    query_norm = _normalize_text(query_text)
    alias_norm = _normalize_text(alias)
    if query_norm and alias_norm and (query_norm in alias_norm or alias_norm in query_norm):
        score += 0.12
    return max(0.0, min(score, 1.0))


def _semantic_rerank_bonus(query_text: str, alias: str) -> float:
    query_norm = _normalize_text(query_text)
    alias_norm = _normalize_text(alias)
    if not query_norm or not alias_norm:
        return 0.0
    if query_norm == alias_norm:
        return 0.22
    if alias_norm.startswith(query_norm) or query_norm.startswith(alias_norm):
        return 0.12
    if alias_norm in query_norm or query_norm in alias_norm:
        return 0.08
    return 0.0


def _supports_branch_filter(service_item: dict[str, Any]) -> bool:
    return bool(_branch_scope_for_service(service_item))


def _pack_query_catalog_templates(truth: dict[str, Any]) -> tuple[str, str]:
    if not isinstance(truth, dict):
        return _PACK_QUERY_FALLBACK_PRESENCE_REPLY, _PACK_QUERY_FALLBACK_NOT_FOUND_REPLY
    containers: list[Any] = [truth.get("services_catalog")]
    client_pack = truth.get("client_pack")
    if isinstance(client_pack, dict):
        containers.append(client_pack.get("services_catalog"))
    presence_reply = None
    not_found_reply = None
    for container in containers:
        if not isinstance(container, dict):
            continue
        if not presence_reply:
            token = _coerce_text_token(container.get("service_presence_reply"))
            if token:
                presence_reply = token
        if not not_found_reply:
            token = _coerce_text_token(container.get("not_found_reply"))
            if token:
                not_found_reply = token
    return (
        presence_reply or _PACK_QUERY_FALLBACK_PRESENCE_REPLY,
        not_found_reply or _PACK_QUERY_FALLBACK_NOT_FOUND_REPLY,
    )


def _runtime_dense_signal(
    text: str,
    *,
    client_slug: str | None,
) -> tuple[str | None, float, str | None]:
    runtime_semantic = _runtime_semantic_service_match(text, client_slug or "generic")
    if not runtime_semantic:
        return None, 0.0, None
    dense_action = _coerce_text_token(getattr(runtime_semantic, "action", None))
    dense_name = _normalize_text(str(getattr(runtime_semantic, "canonical_name", "") or ""))
    dense_score = _coerce_confidence(getattr(runtime_semantic, "score", None)) or 0.0
    return dense_action, dense_score, dense_name


def _service_entries_in_scope(
    truth: dict[str, Any],
    *,
    effective_slug: str | None,
    effective_branch: str | None,
) -> tuple[list[dict[str, Any]], dict[str, bool]]:
    scoped_items: list[dict[str, Any]] = []
    branch_scoped_items_seen = False
    filtered_out_by_branch = False
    filtered_out_by_tenant = False
    for service_item in _service_entries_from_truth(truth):
        canonical_name = _coerce_text_token(service_item.get("name"))
        if not canonical_name:
            continue
        tenant_scope = _tenant_scope_for_service(service_item)
        if effective_slug and tenant_scope and effective_slug not in tenant_scope:
            filtered_out_by_tenant = True
            continue
        branch_scope = _branch_scope_for_service(service_item)
        if branch_scope:
            branch_scoped_items_seen = True
        if effective_branch and branch_scope and effective_branch not in branch_scope:
            filtered_out_by_branch = True
            continue
        scoped_items.append(service_item)
    return scoped_items, {
        "branch_filter_active": bool(effective_branch),
        "branch_scoped_items_seen": branch_scoped_items_seen,
        "filtered_out_by_branch": filtered_out_by_branch,
        "filtered_out_by_tenant": filtered_out_by_tenant,
    }


def _match_backend_candidate_to_scope(
    candidate: PackQueryBackendCandidate,
    *,
    scoped_items: list[dict[str, Any]],
) -> tuple[dict[str, Any], str, str | None] | None:
    candidate_norm = _normalize_text(candidate.canonical_name)
    if not candidate_norm:
        return None
    alias_match: tuple[dict[str, Any], str, str | None] | None = None
    for service_item in scoped_items:
        canonical_name = _coerce_text_token(service_item.get("name"))
        if not canonical_name:
            continue
        canonical_norm = _normalize_text(canonical_name)
        if candidate_norm == canonical_norm:
            return service_item, canonical_name, None
        if alias_match is not None:
            continue
        for alias in _service_aliases(service_item):
            if _normalize_text(alias) == candidate_norm:
                alias_match = (service_item, canonical_name, alias)
                break
    return alias_match


def _to_pack_query_candidate_from_backend(
    backend_candidate: PackQueryBackendCandidate,
    *,
    text: str,
    scoped_items: list[dict[str, Any]],
) -> PackQueryCandidate | None:
    matched = _match_backend_candidate_to_scope(backend_candidate, scoped_items=scoped_items)
    if matched is None:
        return None
    service_item, canonical_name, alias_hit = matched
    sparse_score = backend_candidate.sparse_score
    if sparse_score <= 0.0:
        sparse_score = _sparse_alias_score(text, alias_hit or canonical_name)
    dense_score = backend_candidate.dense_score
    if dense_score <= 0.0:
        dense_score = max(backend_candidate.score, sparse_score)
    rerank_bonus = backend_candidate.rerank_bonus
    final_score = backend_candidate.score
    if final_score <= 0.0:
        final_score = min(1.0, 0.58 * dense_score + 0.42 * sparse_score + rerank_bonus)
    if final_score <= 0.0:
        return None
    return PackQueryCandidate(
        canonical_name=canonical_name,
        sparse_score=max(0.0, min(sparse_score, 1.0)),
        dense_score=max(0.0, min(dense_score, 1.0)),
        rerank_bonus=max(0.0, min(rerank_bonus, 1.0)),
        final_score=max(0.0, min(final_score, 1.0)),
        matched_alias=alias_hit or backend_candidate.matched_alias,
        service_item=service_item,
    )


def _backend_candidates_in_scope(
    backend_lookup: PackQueryBackendLookup,
    *,
    text: str,
    scoped_items: list[dict[str, Any]],
) -> list[PackQueryCandidate]:
    selected: dict[str, PackQueryCandidate] = {}
    for backend_candidate in backend_lookup.candidates:
        candidate = _to_pack_query_candidate_from_backend(
            backend_candidate,
            text=text,
            scoped_items=scoped_items,
        )
        if candidate is None:
            continue
        key = _normalize_text(candidate.canonical_name)
        previous = selected.get(key)
        if previous and previous.final_score >= candidate.final_score:
            continue
        selected[key] = candidate
    return sorted(selected.values(), key=lambda row: row.final_score, reverse=True)


def _pack_query_backend_status(lookup: PackQueryBackendLookup) -> dict[str, Any]:
    meta = lookup.meta if isinstance(lookup.meta, dict) else {}
    payload = {
        "mode": _coerce_text_token(meta.get("mode")),
        "driver": _coerce_text_token(meta.get("driver")),
        "engine": _coerce_text_token(meta.get("engine")),
        "engine_version": _coerce_text_token(meta.get("engine_version")),
        "method": _coerce_text_token(meta.get("method")),
        "available": bool(lookup.available),
        "unavailable_reason": _coerce_text_token(lookup.unavailable_reason),
    }
    return payload


def _build_pack_query_candidates_local(
    text: str,
    *,
    client_slug: str | None,
    branch_id: str | None = None,
) -> tuple[list[PackQueryCandidate], dict[str, Any]]:
    truth = load_yaml_truth(client_slug)
    if not isinstance(truth, dict):
        return [], {}
    effective_slug, runtime_branch = _resolve_runtime_scope(client_slug)
    effective_branch = _normalize_scope_token(branch_id) or runtime_branch
    dense_action, dense_score, dense_name = _runtime_dense_signal(
        text,
        client_slug=client_slug,
    )

    candidates: list[PackQueryCandidate] = []
    scoped_items, scope_meta = _service_entries_in_scope(
        truth,
        effective_slug=effective_slug,
        effective_branch=effective_branch,
    )
    for service_item in scoped_items:
        canonical_name = _coerce_text_token(service_item.get("name"))
        if not canonical_name:
            continue
        aliases = _service_aliases(service_item)
        if not aliases:
            aliases = [canonical_name]

        best_sparse = 0.0
        best_bonus = 0.0
        best_alias = None
        for alias in aliases:
            sparse_score = _sparse_alias_score(text, alias)
            if sparse_score <= 0.0:
                continue
            rerank_bonus = _semantic_rerank_bonus(text, alias)
            if sparse_score > best_sparse:
                best_sparse = sparse_score
                best_bonus = rerank_bonus
                best_alias = alias

        dense_match_score = 0.0
        canonical_norm = _normalize_text(canonical_name)
        if dense_name and canonical_norm and dense_name == canonical_norm:
            dense_match_score = dense_score
        elif dense_name and dense_score > 0.0:
            for alias in aliases:
                if _normalize_text(alias) == dense_name:
                    dense_match_score = dense_score
                    break

        if best_sparse <= 0.0 and dense_match_score <= 0.0:
            continue

        hybrid_score = 0.58 * dense_match_score + 0.42 * best_sparse
        final_score = max(0.0, min(hybrid_score + best_bonus, 1.0))
        candidates.append(
            PackQueryCandidate(
                canonical_name=canonical_name,
                sparse_score=best_sparse,
                dense_score=dense_match_score,
                rerank_bonus=best_bonus,
                final_score=final_score,
                matched_alias=best_alias,
                service_item=service_item,
            )
        )

    candidates.sort(key=lambda row: row.final_score, reverse=True)
    templates = _pack_query_catalog_templates(truth)
    meta = {
        "engine": _PACK_QUERY_ENGINE_ID,
        "engine_version": _PACK_QUERY_ENGINE_VERSION,
        "method": "hybrid_sparse_semantic_rerank",
        "filters": {
            "tenant_slug": effective_slug,
            "branch_id": effective_branch,
        },
        "scope": scope_meta,
        "dense_signal": {
            "action": dense_action,
            "canonical_name": dense_name,
            "score": dense_score,
        },
        "candidate_count": len(candidates),
        "templates": {
            "presence_reply": templates[0],
            "not_found_reply": templates[1],
        },
    }
    return candidates, meta


def _build_pack_query_candidates(
    text: str,
    *,
    client_slug: str | None,
    branch_id: str | None = None,
) -> tuple[list[PackQueryCandidate], dict[str, Any]]:
    local_candidates, local_meta = _build_pack_query_candidates_local(
        text,
        client_slug=client_slug,
        branch_id=branch_id,
    )
    retrieval_mode = get_pack_query_retrieval_mode()
    if retrieval_mode == "runtime_local":
        runtime_meta = dict(local_meta)
        runtime_meta["retrieval_mode"] = "runtime_local"
        runtime_meta["selected_source"] = "runtime_local"
        return local_candidates, runtime_meta

    filters = local_meta.get("filters") if isinstance(local_meta.get("filters"), dict) else {}
    effective_branch = _coerce_text_token(filters.get("branch_id"))
    backend_lookup = resolve_backend_candidates(
        query_text=text,
        client_slug=client_slug,
        branch_id=effective_branch,
    )
    backend_status = _pack_query_backend_status(backend_lookup)

    if retrieval_mode == "backend_shadow":
        shadow_meta = dict(local_meta)
        shadow_meta["retrieval_mode"] = "backend_shadow"
        shadow_meta["selected_source"] = "runtime_local"
        shadow_meta["backend"] = backend_status
        shadow_meta["backend_candidate_count"] = len(backend_lookup.candidates)
        return local_candidates, shadow_meta

    truth = load_yaml_truth(client_slug)
    if not isinstance(truth, dict):
        truth = {}
    effective_slug, runtime_branch = _resolve_runtime_scope(client_slug)
    scoped_branch = _normalize_scope_token(branch_id) or runtime_branch
    scoped_items, _ = _service_entries_in_scope(
        truth,
        effective_slug=effective_slug,
        effective_branch=scoped_branch,
    )
    backend_candidates = _backend_candidates_in_scope(
        backend_lookup,
        text=text,
        scoped_items=scoped_items,
    )

    if backend_candidates:
        backend_meta = dict(local_meta)
        driver_meta = backend_lookup.meta if isinstance(backend_lookup.meta, dict) else {}
        backend_meta["engine"] = _coerce_text_token(driver_meta.get("engine")) or backend_meta.get("engine")
        backend_meta["engine_version"] = _coerce_text_token(driver_meta.get("engine_version")) or backend_meta.get(
            "engine_version"
        )
        backend_meta["method"] = _coerce_text_token(driver_meta.get("method")) or backend_meta.get("method")
        backend_meta["candidate_count"] = len(backend_candidates)
        backend_meta["retrieval_mode"] = "backend_primary"
        backend_meta["selected_source"] = "backend_primary"
        backend_meta["backend"] = backend_status
        return backend_candidates, backend_meta

    fallback_reason = "backend_scope_filtered"
    if not backend_lookup.available:
        fallback_reason = "backend_unavailable"
    elif backend_lookup.unavailable_reason == "no_candidates":
        fallback_reason = "backend_empty"
    fallback_meta = dict(local_meta)
    fallback_meta["retrieval_mode"] = "backend_primary"
    fallback_meta["selected_source"] = "runtime_local_fallback"
    fallback_meta["backend"] = backend_status
    fallback_meta["fallback_reason"] = fallback_reason
    return local_candidates, fallback_meta


def _build_pack_query_retrieval_meta(
    candidates: list[PackQueryCandidate],
    *,
    engine_meta: dict[str, Any],
) -> dict[str, Any]:
    best = candidates[0] if candidates else None
    suggestions = [candidate.canonical_name for candidate in candidates[:_PACK_QUERY_MAX_SUGGESTIONS]]
    payload = {
        "engine": engine_meta.get("engine"),
        "engine_version": engine_meta.get("engine_version"),
        "method": engine_meta.get("method"),
        "candidate_count": len(candidates),
        "filters": engine_meta.get("filters") if isinstance(engine_meta.get("filters"), dict) else {},
        "scope": engine_meta.get("scope") if isinstance(engine_meta.get("scope"), dict) else {},
        "best_candidate": best.canonical_name if best else None,
        "best_score": round(float(best.final_score), 4) if best else 0.0,
        "best_sparse_score": round(float(best.sparse_score), 4) if best else 0.0,
        "best_dense_score": round(float(best.dense_score), 4) if best else 0.0,
        "best_rerank_bonus": round(float(best.rerank_bonus), 4) if best else 0.0,
        "suggestions": suggestions,
    }
    retrieval_mode = _coerce_text_token(engine_meta.get("retrieval_mode"))
    if retrieval_mode:
        payload["retrieval_mode"] = retrieval_mode
    selected_source = _coerce_text_token(engine_meta.get("selected_source"))
    if selected_source:
        payload["selected_source"] = selected_source
    fallback_reason = _coerce_text_token(engine_meta.get("fallback_reason"))
    if fallback_reason:
        payload["fallback_reason"] = fallback_reason
    backend_candidate_count = engine_meta.get("backend_candidate_count")
    if isinstance(backend_candidate_count, int) and backend_candidate_count >= 0:
        payload["backend_candidate_count"] = backend_candidate_count
    backend = engine_meta.get("backend")
    if isinstance(backend, dict):
        payload["backend"] = {
            "mode": _coerce_text_token(backend.get("mode")),
            "driver": _coerce_text_token(backend.get("driver")),
            "engine": _coerce_text_token(backend.get("engine")),
            "engine_version": _coerce_text_token(backend.get("engine_version")),
            "method": _coerce_text_token(backend.get("method")),
            "available": bool(backend.get("available")),
            "unavailable_reason": _coerce_text_token(backend.get("unavailable_reason")),
        }
    return payload


def _to_runtime_semantic_match(raw_match: Any, *, meta: dict[str, Any] | None = None) -> PackQuerySemanticMatch | None:
    if raw_match is None:
        return None
    action = _coerce_text_token(getattr(raw_match, "action", None))
    response = _coerce_text_token(getattr(raw_match, "response", None))
    if not action or not response:
        return None
    score = _coerce_confidence(getattr(raw_match, "score", None)) or 0.0
    canonical_name = _coerce_text_token(getattr(raw_match, "canonical_name", None))
    suggestions = _coerce_text_list(getattr(raw_match, "suggestions", None))
    return PackQuerySemanticMatch(
        action=action,
        response=response,
        score=score,
        canonical_name=canonical_name,
        suggestions=suggestions or None,
        meta=meta,
    )


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


def _has_token_follow_relation(
    normalized_message: str,
    *,
    anchor_text: str,
    follower_terms: list[str],
) -> bool:
    message_tokens = [token for token in normalized_message.split() if token]
    anchor_tokens = [token for token in _normalize_text(anchor_text).split() if token]
    if not message_tokens or not anchor_tokens or not follower_terms:
        return False
    follower_token_set = {
        token
        for term in follower_terms
        for token in [_normalize_text(term)]
        if token
    }
    if not follower_token_set:
        return False
    anchor_length = len(anchor_tokens)
    last_start = len(message_tokens) - anchor_length
    for start in range(last_start + 1):
        if message_tokens[start : start + anchor_length] != anchor_tokens:
            continue
        follower_index = start + anchor_length
        if follower_index < len(message_tokens) and message_tokens[follower_index] in follower_token_set:
            return True
    return False


def _has_master_person_service_relation(
    normalized_message: str,
    *,
    client_slug: str | None,
    person_hit: str | None,
) -> bool:
    if not normalized_message or not person_hit:
        return False
    candidate = person_hit.strip()
    if not candidate:
        return False
    relation_terms = _master_signal_terms(client_slug, _MASTER_QUERY_RELATION_TERMS_KEY)
    return _has_token_follow_relation(
        normalized_message,
        anchor_text=candidate,
        follower_terms=relation_terms,
    )


def _first_master_name_hit(normalized_message: str, *, client_slug: str | None) -> str | None:
    if not normalized_message:
        return None
    truth = load_yaml_truth(client_slug)
    catalog = _load_master_catalog(truth if isinstance(truth, dict) else {})
    for profile in _extract_master_profiles(catalog):
        name = _normalize_optional_text(profile.get("name"))
        if not name:
            continue
        name_token = _normalize_text(name)
        if name_token and name_token in normalized_message:
            return name
    return None


def _is_question_like_master_query(
    message_text: str | None,
    *,
    client_slug: str | None,
) -> bool:
    if not isinstance(message_text, str) or not message_text.strip():
        return False
    if "?" in message_text:
        return True
    return bool(semantic_question_type(message_text, client_slug=client_slug))


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

    resolved_service_query, service_query_source = _resolve_master_service_query(
        message_text=message_text,
        client_slug=client_slug,
        service_query=service_query,
        intent_decomp=intent_decomp,
    )
    person_service_relation = _has_master_person_service_relation(
        normalized_message,
        client_slug=client_slug,
        person_hit=person_hit,
    )
    master_name_hit = _first_master_name_hit(normalized_message, client_slug=client_slug)
    question_like = _is_question_like_master_query(
        message_text,
        client_slug=client_slug,
    )

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
    if master_name_hit:
        matched_signals.append(master_name_hit)

    if not explicit:
        if direct_hit:
            explicit = True
            reason = "direct_signal"
        elif person_hit and (action_hit or experience_hit):
            explicit = True
            reason = "person_action_signal"
        elif person_hit and master_name_hit and question_like and resolved_service_query:
            explicit = True
            reason = "person_named_question_signal"
        elif person_service_relation and resolved_service_query:
            explicit = True
            reason = "person_service_signal"

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


def _normalize_retrieval_meta(meta: Any) -> dict[str, Any] | None:
    if not isinstance(meta, dict):
        return None
    filters = meta.get("filters") if isinstance(meta.get("filters"), dict) else {}
    scope = meta.get("scope") if isinstance(meta.get("scope"), dict) else {}
    backend = meta.get("backend") if isinstance(meta.get("backend"), dict) else {}
    suggestions = _coerce_text_list(meta.get("suggestions"))
    raw_candidate_count = meta.get("candidate_count")
    try:
        candidate_count = int(raw_candidate_count or 0)
    except (TypeError, ValueError):
        candidate_count = 0
    raw_backend_candidate_count = meta.get("backend_candidate_count")
    try:
        backend_candidate_count = int(raw_backend_candidate_count or 0)
    except (TypeError, ValueError):
        backend_candidate_count = 0
    return {
        "engine": _coerce_text_token(meta.get("engine")),
        "engine_version": _coerce_text_token(meta.get("engine_version")),
        "method": _coerce_text_token(meta.get("method")),
        "candidate_count": candidate_count,
        "best_candidate": _coerce_text_token(meta.get("best_candidate")),
        "best_score": _coerce_confidence(meta.get("best_score")) or 0.0,
        "best_sparse_score": _coerce_confidence(meta.get("best_sparse_score")) or 0.0,
        "best_dense_score": _coerce_confidence(meta.get("best_dense_score")) or 0.0,
        "best_rerank_bonus": _coerce_confidence(meta.get("best_rerank_bonus")) or 0.0,
        "retrieval_mode": _coerce_text_token(meta.get("retrieval_mode")),
        "selected_source": _coerce_text_token(meta.get("selected_source")),
        "fallback_reason": _coerce_text_token(meta.get("fallback_reason")),
        "backend_candidate_count": max(backend_candidate_count, 0),
        "suggestions": suggestions,
        "filters": {
            "tenant_slug": _coerce_text_token(filters.get("tenant_slug")),
            "branch_id": _coerce_text_token(filters.get("branch_id")),
        },
        "scope": {
            "branch_filter_active": bool(scope.get("branch_filter_active")),
            "branch_scoped_items_seen": bool(scope.get("branch_scoped_items_seen")),
            "filtered_out_by_branch": bool(scope.get("filtered_out_by_branch")),
            "filtered_out_by_tenant": bool(scope.get("filtered_out_by_tenant")),
        },
        "backend": {
            "mode": _coerce_text_token(backend.get("mode")),
            "driver": _coerce_text_token(backend.get("driver")),
            "engine": _coerce_text_token(backend.get("engine")),
            "engine_version": _coerce_text_token(backend.get("engine_version")),
            "method": _coerce_text_token(backend.get("method")),
            "available": bool(backend.get("available")),
            "unavailable_reason": _coerce_text_token(backend.get("unavailable_reason")),
        },
    }


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
    retrieval_meta = _normalize_retrieval_meta(payload.get("retrieval_meta"))
    if retrieval_meta:
        resolver_contract["retrieval"] = retrieval_meta
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
    if retrieval_meta:
        payload["retrieval_meta"] = retrieval_meta
    payload["fact_bundle"] = fact_bundle
    payload["provenance"] = {
        "pack_id": fact_bundle["pack_id"],
        "entity_id": fact_bundle["entity_id"],
        "source_ref": fact_bundle["source_ref"],
        "confidence": fact_bundle["confidence"],
    }
    return payload


def build_capability_question_contract(
    *,
    subject_kind: str | None,
    capability: str | None,
    temporal_scope: str | None,
    requested_resolution_mode: str | None = None,
) -> dict[str, Any]:
    subject_token = _normalize_scope_token(subject_kind)
    capability_token = _normalize_scope_token(capability)
    temporal_scope_token = _normalize_scope_token(temporal_scope) or "none"
    requested_mode_token = _normalize_scope_token(requested_resolution_mode)
    referent_key = _SEMANTIC_SUBJECT_REFERENT_KEY.get(subject_token)
    contract: dict[str, Any] = {
        "subject_kind": subject_token,
        "capability": capability_token,
        "temporal_scope": temporal_scope_token,
        "requested_resolution_mode": requested_mode_token,
        "contract_resolution_mode": requested_mode_token or "direct",
        "tool_action": None,
        "info_refs": [],
        "referent_key": referent_key,
        "prefers_referent": bool(referent_key and requested_mode_token == "referent_followup"),
        "requires_referent": False,
        "requires_temporal_scope": False,
    }
    if not capability_token:
        return contract

    info_refs = _CAPABILITY_INFO_REF_MAP.get(capability_token)
    if info_refs:
        contract["contract_resolution_mode"] = "policy_fact"
        contract["tool_action"] = "info"
        contract["info_refs"] = list(info_refs)
        contract["requires_referent"] = bool(
            capability_token in {"pricing", "duration"} and subject_token == "service"
        )
        return contract

    if capability_token == "consultation":
        contract["contract_resolution_mode"] = "policy_fact"
        contract["tool_action"] = "consult"
        return contract

    if capability_token == "portfolio":
        contract["contract_resolution_mode"] = "policy_fact"
        contract["tool_action"] = "catalog.portfolio"
        contract["requires_referent"] = bool(subject_token == "service")
        return contract

    if capability_token in {"bookability", "live_availability"}:
        contract["contract_resolution_mode"] = "live_calendar"
        contract["tool_action"] = "calendar.list_slots"
        contract["requires_referent"] = bool(subject_token == "service")
        contract["requires_temporal_scope"] = temporal_scope_token == "none"
        return contract

    if capability_token == "booking_manage":
        if subject_token == "booking":
            contract["contract_resolution_mode"] = "live_calendar"
            contract["tool_action"] = "calendar.get_booking"
            contract["requires_referent"] = True
        else:
            contract["contract_resolution_mode"] = "handoff"
            contract["tool_action"] = "handoff"
        return contract

    return contract


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


def _format_pack_query_presence_reply(service_name: str, template: str) -> str:
    try:
        rendered = template.format(service=service_name)
    except Exception:
        rendered = ""
    if isinstance(rendered, str) and rendered.strip():
        return rendered.strip()
    return _PACK_QUERY_FALLBACK_PRESENCE_REPLY.format(service=service_name)


def _format_pack_query_suggest_reply(suggestions: list[str], template: str) -> str:
    joined = ", ".join(suggestions[:_PACK_QUERY_MAX_SUGGESTIONS])
    try:
        rendered = template.format(suggestions=joined)
    except Exception:
        rendered = ""
    if isinstance(rendered, str) and rendered.strip():
        return rendered.strip()
    if joined:
        return _PACK_QUERY_FALLBACK_NOT_FOUND_REPLY.format(suggestions=joined)
    return _PACK_QUERY_FALLBACK_NOT_FOUND_REPLY.format(suggestions="n/a")


def _is_strict_scope_block(meta: dict[str, Any]) -> bool:
    scope = meta.get("scope") if isinstance(meta.get("scope"), dict) else {}
    branch_filter_active = bool(scope.get("branch_filter_active"))
    branch_scoped_items_seen = bool(scope.get("branch_scoped_items_seen"))
    filtered_out_by_branch = bool(scope.get("filtered_out_by_branch"))
    filtered_out_by_tenant = bool(scope.get("filtered_out_by_tenant"))
    if branch_filter_active and branch_scoped_items_seen and filtered_out_by_branch:
        return True
    return filtered_out_by_tenant


def semantic_service_match(
    text: str,
    client_slug: str | None,
    *,
    branch_id: str | None = None,
) -> PackQuerySemanticMatch | None:
    query = _coerce_text_token(text)
    if not query:
        return None
    normalized_slug = _coerce_text_token(client_slug) or "generic"
    candidates, engine_meta = _build_pack_query_candidates(
        query,
        client_slug=normalized_slug,
        branch_id=branch_id,
    )
    retrieval_meta = _build_pack_query_retrieval_meta(candidates, engine_meta=engine_meta)
    strict_scope_block = _is_strict_scope_block(engine_meta)
    templates = engine_meta.get("templates") if isinstance(engine_meta.get("templates"), dict) else {}
    presence_template = _coerce_text_token(templates.get("presence_reply")) or _PACK_QUERY_FALLBACK_PRESENCE_REPLY
    not_found_template = _coerce_text_token(templates.get("not_found_reply")) or _PACK_QUERY_FALLBACK_NOT_FOUND_REPLY

    if candidates:
        best = candidates[0]
        suggestions = [candidate.canonical_name for candidate in candidates[:_PACK_QUERY_MAX_SUGGESTIONS]]
        if best.final_score >= _PACK_QUERY_MATCH_MIN_SCORE:
            response = _format_pack_query_presence_reply(best.canonical_name, presence_template)
            return PackQuerySemanticMatch(
                action="match",
                response=response,
                score=best.final_score,
                canonical_name=best.canonical_name,
                suggestions=suggestions,
                meta=retrieval_meta,
            )
        if best.final_score >= _PACK_QUERY_SUGGEST_MIN_SCORE and suggestions:
            response = _format_pack_query_suggest_reply(suggestions, not_found_template)
            return PackQuerySemanticMatch(
                action="suggest",
                response=response,
                score=best.final_score,
                canonical_name=best.canonical_name,
                suggestions=suggestions,
                meta=retrieval_meta,
            )

    if strict_scope_block:
        return None

    fallback_match = _to_runtime_semantic_match(
        _runtime_semantic_service_match(query, normalized_slug),
        meta=retrieval_meta,
    )
    if not fallback_match:
        return None
    dense_signal = engine_meta.get("dense_signal") if isinstance(engine_meta.get("dense_signal"), dict) else {}
    dense_name = _coerce_text_token(dense_signal.get("canonical_name"))
    if dense_name and fallback_match.canonical_name:
        if _normalize_text(fallback_match.canonical_name) != _normalize_text(dense_name):
            return None
    return fallback_match


def get_pack_service_hint(
    message: str,
    *,
    client_slug: str | None = None,
    branch_id: str | None = None,
) -> str | None:
    query = _coerce_text_token(message)
    if not query:
        return None
    normalized_slug = _coerce_text_token(client_slug) or "generic"
    candidates, engine_meta = _build_pack_query_candidates(
        query,
        client_slug=normalized_slug,
        branch_id=branch_id,
    )
    if candidates and candidates[0].final_score >= _PACK_QUERY_HINT_MIN_SCORE:
        return candidates[0].canonical_name
    if _is_strict_scope_block(engine_meta):
        return None
    return _runtime_get_pack_service_hint(query, client_slug=normalized_slug)


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
    if isinstance(decision, PackDecision):
        meta = dict(decision.meta) if isinstance(decision.meta, dict) else {}
        candidates, engine_meta = _build_pack_query_candidates(
            message,
            client_slug=client_slug,
        )
        if candidates:
            best = candidates[0]
            meta.setdefault("service_query", best.canonical_name)
            meta.setdefault("service_query_source", "pack_query_engine_v2")
            meta["service_query_score"] = round(float(best.final_score), 4)
        retrieval_meta = _build_pack_query_retrieval_meta(candidates, engine_meta=engine_meta)
        if retrieval_meta:
            meta["retrieval_meta"] = retrieval_meta
        decision = PackDecision(
            action=decision.action,
            response=decision.response,
            intent=decision.intent,
            collect=decision.collect,
            meta=meta,
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
    "build_capability_question_contract",
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
