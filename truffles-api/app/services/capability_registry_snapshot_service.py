from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.services.capabilities_runtime import get_runtime_capabilities


class FactScopePolicySnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "fact_scope_policy_snapshot.v1"
    source: str = "default"
    allowed_scopes: tuple[str, ...] = Field(default_factory=tuple)


class HandoffPolicySnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "handoff_policy_snapshot.v1"
    source: str = "default"
    policy: str = "allow"


class ToolProtocolPolicySnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "tool_protocol_policy_snapshot.v1"
    source: str = "default"
    allow_tokens: tuple[str, ...] = Field(default_factory=tuple)
    deny_tokens: tuple[str, ...] = Field(default_factory=tuple)
    enforcement_enabled: bool = True
    deny_by_default: bool = False
    has_runtime_records: bool = False
    has_tool_policy_records: bool = False


class CapabilityRegistrySnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "capability_registry_snapshot.v1"
    registry_version: str = "v1"
    source: str = "default"
    fact_scope_policy: FactScopePolicySnapshotV1 = Field(
        default_factory=FactScopePolicySnapshotV1
    )
    handoff_policy: HandoffPolicySnapshotV1 = Field(
        default_factory=HandoffPolicySnapshotV1
    )
    tool_protocol_policy: ToolProtocolPolicySnapshotV1 = Field(
        default_factory=ToolProtocolPolicySnapshotV1
    )


class FactScopeDecisionSnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "fact_scope_decision_snapshot.v1"
    allowed: bool
    reason: str | None
    source: str
    requested_scope: str | None
    allowed_scopes: tuple[str, ...] = Field(default_factory=tuple)


class HandoffDecisionSnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "handoff_decision_snapshot.v1"
    allowed: bool
    reason: str | None
    source: str
    policy: str
    explicit_manager_request: bool


class ToolProtocolDecisionSnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "tool_protocol_decision_snapshot.v1"
    allowed: bool
    reason: str | None
    source: str
    allow_tokens: tuple[str, ...] = Field(default_factory=tuple)
    deny_tokens: tuple[str, ...] = Field(default_factory=tuple)
    enforcement_enabled: bool
    deny_by_default: bool


def _is_env_enabled(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def _normalize_tool_policy_tokens(raw_tokens: Any) -> tuple[str, ...]:
    if not isinstance(raw_tokens, list):
        return ()
    normalized: list[str] = []
    seen: set[str] = set()
    for token in raw_tokens:
        text = str(token or "").strip().casefold()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return tuple(normalized)


def _tool_policy_token_matches(*, token: str, tool_action: str) -> bool:
    if token == "*":
        return True
    if token.endswith(".*"):
        return tool_action.startswith(token[:-1])
    return token == tool_action


def _normalize_fact_scope_token(token: str | None, *, default_prefix: str) -> str | None:
    normalized = str(token or "").strip().casefold()
    if not normalized:
        return None
    if normalized == "*":
        return f"{default_prefix}.*"
    scope_head, dot, scope_tail = normalized.partition(".")
    if dot and scope_head in {"info", "consult"} and scope_tail:
        return normalized
    return f"{default_prefix}.{normalized}"


def _normalize_pack_refs(pack_refs: list[str] | None) -> tuple[str, ...]:
    if not isinstance(pack_refs, list):
        return ()
    normalized: list[str] = []
    seen: set[str] = set()
    for ref in pack_refs:
        value = str(ref or "").strip()
        if not value:
            continue
        normalized_ref = value.casefold()
        if normalized_ref in seen:
            continue
        seen.add(normalized_ref)
        normalized.append(normalized_ref)
    return tuple(normalized)


def _resolve_runtime_payload() -> tuple[object | None, str, bool, bool]:
    runtime = get_runtime_capabilities()
    if runtime is None:
        return None, "default", False, False
    source = str(getattr(runtime, "source", "") or "runtime")
    has_records = bool(getattr(runtime, "has_records", False))
    has_tool_policy_records = bool(getattr(runtime, "has_tool_policy_records", False))
    return runtime.payload, source, has_records, has_tool_policy_records


def build_capability_registry_snapshot() -> CapabilityRegistrySnapshotV1:
    payload, source, has_records, has_tool_policy_records = _resolve_runtime_payload()

    raw_scopes = getattr(payload, "allowed_fact_scopes", None) if payload is not None else None
    raw_policy = getattr(payload, "handoff_policy", None) if payload is not None else None
    tools_config = getattr(payload, "tools", None) if payload is not None else None

    allowed_scopes = _normalize_tool_policy_tokens(raw_scopes)
    handoff_policy = str(raw_policy or "").strip().casefold() or "allow"
    if handoff_policy not in {"allow", "manager_request_only", "deny"}:
        handoff_policy = "allow"

    allow_tokens = _normalize_tool_policy_tokens(getattr(tools_config, "allow", None))
    deny_tokens = _normalize_tool_policy_tokens(getattr(tools_config, "deny", None))
    if not has_tool_policy_records and has_records and (allow_tokens or deny_tokens):
        # Backward-compatible guard for legacy runtime objects built without the
        # `has_tool_policy_records` flag.
        has_tool_policy_records = True

    enforcement_enabled = _is_env_enabled(
        os.environ.get("TOOL_POLICY_ENFORCEMENT"), default=True
    )
    deny_by_default_env = os.environ.get("TOOL_PROTOCOL_DENY_BY_DEFAULT")
    if deny_by_default_env is None:
        # Fail closed only when tenant explicitly owns tool policy records.
        # Non-tool capability records (channels/providers/features) should not
        # silently block FACT/tools by default.
        deny_by_default = has_tool_policy_records
    else:
        deny_by_default = _is_env_enabled(deny_by_default_env, default=False)

    return CapabilityRegistrySnapshotV1(
        source=source,
        fact_scope_policy=FactScopePolicySnapshotV1(
            source=source,
            allowed_scopes=allowed_scopes,
        ),
        handoff_policy=HandoffPolicySnapshotV1(
            source=source,
            policy=handoff_policy,
        ),
        tool_protocol_policy=ToolProtocolPolicySnapshotV1(
            source=source,
            allow_tokens=allow_tokens,
            deny_tokens=deny_tokens,
            enforcement_enabled=enforcement_enabled,
            deny_by_default=deny_by_default,
            has_runtime_records=has_records,
            has_tool_policy_records=has_tool_policy_records,
        ),
    )


def build_requested_fact_scopes(
    *,
    tool_action: str | None,
    pack_refs: list[str] | None,
) -> list[str]:
    if tool_action == "info":
        prefix = "info"
    elif tool_action == "consult":
        prefix = "consult"
    else:
        return []
    scopes: list[str] = []
    for ref in _normalize_pack_refs(pack_refs):
        scope = _normalize_fact_scope_token(ref, default_prefix=prefix)
        if scope and scope not in scopes:
            scopes.append(scope)
    if scopes:
        return scopes
    return [f"{prefix}.*"]


def resolve_fact_scope_snapshot(scope_token: str | None) -> FactScopeDecisionSnapshotV1:
    snapshot = build_capability_registry_snapshot()
    requested_scope = str(scope_token or "").strip().casefold()
    allowed_scopes = snapshot.fact_scope_policy.allowed_scopes
    if not requested_scope:
        return FactScopeDecisionSnapshotV1(
            allowed=False,
            reason="scope_missing",
            source=snapshot.fact_scope_policy.source,
            requested_scope=None,
            allowed_scopes=allowed_scopes,
        )
    if not allowed_scopes:
        return FactScopeDecisionSnapshotV1(
            allowed=True,
            reason=None,
            source=snapshot.fact_scope_policy.source,
            requested_scope=requested_scope,
            allowed_scopes=allowed_scopes,
        )
    for token in allowed_scopes:
        if _tool_policy_token_matches(token=token, tool_action=requested_scope):
            return FactScopeDecisionSnapshotV1(
                allowed=True,
                reason=None,
                source=snapshot.fact_scope_policy.source,
                requested_scope=requested_scope,
                allowed_scopes=allowed_scopes,
            )
    return FactScopeDecisionSnapshotV1(
        allowed=False,
        reason="fact_scope_not_allowed",
        source=snapshot.fact_scope_policy.source,
        requested_scope=requested_scope,
        allowed_scopes=allowed_scopes,
    )


def resolve_handoff_policy_snapshot(*, explicit_manager_request: bool) -> HandoffDecisionSnapshotV1:
    snapshot = build_capability_registry_snapshot()
    policy = snapshot.handoff_policy.policy
    if policy == "allow":
        return HandoffDecisionSnapshotV1(
            allowed=True,
            reason=None,
            source=snapshot.handoff_policy.source,
            policy=policy,
            explicit_manager_request=bool(explicit_manager_request),
        )
    if policy == "manager_request_only":
        allowed = bool(explicit_manager_request)
        return HandoffDecisionSnapshotV1(
            allowed=allowed,
            reason=None if allowed else "manager_request_required",
            source=snapshot.handoff_policy.source,
            policy=policy,
            explicit_manager_request=bool(explicit_manager_request),
        )
    return HandoffDecisionSnapshotV1(
        allowed=False,
        reason="handoff_denied_by_policy",
        source=snapshot.handoff_policy.source,
        policy=policy,
        explicit_manager_request=bool(explicit_manager_request),
    )


def resolve_tool_protocol_snapshot(tool_action: str) -> ToolProtocolDecisionSnapshotV1:
    snapshot = build_capability_registry_snapshot()
    policy = snapshot.tool_protocol_policy
    normalized_action = str(tool_action or "").strip().casefold()
    if not policy.enforcement_enabled:
        return ToolProtocolDecisionSnapshotV1(
            allowed=True,
            reason=None,
            source=policy.source,
            allow_tokens=policy.allow_tokens,
            deny_tokens=policy.deny_tokens,
            enforcement_enabled=False,
            deny_by_default=policy.deny_by_default,
        )

    for token in policy.deny_tokens:
        if _tool_policy_token_matches(token=token, tool_action=normalized_action):
            return ToolProtocolDecisionSnapshotV1(
                allowed=False,
                reason=f"deny:{token}",
                source=policy.source,
                allow_tokens=policy.allow_tokens,
                deny_tokens=policy.deny_tokens,
                enforcement_enabled=True,
                deny_by_default=policy.deny_by_default,
            )

    if policy.allow_tokens:
        for token in policy.allow_tokens:
            if _tool_policy_token_matches(token=token, tool_action=normalized_action):
                return ToolProtocolDecisionSnapshotV1(
                    allowed=True,
                    reason=None,
                    source=policy.source,
                    allow_tokens=policy.allow_tokens,
                    deny_tokens=policy.deny_tokens,
                    enforcement_enabled=True,
                    deny_by_default=policy.deny_by_default,
                )
        return ToolProtocolDecisionSnapshotV1(
            allowed=False,
            reason="allowlist_miss",
            source=policy.source,
            allow_tokens=policy.allow_tokens,
            deny_tokens=policy.deny_tokens,
            enforcement_enabled=True,
            deny_by_default=policy.deny_by_default,
        )

    if policy.deny_by_default:
        return ToolProtocolDecisionSnapshotV1(
            allowed=False,
            reason="deny_by_default",
            source=policy.source,
            allow_tokens=policy.allow_tokens,
            deny_tokens=policy.deny_tokens,
            enforcement_enabled=True,
            deny_by_default=policy.deny_by_default,
        )

    return ToolProtocolDecisionSnapshotV1(
        allowed=True,
        reason=None,
        source=policy.source,
        allow_tokens=policy.allow_tokens,
        deny_tokens=policy.deny_tokens,
        enforcement_enabled=True,
        deny_by_default=policy.deny_by_default,
    )


__all__ = [
    "CapabilityRegistrySnapshotV1",
    "FactScopeDecisionSnapshotV1",
    "FactScopePolicySnapshotV1",
    "HandoffDecisionSnapshotV1",
    "HandoffPolicySnapshotV1",
    "ToolProtocolDecisionSnapshotV1",
    "ToolProtocolPolicySnapshotV1",
    "build_capability_registry_snapshot",
    "build_requested_fact_scopes",
    "resolve_fact_scope_snapshot",
    "resolve_handoff_policy_snapshot",
    "resolve_tool_protocol_snapshot",
]
