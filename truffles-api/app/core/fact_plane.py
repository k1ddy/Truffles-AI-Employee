from __future__ import annotations

from functools import lru_cache
from typing import Any, Iterable, Literal, Mapping
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.binding_plan import BindingPlanV1
from app.services.capability_manifest_service import (
    build_requested_fact_scopes,
    resolve_fact_scope_decision,
)

FactScopeVerdict = Literal["ok", "empty", "out_of_scope"]
FactCompositionMode = Literal["single_only", "companion_allowed", "bundle_required"]


class FactManifestEntryV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    canonical_ref: str
    scope_namespace: str
    aliases: list[str] = Field(default_factory=list)
    resolver_id: str
    renderer_id: str
    provenance_sources: list[str] = Field(default_factory=list)
    companion_group_id: str | None = None


class FactCompanionGroupV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    group_id: str
    members: list[str] = Field(default_factory=list)
    requested_ref_policies: dict[str, list[str]] = Field(default_factory=dict)
    composition_mode: FactCompositionMode = "companion_allowed"
    renderer_id: str
    provenance_sources: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_requested_ref_policies(self) -> FactCompanionGroupV1:
        allowed_members = set(self.members)
        for requested_ref, emitted_set in self.requested_ref_policies.items():
            if requested_ref not in allowed_members:
                raise ValueError("fact_companion_group_requested_ref_not_in_members")
            if any(item not in allowed_members for item in emitted_set):
                raise ValueError("fact_companion_group_emitted_set_not_in_members")
        return self

    def emitted_set_for_requested_refs(self, requested_refs: list[str]) -> list[str] | None:
        emitted: list[str] = []
        for item in requested_refs:
            rule = self.requested_ref_policies.get(item)
            if not rule:
                return None
            for ref in rule:
                normalized = _normalize_token(ref)
                if normalized and normalized not in emitted:
                    emitted.append(normalized)
        return emitted or None


class FactManifestV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "fact_manifest.v1"
    manifest_id: str = "default_fact_manifest.v1"
    namespace: str = "consultant_core"
    entries: list[FactManifestEntryV1] = Field(default_factory=list)
    companion_groups: list[FactCompanionGroupV1] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_entries(self) -> FactManifestV1:
        canonical_refs: set[str] = set()
        aliases: set[str] = set()
        group_ids = {group.group_id for group in self.companion_groups}
        for entry in self.entries:
            if entry.canonical_ref in canonical_refs:
                raise ValueError("fact_manifest_duplicate_canonical_ref")
            canonical_refs.add(entry.canonical_ref)
            if entry.companion_group_id and entry.companion_group_id not in group_ids:
                raise ValueError("fact_manifest_missing_companion_group")
            for alias in entry.aliases:
                if alias in aliases or alias in canonical_refs:
                    raise ValueError("fact_manifest_duplicate_alias")
                aliases.add(alias)
        return self

    @property
    def entries_by_ref(self) -> dict[str, FactManifestEntryV1]:
        return {entry.canonical_ref: entry for entry in self.entries}

    @property
    def alias_map(self) -> dict[str, str | None]:
        mapping: dict[str, str | None] = {
            "bookability": None,
            "capability": None,
            "check_booking": None,
            "fact": None,
            "fact_unresolved": None,
            "info": None,
            "off_topic": None,
            "other": None,
            "portfolio": None,
            "presence_fallback": None,
        }
        for entry in self.entries:
            mapping[entry.canonical_ref] = entry.canonical_ref
            for alias in entry.aliases:
                mapping[alias] = entry.canonical_ref
        return mapping

    def canonicalize_ref(self, value: str | None) -> str | None:
        token = _normalize_token(value)
        if token is None:
            return None
        return self.alias_map.get(token)

    def entry_for_ref(self, canonical_ref: str | None) -> FactManifestEntryV1 | None:
        token = _normalize_token(canonical_ref)
        if token is None:
            return None
        return self.entries_by_ref.get(token)

    def scope_namespace_for_refs(self, fact_refs: list[str]) -> str | None:
        namespaces = {
            entry.scope_namespace
            for ref in fact_refs
            if (entry := self.entry_for_ref(ref)) is not None
        }
        if not namespaces:
            return None
        if "consult" in namespaces:
            return "consult"
        return "info"

    def default_composition_mode_for_refs(self, fact_refs: list[str]) -> FactCompositionMode:
        if not fact_refs:
            return "single_only"
        if self.companion_group_for_refs(fact_refs) is not None:
            return "companion_allowed"
        return "single_only"

    def companion_group_for_refs(self, fact_refs: list[str]) -> FactCompanionGroupV1 | None:
        requested = {_normalize_token(item) for item in fact_refs}
        requested.discard(None)
        if not requested:
            return None
        candidate_ids = {
            entry.companion_group_id
            for ref in requested
            if (entry := self.entry_for_ref(ref)) is not None and entry.companion_group_id
        }
        if len(candidate_ids) != 1:
            return None
        group_id = next(iter(candidate_ids))
        for group in self.companion_groups:
            if group.group_id == group_id:
                return group
        return None


@lru_cache(maxsize=1)
def build_default_fact_manifest() -> FactManifestV1:
    return FactManifestV1(
        entries=[
            FactManifestEntryV1(
                canonical_ref="pricing",
                scope_namespace="info",
                aliases=["payment", "payment_info", "price_item_fallback", "price_manicure", "price_query", "price_service", "truth_fallback"],
                resolver_id="catalog.service_query",
                renderer_id="catalog.service_query.reply",
                provenance_sources=["service_catalog", "pack_manifest"],
                companion_group_id="service_query_fact_sections",
            ),
            FactManifestEntryV1(
                canonical_ref="promotions",
                scope_namespace="info",
                aliases=["discount", "discounts", "promotion", "promo"],
                resolver_id="catalog.service_query",
                renderer_id="catalog.service_query.reply",
                provenance_sources=["service_catalog", "pack_manifest"],
                companion_group_id="service_query_fact_sections",
            ),
            FactManifestEntryV1(
                canonical_ref="duration",
                scope_namespace="info",
                aliases=["duration_question", "service_duration"],
                resolver_id="catalog.service_query",
                renderer_id="catalog.service_query.reply",
                provenance_sources=["service_catalog", "pack_manifest"],
                companion_group_id="service_query_fact_sections",
            ),
            FactManifestEntryV1(
                canonical_ref="services_overview",
                scope_namespace="info",
                aliases=["service_overview", "services", "services_catalog"],
                resolver_id="catalog.service_query",
                renderer_id="catalog.service_query.reply",
                provenance_sources=["service_catalog", "pack_manifest"],
                companion_group_id="service_query_fact_sections",
            ),
            FactManifestEntryV1(
                canonical_ref="location",
                scope_namespace="info",
                aliases=["address", "location_info"],
                resolver_id="catalog.location",
                renderer_id="catalog.location.reply",
                provenance_sources=["branch_catalog", "pack_manifest"],
                companion_group_id="location_base_bundle",
            ),
            FactManifestEntryV1(
                canonical_ref="hours",
                scope_namespace="info",
                aliases=["hours_info"],
                resolver_id="catalog.location",
                renderer_id="catalog.location.reply",
                provenance_sources=["branch_catalog", "pack_manifest"],
                companion_group_id="location_base_bundle",
            ),
            FactManifestEntryV1(
                canonical_ref="parking",
                scope_namespace="info",
                aliases=["parking_info"],
                resolver_id="catalog.location",
                renderer_id="catalog.location.reply",
                provenance_sources=["branch_catalog", "pack_manifest"],
                companion_group_id="location_base_bundle",
            ),
            FactManifestEntryV1(
                canonical_ref="contact",
                scope_namespace="info",
                aliases=["contact_info"],
                resolver_id="catalog.location",
                renderer_id="catalog.location.reply",
                provenance_sources=["branch_catalog", "pack_manifest"],
            ),
            FactManifestEntryV1(
                canonical_ref="master",
                scope_namespace="consult",
                aliases=["master_query", "masters", "specialists"],
                resolver_id="consult.master",
                renderer_id="consult.master.reply",
                provenance_sources=["pack_runtime", "catalog"],
            ),
            FactManifestEntryV1(
                canonical_ref="specialist",
                scope_namespace="consult",
                aliases=[],
                resolver_id="consult.master",
                renderer_id="consult.master.reply",
                provenance_sources=["pack_runtime", "catalog"],
            ),
            FactManifestEntryV1(
                canonical_ref="guest_policy",
                scope_namespace="info",
                aliases=["guest", "guest_rules"],
                resolver_id="catalog.service_query",
                renderer_id="catalog.service_query.reply",
                provenance_sources=["service_catalog", "pack_manifest"],
                companion_group_id="service_query_fact_sections",
            ),
        ],
        companion_groups=[
            FactCompanionGroupV1(
                group_id="service_query_fact_sections",
                members=["pricing", "promotions", "duration", "services_overview", "guest_policy"],
                requested_ref_policies={
                    "pricing": ["pricing"],
                    "promotions": ["promotions"],
                    "duration": ["duration"],
                    "services_overview": ["services_overview"],
                    "guest_policy": ["guest_policy"],
                },
                composition_mode="companion_allowed",
                renderer_id="catalog.service_query.reply",
                provenance_sources=["service_catalog", "pack_manifest"],
            ),
            FactCompanionGroupV1(
                group_id="location_base_bundle",
                members=["location", "hours", "parking"],
                requested_ref_policies={
                    "location": ["location"],
                    "hours": ["hours"],
                    "parking": ["parking"],
                },
                composition_mode="companion_allowed",
                renderer_id="catalog.location.reply",
                provenance_sources=["branch_catalog", "pack_manifest"],
            )
        ],
    )


def _normalize_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().casefold()
    return cleaned or None


def _dedupe_tokens(values: Iterable[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for item in values:
        token = _normalize_token(item)
        if token is None or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _normalize_fact_ref(value: Any) -> str | None:
    token = _normalize_token(value)
    if token is None:
        return None
    token = token.removeprefix("info.")
    token = token.removeprefix("consult.")
    token = token.removeprefix("fact.")
    return build_default_fact_manifest().canonicalize_ref(token)


def normalize_fact_ref_list(value: Any) -> list[str]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return []
    refs: list[str] = []
    for item in value:
        normalized = _normalize_fact_ref(item)
        if normalized is not None:
            refs.append(normalized)
    return _dedupe_tokens(refs)


def _scope_namespace_for_fact_refs(fact_refs: list[str]) -> str | None:
    return build_default_fact_manifest().scope_namespace_for_refs(fact_refs)


def _scopes_from_fact_refs(*, namespace: str | None, fact_refs: list[str]) -> list[str]:
    if namespace not in {"info", "consult"}:
        return []
    return build_requested_fact_scopes(tool_action=namespace, pack_refs=fact_refs)


def _fact_scope_policy_projection(
    *,
    namespace: str | None,
    fact_refs: list[str],
) -> tuple[list[str], list[str], str]:
    if namespace not in {"info", "consult"} or not fact_refs:
        return [], [], "default"
    allowed_refs: list[str] = []
    blocked_scopes: list[str] = []
    policy_source = "default"
    scope_to_ref = dict(zip(_scopes_from_fact_refs(namespace=namespace, fact_refs=fact_refs), fact_refs))
    for scope, fact_ref in scope_to_ref.items():
        decision = resolve_fact_scope_decision(scope)
        policy_source = decision.source
        if decision.allowed:
            allowed_refs.append(fact_ref)
        else:
            blocked_scopes.append(scope)
    return _dedupe_tokens(allowed_refs), _dedupe_tokens(blocked_scopes), policy_source


def collect_requested_fact_refs(decision: Any) -> list[str]:
    coarse_refs: list[str] = []
    pack_refs: list[str] = []
    exact_refs: list[str] = []

    def _remember(target: list[str], value: Any) -> None:
        normalized = _normalize_fact_ref(value)
        if normalized is not None:
            target.append(normalized)

    _remember(coarse_refs, getattr(decision, "intent", None))
    for item in getattr(decision, "capability_refs", ()) or ():
        _remember(coarse_refs, item)
    for item in getattr(decision, "pack_refs", ()) or ():
        _remember(pack_refs, item)
    for item in getattr(decision, "fact_refs", ()) or ():
        _remember(exact_refs, item)

    tool_args = getattr(decision, "tool_args", None)
    if isinstance(tool_args, Mapping):
        _remember(exact_refs, tool_args.get("info_ref"))
        for item in tool_args.get("info_refs") or []:
            _remember(exact_refs, item)

    semantic_decision = getattr(decision, "semantic_decision", None)
    if semantic_decision is not None:
        _remember(coarse_refs, getattr(semantic_decision, "intent", None))
        _remember(coarse_refs, getattr(semantic_decision, "capability_id", None))
        grounding_requirements = getattr(semantic_decision, "grounding_requirements", None)
        if grounding_requirements is not None:
            for item in getattr(grounding_requirements, "pack_refs", ()) or ():
                _remember(pack_refs, item)

    decision_meta = getattr(decision, "meta", None)
    if isinstance(decision_meta, Mapping):
        semantic_contract = decision_meta.get("semantic_contract")
        if isinstance(semantic_contract, Mapping):
            _remember(coarse_refs, semantic_contract.get("capability"))

    manifest = build_default_fact_manifest()
    group_priority: dict[str, int] = {}
    for priority, bucket in enumerate((coarse_refs, pack_refs, exact_refs)):
        for ref in bucket:
            entry = manifest.entry_for_ref(ref)
            group_id = _normalize_token(entry.companion_group_id) if entry is not None else None
            if group_id is None:
                continue
            current = group_priority.get(group_id, -1)
            if priority > current:
                group_priority[group_id] = priority

    requested: list[str] = []
    seen: set[str] = set()
    for priority, bucket in enumerate((coarse_refs, pack_refs, exact_refs)):
        for ref in bucket:
            entry = manifest.entry_for_ref(ref)
            group_id = _normalize_token(entry.companion_group_id) if entry is not None else None
            if group_id is not None and group_priority.get(group_id, priority) != priority:
                continue
            if ref in seen:
                continue
            seen.add(ref)
            requested.append(ref)

    return requested


def _resolve_decision_id(decision: Any) -> str:
    semantic_decision = getattr(decision, "semantic_decision", None)
    semantic_decision_id = _normalize_token(getattr(semantic_decision, "decision_id", None))
    if semantic_decision_id:
        return semantic_decision_id
    binding_plan = getattr(decision, "binding_plan", None)
    binding_plan_decision_id = _normalize_token(getattr(binding_plan, "decision_id", None))
    if binding_plan_decision_id:
        return binding_plan_decision_id
    decision_meta = getattr(decision, "meta", None)
    if isinstance(decision_meta, Mapping):
        meta_decision_id = _normalize_token(decision_meta.get("semantic_decision_id"))
        if meta_decision_id:
            return meta_decision_id
    return uuid4().hex


def _resolve_binding_plan(decision: Any) -> BindingPlanV1 | None:
    binding_plan = getattr(decision, "binding_plan", None)
    if isinstance(binding_plan, BindingPlanV1):
        return binding_plan
    return None


def _resolve_selected_tool_ref(decision: Any) -> str:
    binding_plan = _resolve_binding_plan(decision)
    selected = _normalize_token(getattr(binding_plan, "selected_tool_or_workflow_ref", None))
    if selected:
        return selected
    return _normalize_token(getattr(decision, "tool_action", None)) or "info"


def _allowed_fact_sets_for_request(
    *,
    manifest: FactManifestV1,
    requested_fact_refs: list[str],
    composition_mode: FactCompositionMode,
) -> tuple[list[list[str]], str, str | None, list[str]]:
    requested = list(requested_fact_refs)
    if not requested:
        return [], "requested_only", None, []

    if composition_mode != "single_only":
        group = manifest.companion_group_for_refs(requested)
        if group is not None:
            emitted_set = group.emitted_set_for_requested_refs(requested)
            if emitted_set:
                return [emitted_set], group.group_id, group.renderer_id, list(group.provenance_sources)

    primary_entry = manifest.entry_for_ref(requested[0])
    renderer_id = primary_entry.renderer_id if primary_entry is not None else None
    provenance_sources = list(primary_entry.provenance_sources) if primary_entry is not None else []
    return [requested], "requested_only", renderer_id, provenance_sources


class FactRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "fact_request.v1"
    manifest_id: str = build_default_fact_manifest().manifest_id
    request_id: str = Field(default_factory=lambda: uuid4().hex)
    decision_id: str
    intent: str
    scope_namespace: str | None = None
    requested_fact_refs: list[str] = Field(default_factory=list)
    requested_scopes: list[str] = Field(default_factory=list)
    supporting_pack_refs: list[str] = Field(default_factory=list)
    supporting_capability_refs: list[str] = Field(default_factory=list)
    subject_kind: str | None = None
    subject_scope: str | None = None
    resolution_mode: str | None = None
    composition_mode: FactCompositionMode = "single_only"
    locale_hint: str | None = None
    format_hint: str | None = None
    owner_source: str = "policy_decision"

    @classmethod
    def build_from_policy_decision(cls, decision: Any) -> FactRequestV1:
        manifest = build_default_fact_manifest()
        requested_fact_refs = collect_requested_fact_refs(decision)
        scope_namespace = manifest.scope_namespace_for_refs(requested_fact_refs)
        decision_meta = getattr(decision, "meta", None)
        supporting_pack_refs = _dedupe_tokens(getattr(decision, "pack_refs", ()) or ())
        supporting_capability_refs = _dedupe_tokens(getattr(decision, "capability_refs", ()) or ())
        composition_mode = manifest.default_composition_mode_for_refs(requested_fact_refs)
        return cls(
            decision_id=_resolve_decision_id(decision),
            intent=_normalize_token(getattr(decision, "intent", None)) or "other",
            scope_namespace=scope_namespace,
            requested_fact_refs=requested_fact_refs,
            requested_scopes=_scopes_from_fact_refs(
                namespace=scope_namespace,
                fact_refs=requested_fact_refs,
            ),
            supporting_pack_refs=supporting_pack_refs,
            supporting_capability_refs=supporting_capability_refs,
            subject_kind=_normalize_token(decision_meta.get("subject_kind")) if isinstance(decision_meta, Mapping) else None,
            subject_scope=(
                _normalize_token(decision_meta.get("subject_scope"))
                if isinstance(decision_meta, Mapping)
                else None
            )
            or (
                _normalize_token(decision_meta.get("subject_kind"))
                if isinstance(decision_meta, Mapping)
                else None
            ),
            resolution_mode=_normalize_token(decision_meta.get("resolution_mode")) if isinstance(decision_meta, Mapping) else None,
            composition_mode=composition_mode,
            locale_hint=(
                _normalize_token(decision_meta.get("locale"))
                if isinstance(decision_meta, Mapping)
                else None
            ) or (
                _normalize_token(decision_meta.get("language"))
                if isinstance(decision_meta, Mapping)
                else None
            ),
            format_hint=(
                _normalize_token(decision_meta.get("format_hint"))
                if isinstance(decision_meta, Mapping)
                else None
            ),
            owner_source=_normalize_token(getattr(decision, "source", None)) or "policy_decision",
        )


class FactPlanV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "fact_plan.v1"
    manifest_id: str
    plan_id: str = Field(default_factory=lambda: uuid4().hex)
    request_id: str
    decision_id: str
    binding_id: str | None = None
    selected_tool_or_workflow_ref: str
    selected_resolver: str
    renderer_id: str | None = None
    scope_namespace: str | None = None
    requested_fact_refs: list[str] = Field(default_factory=list)
    requested_scopes: list[str] = Field(default_factory=list)
    composition_mode: FactCompositionMode = "single_only"
    allowed_emitted_sets: list[list[str]] = Field(default_factory=list)
    allowed_emitted_fact_refs: list[str] = Field(default_factory=list)
    allowed_emitted_scopes: list[str] = Field(default_factory=list)
    blocked_scopes: list[str] = Field(default_factory=list)
    bundle_policy: str = "requested_only"
    scope_policy_source: str = "default"
    fallback_policy: str = "deny_out_of_plan"
    provenance_sources: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_scope_consistency(self) -> FactPlanV1:
        if self.scope_namespace is None:
            if self.requested_scopes or self.allowed_emitted_scopes or self.blocked_scopes:
                raise ValueError("fact_plan_scope_namespace_required")
        flattened = _dedupe_tokens(item for emitted_set in self.allowed_emitted_sets for item in emitted_set)
        if flattened != list(self.allowed_emitted_fact_refs):
            raise ValueError("fact_plan_allowed_emitted_refs_must_match_allowed_sets")
        return self

    @property
    def allowed_info_sections(self) -> list[str]:
        return list(self.allowed_emitted_fact_refs)

    @classmethod
    def build_from_request(cls, request: FactRequestV1, *, decision: Any) -> FactPlanV1:
        manifest = build_default_fact_manifest()
        binding_plan = _resolve_binding_plan(decision)
        selected_tool_ref = _resolve_selected_tool_ref(decision)
        requested_fact_refs = list(request.requested_fact_refs)
        requested_scopes = list(request.requested_scopes)
        raw_allowed_sets, bundle_policy, renderer_id, provenance_sources = _allowed_fact_sets_for_request(
            manifest=manifest,
            requested_fact_refs=requested_fact_refs,
            composition_mode=request.composition_mode,
        )
        scope_namespace = request.scope_namespace or manifest.scope_namespace_for_refs(
            _dedupe_tokens(item for emitted_set in raw_allowed_sets for item in emitted_set) or requested_fact_refs
        )
        raw_allowed_refs = _dedupe_tokens(item for emitted_set in raw_allowed_sets for item in emitted_set)
        if scope_namespace in {"info", "consult"}:
            allowed_emitted_fact_refs, blocked_scopes, scope_policy_source = _fact_scope_policy_projection(
                namespace=scope_namespace,
                fact_refs=raw_allowed_refs,
            )
        else:
            allowed_emitted_fact_refs = raw_allowed_refs
            blocked_scopes = []
            scope_policy_source = "default"
        allowed_emitted_sets: list[list[str]] = []
        for emitted_set in raw_allowed_sets:
            normalized = _dedupe_tokens(ref for ref in emitted_set if ref in allowed_emitted_fact_refs)
            if normalized == emitted_set and normalized not in allowed_emitted_sets:
                allowed_emitted_sets.append(normalized)
        return cls(
            manifest_id=request.manifest_id,
            request_id=request.request_id,
            decision_id=request.decision_id,
            binding_id=_normalize_token(getattr(binding_plan, "binding_id", None)),
            selected_tool_or_workflow_ref=selected_tool_ref,
            selected_resolver=selected_tool_ref,
            renderer_id=renderer_id,
            scope_namespace=scope_namespace,
            requested_fact_refs=requested_fact_refs,
            requested_scopes=requested_scopes,
            composition_mode=request.composition_mode,
            allowed_emitted_sets=allowed_emitted_sets,
            allowed_emitted_fact_refs=allowed_emitted_fact_refs,
            allowed_emitted_scopes=_scopes_from_fact_refs(
                namespace=scope_namespace,
                fact_refs=allowed_emitted_fact_refs,
            ),
            blocked_scopes=blocked_scopes,
            bundle_policy=bundle_policy,
            scope_policy_source=scope_policy_source,
            fallback_policy="deny_out_of_plan",
            provenance_sources=provenance_sources,
        )


class FactResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "fact_result.v1"
    result_id: str = Field(default_factory=lambda: uuid4().hex)
    plan_id: str
    decision_id: str
    selected_tool_or_workflow_ref: str
    selected_source: str
    resolution_source: str
    retrieval_mode: str
    renderer_id: str | None = None
    scope_namespace: str | None = None
    emitted_fact_refs: list[str] = Field(default_factory=list)
    emitted_scopes: list[str] = Field(default_factory=list)
    omitted_fact_refs: list[str] = Field(default_factory=list)
    out_of_scope_fact_refs: list[str] = Field(default_factory=list)
    scope_verdict: FactScopeVerdict = "empty"
    response_generated: bool = False
    resolution_reason: str | None = None
    fallback_reason: str | None = None
    provenance: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_scope_verdict(self) -> FactResultV1:
        if self.scope_verdict == "ok" and self.out_of_scope_fact_refs:
            raise ValueError("fact_result_out_of_scope_refs_forbidden_when_ok")
        if self.scope_verdict == "out_of_scope" and not self.out_of_scope_fact_refs:
            raise ValueError("fact_result_out_of_scope_refs_required")
        if self.scope_namespace is None and self.emitted_scopes:
            raise ValueError("fact_result_scope_namespace_required")
        return self

    @classmethod
    def build_from_runtime_payload(
        cls,
        fact_plan: FactPlanV1,
        *,
        resolution_source: str,
        response_text: str | None,
        meta: Mapping[str, Any] | None = None,
        fallback_fact_refs: Iterable[str] | None = None,
        resolution_reason: str | None = None,
    ) -> FactResultV1:
        emitted_fact_refs = normalize_fact_ref_list((meta or {}).get("info_sections") or [])
        if fallback_fact_refs is not None:
            emitted_fact_refs.extend(normalize_fact_ref_list(list(fallback_fact_refs)))
        emitted_fact_refs = _dedupe_tokens(emitted_fact_refs)
        allowed_union = set(fact_plan.allowed_emitted_fact_refs)
        out_of_scope_fact_refs = [
            item for item in emitted_fact_refs if item not in allowed_union
        ]
        allowed_set_tuples = [tuple(item) for item in fact_plan.allowed_emitted_sets if item]
        emitted_tuple = tuple(emitted_fact_refs)
        exact_set_match = not emitted_tuple or emitted_tuple in allowed_set_tuples
        if emitted_tuple and not exact_set_match and not out_of_scope_fact_refs:
            out_of_scope_fact_refs = list(emitted_fact_refs)
        response_generated = isinstance(response_text, str) and bool(response_text.strip())
        scope_verdict: FactScopeVerdict
        if out_of_scope_fact_refs:
            scope_verdict = "out_of_scope"
        elif response_generated and emitted_fact_refs:
            scope_verdict = "ok"
        else:
            scope_verdict = "empty"
        omitted_fact_refs = [item for item in fact_plan.allowed_emitted_fact_refs if item not in emitted_fact_refs]
        return cls(
            plan_id=fact_plan.plan_id,
            decision_id=fact_plan.decision_id,
            selected_tool_or_workflow_ref=fact_plan.selected_tool_or_workflow_ref,
            selected_source=_normalize_token(resolution_source) or "runtime",
            resolution_source=_normalize_token(resolution_source) or "runtime",
            retrieval_mode="resolved" if response_generated else "fallback",
            renderer_id=fact_plan.renderer_id,
            scope_namespace=fact_plan.scope_namespace,
            emitted_fact_refs=emitted_fact_refs,
            emitted_scopes=_scopes_from_fact_refs(
                namespace=fact_plan.scope_namespace,
                fact_refs=emitted_fact_refs,
            ),
            omitted_fact_refs=omitted_fact_refs,
            out_of_scope_fact_refs=out_of_scope_fact_refs,
            scope_verdict=scope_verdict,
            response_generated=response_generated,
            resolution_reason=_normalize_token(resolution_reason),
            fallback_reason=None if response_generated else _normalize_token(resolution_reason),
            provenance=list(fact_plan.provenance_sources),
        )


class FactContractV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "fact_contract.v1"
    manifest_id: str
    request: FactRequestV1
    plan: FactPlanV1
    result: FactResultV1



def build_fact_contract_meta(
    meta: Mapping[str, Any] | None,
    *,
    fact_request: FactRequestV1,
    fact_plan: FactPlanV1,
    fact_result: FactResultV1,
) -> dict[str, Any]:
    payload = dict(meta) if isinstance(meta, Mapping) else {}
    if fact_result.emitted_fact_refs:
        payload["info_sections"] = list(fact_result.emitted_fact_refs)
    else:
        payload.pop("info_sections", None)
    payload["fact_manifest_id"] = fact_plan.manifest_id
    payload["fact_requested_refs"] = list(fact_request.requested_fact_refs)
    payload["fact_allowed_refs"] = list(fact_plan.allowed_emitted_fact_refs)
    payload["fact_allowed_sets"] = [list(item) for item in fact_plan.allowed_emitted_sets]
    payload["fact_emitted_refs"] = list(fact_result.emitted_fact_refs)
    payload["fact_contract"] = FactContractV1(
        manifest_id=fact_plan.manifest_id,
        request=fact_request,
        plan=fact_plan,
        result=fact_result,
    ).model_dump(mode="python")
    return payload


__all__ = [
    "FactCompanionGroupV1",
    "FactCompositionMode",
    "FactContractV1",
    "FactManifestEntryV1",
    "FactManifestV1",
    "FactPlanV1",
    "FactRequestV1",
    "FactResultV1",
    "FactScopeVerdict",
    "build_default_fact_manifest",
    "build_fact_contract_meta",
    "collect_requested_fact_refs",
    "normalize_fact_ref_list",
]
