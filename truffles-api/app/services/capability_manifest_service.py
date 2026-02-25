from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from app.services.capabilities_runtime import get_runtime_capabilities


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


def _is_env_enabled(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def _normalize_tool_policy_tokens(raw_tokens: Any) -> list[str]:
    if not isinstance(raw_tokens, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for token in raw_tokens:
        text = str(token or "").strip().casefold()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


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


def _normalize_pack_refs(pack_refs: list[str] | None) -> list[str]:
    if not isinstance(pack_refs, list):
        return []
    normalized: list[str] = []
    for ref in pack_refs:
        value = str(ref or "").strip()
        if not value:
            continue
        normalized_ref = value.casefold()
        if normalized_ref in normalized:
            continue
        normalized.append(normalized_ref)
    return normalized


def _resolve_runtime_fact_scopes() -> tuple[list[str], str]:
    runtime = get_runtime_capabilities()
    if runtime is None:
        return [], "default"
    raw_scopes = getattr(runtime.payload, "allowed_fact_scopes", None)
    scopes = _normalize_tool_policy_tokens(raw_scopes)
    source = str(getattr(runtime, "source", "") or "runtime")
    return scopes, source


def _resolve_runtime_handoff_policy() -> tuple[str, str]:
    runtime = get_runtime_capabilities()
    if runtime is None:
        return "allow", "default"
    raw_policy = getattr(runtime.payload, "handoff_policy", None)
    policy = str(raw_policy or "").strip().casefold() or "allow"
    source = str(getattr(runtime, "source", "") or "runtime")
    return policy, source


def _resolve_runtime_tool_policy() -> tuple[list[str], list[str], str, bool]:
    runtime = get_runtime_capabilities()
    if runtime is None:
        return [], [], "default", False
    tools_config = getattr(runtime.payload, "tools", None)
    allow_tokens = _normalize_tool_policy_tokens(getattr(tools_config, "allow", None))
    deny_tokens = _normalize_tool_policy_tokens(getattr(tools_config, "deny", None))
    source = str(getattr(runtime, "source", "") or "runtime")
    has_records = bool(getattr(runtime, "has_records", False))
    return allow_tokens, deny_tokens, source, has_records


def resolve_fact_scope_decision(scope_token: str | None) -> FactScopeDecision:
    requested_scope = str(scope_token or "").strip().casefold()
    allowed_scopes, source = _resolve_runtime_fact_scopes()
    if not requested_scope:
        return FactScopeDecision(
            allowed=False,
            reason="scope_missing",
            source=source,
            requested_scope=None,
            allowed_scopes=allowed_scopes,
        )
    if not allowed_scopes:
        return FactScopeDecision(
            allowed=True,
            reason=None,
            source=source,
            requested_scope=requested_scope,
            allowed_scopes=allowed_scopes,
        )
    for token in allowed_scopes:
        if _tool_policy_token_matches(token=token, tool_action=requested_scope):
            return FactScopeDecision(
                allowed=True,
                reason=None,
                source=source,
                requested_scope=requested_scope,
                allowed_scopes=allowed_scopes,
            )
    return FactScopeDecision(
        allowed=False,
        reason="fact_scope_not_allowed",
        source=source,
        requested_scope=requested_scope,
        allowed_scopes=allowed_scopes,
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


def resolve_handoff_policy_decision(*, explicit_manager_request: bool) -> HandoffPolicyDecision:
    policy, source = _resolve_runtime_handoff_policy()
    policy_token = policy if policy in {"allow", "manager_request_only", "deny"} else "allow"
    if policy_token == "allow":
        return HandoffPolicyDecision(
            allowed=True,
            reason=None,
            source=source,
            policy=policy_token,
            explicit_manager_request=bool(explicit_manager_request),
        )
    if policy_token == "manager_request_only":
        allowed = bool(explicit_manager_request)
        return HandoffPolicyDecision(
            allowed=allowed,
            reason=None if allowed else "manager_request_required",
            source=source,
            policy=policy_token,
            explicit_manager_request=bool(explicit_manager_request),
        )
    return HandoffPolicyDecision(
        allowed=False,
        reason="handoff_denied_by_policy",
        source=source,
        policy=policy_token,
        explicit_manager_request=bool(explicit_manager_request),
    )


def resolve_tool_protocol_decision(tool_action: str) -> ToolProtocolDecision:
    normalized_action = str(tool_action or "").strip().casefold()
    allow_tokens, deny_tokens, source, has_records = _resolve_runtime_tool_policy()
    enforcement_enabled = _is_env_enabled(
        os.environ.get("TOOL_POLICY_ENFORCEMENT"), default=True
    )
    deny_by_default_env = os.environ.get("TOOL_PROTOCOL_DENY_BY_DEFAULT")
    if deny_by_default_env is None:
        # If a tenant already has capability records, fail closed unless policy
        # explicitly allows a tool (allowlist) or denies it with reason.
        deny_by_default = has_records
    else:
        deny_by_default = _is_env_enabled(deny_by_default_env, default=False)

    if not enforcement_enabled:
        return ToolProtocolDecision(
            allowed=True,
            reason=None,
            source=source,
            allow_tokens=allow_tokens,
            deny_tokens=deny_tokens,
            enforcement_enabled=False,
            deny_by_default=deny_by_default,
        )

    for token in deny_tokens:
        if _tool_policy_token_matches(token=token, tool_action=normalized_action):
            return ToolProtocolDecision(
                allowed=False,
                reason=f"deny:{token}",
                source=source,
                allow_tokens=allow_tokens,
                deny_tokens=deny_tokens,
                enforcement_enabled=True,
                deny_by_default=deny_by_default,
            )

    if allow_tokens:
        for token in allow_tokens:
            if _tool_policy_token_matches(token=token, tool_action=normalized_action):
                return ToolProtocolDecision(
                    allowed=True,
                    reason=None,
                    source=source,
                    allow_tokens=allow_tokens,
                    deny_tokens=deny_tokens,
                    enforcement_enabled=True,
                    deny_by_default=deny_by_default,
                )
        return ToolProtocolDecision(
            allowed=False,
            reason="allowlist_miss",
            source=source,
            allow_tokens=allow_tokens,
            deny_tokens=deny_tokens,
            enforcement_enabled=True,
            deny_by_default=deny_by_default,
        )

    if deny_by_default:
        return ToolProtocolDecision(
            allowed=False,
            reason="deny_by_default",
            source=source,
            allow_tokens=allow_tokens,
            deny_tokens=deny_tokens,
            enforcement_enabled=True,
            deny_by_default=deny_by_default,
        )

    return ToolProtocolDecision(
        allowed=True,
        reason=None,
        source=source,
        allow_tokens=allow_tokens,
        deny_tokens=deny_tokens,
        enforcement_enabled=True,
        deny_by_default=deny_by_default,
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
