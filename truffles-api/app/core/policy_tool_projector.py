from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping
from uuid import UUID

from app.core.binding_plan import BindingPlanV1
from app.schemas.intent import validate_tool_args_shape
from app.services.tool_registry_snapshot_service import (
    resolve_policy_info_tool_action,
    resolve_tool_registry_entry,
)


@dataclass(frozen=True)
class PolicyToolProjection:
    tool_action: str
    tool_args: dict[str, Any]
    trace: dict[str, Any]


def _normalize_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().casefold()
    return cleaned or None


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _looks_like_uuid(value: Any) -> bool:
    token = _normalize_text(value)
    if token is None:
        return False
    try:
        UUID(token)
    except (TypeError, ValueError):
        return False
    return True


def _normalize_slots(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, str] = {}
    for key in ("service", "datetime", "name", "phone"):
        text = _normalize_text(value.get(key))
        if text:
            normalized[key] = text
    return normalized


def _normalize_referent_payload(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, str] = {}
    for key in ("value", "entity_id", "entity_type", "source_ref"):
        text = _normalize_text(value.get(key))
        if text:
            normalized[key] = text
    return normalized


def _normalize_referents(value: Any) -> dict[str, dict[str, str]]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, dict[str, str]] = {}
    for key in ("service", "specialist", "branch", "booking_ref", "customer"):
        payload = _normalize_referent_payload(value.get(key))
        if payload:
            normalized[key] = payload
    return normalized


def _sanitize_projected_tool_args(
    *,
    tool_action: str,
    tool_args: dict[str, Any],
) -> dict[str, Any]:
    if not tool_args:
        return {}
    cleaned_args = dict(tool_args)
    while True:
        normalized_args, error = validate_tool_args_shape(
            tool_action=tool_action,
            tool_args=cleaned_args,
        )
        if error is None:
            return normalized_args or {}
        if not error.startswith("tool_args_unknown_field:"):
            return {}
        _, _, field_name = error.partition(":")
        if not field_name or field_name not in cleaned_args:
            return {}
        cleaned_args.pop(field_name, None)


def _iter_policy_info_refs(semantic_decision: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()

    def _remember(value: Any) -> None:
        normalized = _normalize_token(value)
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        refs.append(normalized)

    _remember(semantic_decision.get("intent"))
    _remember(semantic_decision.get("capability_id") or semantic_decision.get("capability"))
    grounding_requirements = (
        semantic_decision.get("grounding_requirements")
        if isinstance(semantic_decision.get("grounding_requirements"), Mapping)
        else {}
    )
    for item in grounding_requirements.get("pack_refs") or semantic_decision.get("pack_refs") or []:
        _remember(item)
    return refs


def _resolve_binding_tool_action(
    *,
    action: str,
    tool_action_hint: str,
    semantic_decision: Mapping[str, Any],
) -> str:
    if action != "fact" or tool_action_hint != "info":
        return tool_action_hint
    for info_ref in _iter_policy_info_refs(semantic_decision):
        projected = resolve_policy_info_tool_action(info_ref)
        if projected:
            return projected
    return tool_action_hint


def _normalize_collect_binding_hint(
    tool_action_hint: str | None,
) -> tuple[str, str | None, str | None]:
    if not tool_action_hint or tool_action_hint == "collect":
        return "collect", None, None
    if tool_action_hint == "handoff":
        return "collect", None, "collect_tool_action_hint_conflict"
    return "collect", tool_action_hint, None


def project_policy_tool_binding(
    *,
    semantic_decision: Mapping[str, Any],
    allowed_tool_actions: Iterable[str],
) -> tuple[PolicyToolProjection | None, str | None]:
    action = _normalize_token(semantic_decision.get("requested_outcome") or semantic_decision.get("action"))
    tool_action_hint = _normalize_token(
        semantic_decision.get("tool_action_hint") or semantic_decision.get("tool_action")
    )
    collect_context_hint: str | None = None
    if action not in {"fact", "collect", "handoff"}:
        return None, "action_invalid"

    if action == "collect":
        (
            resolved_tool_action,
            collect_context_hint,
            collect_hint_error,
        ) = _normalize_collect_binding_hint(tool_action_hint)
        if collect_hint_error is not None:
            return None, collect_hint_error
    elif action == "handoff":
        if tool_action_hint and tool_action_hint != "handoff":
            return None, "handoff_tool_action_hint_conflict"
        resolved_tool_action = "handoff"
    else:
        if not tool_action_hint:
            return None, "tool_action_hint_missing"
        if tool_action_hint in {"collect", "handoff"}:
            return None, f"fact_tool_action_hint_invalid:{tool_action_hint}"
        resolved_tool_action = _resolve_binding_tool_action(
            action=action,
            tool_action_hint=tool_action_hint,
            semantic_decision=semantic_decision,
        )

    allowed = {
        value.strip()
        for value in allowed_tool_actions
        if isinstance(value, str) and value.strip()
    }
    if resolved_tool_action not in allowed:
        return None, f"tool_action_not_allowed:{resolved_tool_action}"
    tool_entry = resolve_tool_registry_entry(resolved_tool_action) if action == "fact" else None
    if action == "fact" and resolved_tool_action != "info" and tool_entry is None:
        return None, f"tool_action_unknown:{resolved_tool_action}"

    slots = _normalize_slots(
        semantic_decision.get("semantic_slots") or semantic_decision.get("slots")
    )
    grounding_requirements = (
        semantic_decision.get("grounding_requirements")
        if isinstance(semantic_decision.get("grounding_requirements"), Mapping)
        else {}
    )
    referents = _normalize_referents(
        grounding_requirements.get("referents") or semantic_decision.get("referents")
    )
    projected_args: dict[str, Any] = {}

    service_payload = referents.get("service") or {}
    projected_service_query = _normalize_text(
        service_payload.get("value") or slots.get("service")
    )
    if projected_service_query and tool_entry and tool_entry.accepts_service_query:
        projected_args["service_query"] = projected_service_query

    specialist_payload = referents.get("specialist") or {}
    projected_specialist_name = _normalize_text(specialist_payload.get("value"))
    if projected_specialist_name and tool_entry and tool_entry.accepts_specialist_name:
        projected_args["specialist_name"] = projected_specialist_name

    projected_specialist_id = _normalize_text(specialist_payload.get("entity_id"))
    if (
        projected_specialist_id
        and tool_entry
        and tool_entry.accepts_specialist_id
        and _looks_like_uuid(projected_specialist_id)
    ):
        projected_args["specialist_id"] = projected_specialist_id

    booking_ref_payload = referents.get("booking_ref") or {}
    projected_booking_ref = _normalize_text(
        booking_ref_payload.get("entity_id") or booking_ref_payload.get("value")
    )
    if (
        projected_booking_ref
        and tool_entry
        and tool_entry.accepts_appointment_id
        and _looks_like_uuid(projected_booking_ref)
    ):
        projected_args["appointment_id"] = projected_booking_ref

    customer_name = _normalize_text(slots.get("name"))
    if customer_name and tool_entry and tool_entry.accepts_customer_name:
        projected_args["customer_name"] = customer_name

    customer_phone = _normalize_text(slots.get("phone"))
    if customer_phone and tool_entry and tool_entry.accepts_customer_phone:
        projected_args["customer_phone"] = customer_phone

    projected_args = _sanitize_projected_tool_args(
        tool_action=resolved_tool_action,
        tool_args=projected_args,
    )

    trace: dict[str, Any] = {
        "status": "ok",
        "projection_source": "policy_tool_projector",
        "tool_action_hint": tool_action_hint,
        "tool_action": resolved_tool_action,
    }
    if action == "collect" and collect_context_hint:
        trace["collect_context_hint"] = collect_context_hint
    if projected_args:
        trace["tool_args"] = dict(projected_args)

    return (
        PolicyToolProjection(
            tool_action=resolved_tool_action,
            tool_args=projected_args,
            trace=trace,
        ),
        None,
    )


def build_binding_plan(
    *,
    semantic_decision: Mapping[str, Any],
    allowed_tool_actions: Iterable[str],
) -> tuple[BindingPlanV1 | None, dict[str, Any] | None, str | None]:
    action = _normalize_token(
        semantic_decision.get("requested_outcome") or semantic_decision.get("action")
    )
    projection, error = project_policy_tool_binding(
        semantic_decision=semantic_decision,
        allowed_tool_actions=allowed_tool_actions,
    )
    if error or projection is None:
        return None, None, error or "binding_projection_invalid"
    decision_id = _normalize_text(semantic_decision.get("decision_id"))
    if not decision_id:
        return None, None, "binding_decision_id_missing"
    capability_id = _normalize_text(
        semantic_decision.get("capability_id") or semantic_decision.get("capability")
    )
    binding_plan = BindingPlanV1.build_compat(
        decision_id=decision_id,
        requested_outcome=action,
        capability_id=capability_id,
        selected_tool_or_workflow_ref=projection.tool_action,
        resolved_args=projection.tool_args,
        handoff_reason_code=_normalize_text(
            semantic_decision.get("handoff_reason_code")
            or semantic_decision.get("degrade_reason_code")
            or semantic_decision.get("decision_summary")
        ),
    )
    return binding_plan, dict(projection.trace), None


__all__ = ["BindingPlanV1", "PolicyToolProjection", "build_binding_plan", "project_policy_tool_binding"]
