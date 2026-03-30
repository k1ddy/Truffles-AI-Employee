from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.tool_registry_entry import ToolRegistryEntry
from app.services.tool_registry_snapshot_service import list_declared_tool_actions

TOOL_REGISTRY_SCHEMA_VERSION = "v1"
TOOL_REGISTRY_STATUS_ACTIVE = "active"
TOOL_REGISTRY_STATUS_DISABLED = "disabled"
TOOL_CERTIFICATION_CERTIFIED = "certified"
TOOL_CERTIFICATION_UNCERTIFIED = "uncertified"
TOOL_HEALTH_HEALTHY = "healthy"
TOOL_HEALTH_DEGRADED = "degraded"
TOOL_HEALTH_DOWN = "down"
TOOL_SCOPE_CLIENT = "client"
TOOL_SCOPE_BRANCH = "branch"
TOOL_SCOPE_VALUES = (TOOL_SCOPE_CLIENT, TOOL_SCOPE_BRANCH)
TOOL_REGISTRY_ACTION_RE = r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$"


@dataclass(frozen=True)
class ToolCertificationDecision:
    allowed: bool
    reason: str | None
    source: str
    certification_status: str
    health_status: str
    registry_status: str
    allowed_scopes: tuple[str, ...]


@dataclass(frozen=True)
class _RegistryEntryView:
    tool_action: str
    tool_group: str
    certification_status: str
    health_status: str
    registry_status: str
    allowed_scopes: tuple[str, ...]
    source: str


_DEFAULT_TOOL_ACTIONS: tuple[str, ...] = list_declared_tool_actions()


def _normalize_tool_action(value: str) -> str:
    token = str(value or "").strip().casefold()
    if not token:
        raise ValueError("tool_action required")
    import re

    if not re.match(TOOL_REGISTRY_ACTION_RE, token):
        raise ValueError("tool_action must be '<group>.<action>'")
    return token


def _normalize_tool_scope(value: str) -> str:
    token = str(value or "").strip().casefold()
    if token not in TOOL_SCOPE_VALUES:
        raise ValueError("scope must be client|branch")
    return token


def _normalize_allowed_scopes(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return TOOL_SCOPE_VALUES
    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw:
        token = str(item or "").strip().casefold()
        if token not in TOOL_SCOPE_VALUES:
            continue
        if token in seen:
            continue
        seen.add(token)
        normalized.append(token)
    if not normalized:
        return TOOL_SCOPE_VALUES
    return tuple(normalized)


def _normalize_certification_status(value: Any) -> str:
    token = str(value or "").strip().casefold()
    if token in {TOOL_CERTIFICATION_CERTIFIED, TOOL_CERTIFICATION_UNCERTIFIED}:
        return token
    return TOOL_CERTIFICATION_UNCERTIFIED


def _normalize_health_status(value: Any) -> str:
    token = str(value or "").strip().casefold()
    if token in {TOOL_HEALTH_HEALTHY, TOOL_HEALTH_DEGRADED, TOOL_HEALTH_DOWN}:
        return token
    return TOOL_HEALTH_DOWN


def _normalize_registry_status(value: Any) -> str:
    token = str(value or "").strip().casefold()
    if token in {TOOL_REGISTRY_STATUS_ACTIVE, TOOL_REGISTRY_STATUS_DISABLED}:
        return token
    return TOOL_REGISTRY_STATUS_DISABLED


def _build_default_registry() -> dict[str, _RegistryEntryView]:
    registry: dict[str, _RegistryEntryView] = {}
    for action in _DEFAULT_TOOL_ACTIONS:
        group, _sep, _name = action.partition(".")
        registry[action] = _RegistryEntryView(
            tool_action=action,
            tool_group=group,
            certification_status=TOOL_CERTIFICATION_CERTIFIED,
            health_status=TOOL_HEALTH_HEALTHY,
            registry_status=TOOL_REGISTRY_STATUS_ACTIVE,
            allowed_scopes=TOOL_SCOPE_VALUES,
            source="default",
        )
    return registry


def _load_effective_registry(db: Session) -> dict[str, _RegistryEntryView]:
    registry = _build_default_registry()
    try:
        rows = db.query(ToolRegistryEntry).all()
    except Exception:
        return registry
    if not isinstance(rows, (list, tuple)):
        return registry

    for row in rows:
        try:
            action = _normalize_tool_action(row.tool_action)
            group = str(row.tool_group or "").strip().casefold() or action.partition(".")[0]
            registry[action] = _RegistryEntryView(
                tool_action=action,
                tool_group=group,
                certification_status=_normalize_certification_status(row.certification_status),
                health_status=_normalize_health_status(row.health_status),
                registry_status=_normalize_registry_status(row.status),
                allowed_scopes=_normalize_allowed_scopes(row.allowed_scopes_json),
                source="tool_registry",
            )
        except Exception:
            continue
    return registry


def resolve_tool_certification_decision(
    db: Session,
    *,
    tool_action: str,
    scope: str,
) -> ToolCertificationDecision:
    action = _normalize_tool_action(tool_action)
    normalized_scope = _normalize_tool_scope(scope)
    registry = _load_effective_registry(db)
    entry = registry.get(action)
    if entry is None:
        return ToolCertificationDecision(
            allowed=False,
            reason="registry_missing",
            source="tool_registry",
            certification_status=TOOL_CERTIFICATION_UNCERTIFIED,
            health_status=TOOL_HEALTH_DOWN,
            registry_status=TOOL_REGISTRY_STATUS_DISABLED,
            allowed_scopes=tuple(),
        )
    if entry.registry_status != TOOL_REGISTRY_STATUS_ACTIVE:
        return ToolCertificationDecision(
            allowed=False,
            reason=f"registry:{entry.registry_status}",
            source=entry.source,
            certification_status=entry.certification_status,
            health_status=entry.health_status,
            registry_status=entry.registry_status,
            allowed_scopes=entry.allowed_scopes,
        )
    if normalized_scope not in entry.allowed_scopes:
        return ToolCertificationDecision(
            allowed=False,
            reason=f"scope:{normalized_scope}",
            source=entry.source,
            certification_status=entry.certification_status,
            health_status=entry.health_status,
            registry_status=entry.registry_status,
            allowed_scopes=entry.allowed_scopes,
        )
    if entry.certification_status != TOOL_CERTIFICATION_CERTIFIED:
        return ToolCertificationDecision(
            allowed=False,
            reason=f"certification:{entry.certification_status}",
            source=entry.source,
            certification_status=entry.certification_status,
            health_status=entry.health_status,
            registry_status=entry.registry_status,
            allowed_scopes=entry.allowed_scopes,
        )
    if entry.health_status == TOOL_HEALTH_DOWN:
        return ToolCertificationDecision(
            allowed=False,
            reason=f"health:{entry.health_status}",
            source=entry.source,
            certification_status=entry.certification_status,
            health_status=entry.health_status,
            registry_status=entry.registry_status,
            allowed_scopes=entry.allowed_scopes,
        )
    return ToolCertificationDecision(
        allowed=True,
        reason=None,
        source=entry.source,
        certification_status=entry.certification_status,
        health_status=entry.health_status,
        registry_status=entry.registry_status,
        allowed_scopes=entry.allowed_scopes,
    )


def _token_matches_action(*, token: str, tool_action: str) -> bool:
    if token == "*":
        return True
    if token.endswith(".*"):
        return tool_action.startswith(token[:-1])
    return token == tool_action


def validate_tool_allow_tokens_for_scope(
    db: Session,
    *,
    allow_tokens: list[str] | None,
    scope: str,
) -> tuple[bool, str | None]:
    if not allow_tokens:
        return True, None
    normalized_scope = _normalize_tool_scope(scope)
    registry = _load_effective_registry(db)
    actions = sorted(registry.keys())
    for raw_token in allow_tokens:
        token = str(raw_token or "").strip().casefold()
        if not token:
            continue
        matched = [action for action in actions if _token_matches_action(token=token, tool_action=action)]
        if not matched:
            return (
                False,
                f"tools.allow token '{token}' does not match known tool actions",
            )
        for action in matched:
            decision = resolve_tool_certification_decision(
                db,
                tool_action=action,
                scope=normalized_scope,
            )
            if decision.allowed:
                continue
            return (
                False,
                (
                    f"tools.allow token '{token}' includes blocked action '{action}' "
                    f"({decision.reason})"
                ),
            )
    return True, None


__all__ = [
    "TOOL_CERTIFICATION_CERTIFIED",
    "TOOL_CERTIFICATION_UNCERTIFIED",
    "TOOL_HEALTH_DEGRADED",
    "TOOL_HEALTH_DOWN",
    "TOOL_HEALTH_HEALTHY",
    "TOOL_REGISTRY_SCHEMA_VERSION",
    "TOOL_REGISTRY_STATUS_ACTIVE",
    "TOOL_REGISTRY_STATUS_DISABLED",
    "TOOL_SCOPE_BRANCH",
    "TOOL_SCOPE_CLIENT",
    "TOOL_SCOPE_VALUES",
    "ToolCertificationDecision",
    "resolve_tool_certification_decision",
    "validate_tool_allow_tokens_for_scope",
]
