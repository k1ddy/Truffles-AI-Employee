from __future__ import annotations

from dataclasses import dataclass

from app.services.capability_registry_snapshot_service import (
    build_requested_fact_scopes as build_requested_fact_scopes_from_snapshot,
)
from app.services.capability_registry_snapshot_service import (
    resolve_fact_scope_snapshot,
    resolve_handoff_policy_snapshot,
    resolve_tool_protocol_snapshot,
)


@dataclass(frozen=True)
class ToolProtocolDecision:
    allowed: bool
    reason: str | None
    source: str
    allow_tokens: list[str]
    deny_tokens: list[str]
    enforcement_enabled: bool
    deny_by_default: bool


@dataclass(frozen=True)
class FactScopeDecision:
    allowed: bool
    reason: str | None
    source: str
    requested_scope: str | None
    allowed_scopes: list[str]


@dataclass(frozen=True)
class HandoffPolicyDecision:
    allowed: bool
    reason: str | None
    source: str
    policy: str
    explicit_manager_request: bool


def resolve_fact_scope_decision(scope_token: str | None) -> FactScopeDecision:
    snapshot = resolve_fact_scope_snapshot(scope_token)
    return FactScopeDecision(
        allowed=snapshot.allowed,
        reason=snapshot.reason,
        source=snapshot.source,
        requested_scope=snapshot.requested_scope,
        allowed_scopes=list(snapshot.allowed_scopes),
    )


def build_requested_fact_scopes(
    *,
    tool_action: str | None,
    pack_refs: list[str] | None,
) -> list[str]:
    return build_requested_fact_scopes_from_snapshot(
        tool_action=tool_action,
        pack_refs=pack_refs,
    )


def resolve_handoff_policy_decision(*, explicit_manager_request: bool) -> HandoffPolicyDecision:
    snapshot = resolve_handoff_policy_snapshot(
        explicit_manager_request=explicit_manager_request
    )
    return HandoffPolicyDecision(
        allowed=snapshot.allowed,
        reason=snapshot.reason,
        source=snapshot.source,
        policy=snapshot.policy,
        explicit_manager_request=snapshot.explicit_manager_request,
    )


def resolve_tool_protocol_decision(tool_action: str) -> ToolProtocolDecision:
    snapshot = resolve_tool_protocol_snapshot(tool_action)
    return ToolProtocolDecision(
        allowed=snapshot.allowed,
        reason=snapshot.reason,
        source=snapshot.source,
        allow_tokens=list(snapshot.allow_tokens),
        deny_tokens=list(snapshot.deny_tokens),
        enforcement_enabled=snapshot.enforcement_enabled,
        deny_by_default=snapshot.deny_by_default,
    )


__all__ = [
    "FactScopeDecision",
    "HandoffPolicyDecision",
    "ToolProtocolDecision",
    "build_requested_fact_scopes",
    "resolve_fact_scope_decision",
    "resolve_handoff_policy_decision",
    "resolve_tool_protocol_decision",
]
