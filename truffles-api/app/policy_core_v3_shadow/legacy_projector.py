"""Defensive projector from any legacy-decision-like object to LegacySummary.

Spec: SPECS/SHADOW_RUN_V3.md (B.2.a extension).

This helper is for callers in Phase B.2.b that have a real legacy
`IntentResponse` (or equivalent) and want to produce a typed `LegacySummary`
without each call site reinventing the same getattr pattern.

The projector is **defensive**: missing attributes fall back to safe
defaults. It does not import any legacy module. It does not interpret
business meaning. It only normalizes attribute names.
"""
from __future__ import annotations

from typing import Any

from .legacy_summary import LegacySummary


# Attribute search lists per LegacySummary field. The first attribute that
# is present and non-None on the source object wins. The lists are minimal
# and stable; new entries belong in a Decision Ledger entry, not in
# scenario-driven patches.
_INTENT_ATTRS = ("intent", "intent_value", "intent_name")
_ACTION_ATTRS = ("action", "action_kind", "action_name")
_TOOL_ATTRS = ("tool_action", "tool_id", "tool")
_MESSAGE_ATTRS = ("message_text", "message", "reply_text", "text")
_RESCUE_ATTRS = ("rescue", "rescue_flag", "is_rescue")
_DEGRADE_FLAG_ATTRS = ("policy_core_degrade", "is_degraded", "degraded")
_DEGRADE_REASON_ATTRS = (
    "policy_core_degrade_reason",
    "degrade_reason",
    "policy_core_reason_code",
)
_LATENCY_ATTRS = ("latency_ms", "elapsed_ms", "duration_ms")


def _first_attr(obj: Any, names: tuple[str, ...]) -> Any:
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return value
    return None


def _coerce_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    # Enum-like: prefer .value, then .name, then str()
    if hasattr(value, "value") and isinstance(value.value, str):
        return value.value
    if hasattr(value, "name") and isinstance(value.name, str):
        return value.name
    return str(value)


def _coerce_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return _coerce_str(value)


def _coerce_bool(value: Any) -> bool:
    return bool(value) if value is not None else False


def _coerce_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out < 0:
        return None
    return out


def project_legacy_decision(decision: Any, *, extras: dict[str, Any] | None = None) -> LegacySummary:
    """Build a `LegacySummary` from any object with legacy-decision-like attrs.

    Missing or None attributes fall back to safe defaults. `extras` is the
    explicit escape hatch for caller-specific raw fields; the projector
    itself never inspects unknown attributes to populate it.
    """
    intent = _coerce_str(_first_attr(decision, _INTENT_ATTRS), default="unknown")
    action = _coerce_str(_first_attr(decision, _ACTION_ATTRS), default="")
    tool_action = _coerce_optional_str(_first_attr(decision, _TOOL_ATTRS))
    message_text = _coerce_str(_first_attr(decision, _MESSAGE_ATTRS), default="")
    rescue_flag = _coerce_bool(_first_attr(decision, _RESCUE_ATTRS))
    policy_core_degrade = _coerce_bool(_first_attr(decision, _DEGRADE_FLAG_ATTRS))
    degrade_reason = _coerce_optional_str(_first_attr(decision, _DEGRADE_REASON_ATTRS))
    latency_ms = _coerce_optional_float(_first_attr(decision, _LATENCY_ATTRS))

    return LegacySummary(
        intent=intent,
        action=action,
        tool_action=tool_action,
        message_text=message_text,
        rescue_flag=rescue_flag,
        policy_core_degrade=policy_core_degrade,
        degrade_reason=degrade_reason,
        latency_ms=latency_ms,
        extras=dict(extras) if extras else {},
    )
