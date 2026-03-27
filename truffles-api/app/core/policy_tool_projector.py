from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping
from uuid import UUID

from app.schemas.intent import validate_tool_args_shape

_SERVICE_QUERY_TOOL_ACTIONS = {
    "calendar.list_slots",
    "calendar.book_slot",
    "catalog.service_query",
    "catalog.portfolio",
}
_SPECIALIST_TOOL_ACTIONS = {
    "calendar.list_slots",
    "calendar.book_slot",
}
_BOOKING_REF_TOOL_ACTIONS = {
    "calendar.get_booking",
    "calendar.reschedule",
    "calendar.cancel",
}
_BOOKING_CUSTOMER_TOOL_ACTIONS = {
    "calendar.book_slot",
}


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


def project_policy_tool_binding(
    *,
    semantic_decision: Mapping[str, Any],
    allowed_tool_actions: Iterable[str],
) -> tuple[PolicyToolProjection | None, str | None]:
    action = _normalize_token(semantic_decision.get("requested_outcome") or semantic_decision.get("action"))
    tool_action_hint = _normalize_token(
        semantic_decision.get("tool_action_hint") or semantic_decision.get("tool_action")
    )
    if action not in {"fact", "collect", "handoff"}:
        return None, "action_invalid"

    if action == "collect":
        if tool_action_hint and tool_action_hint != "collect":
            return None, "collect_tool_action_hint_conflict"
        resolved_tool_action = "collect"
    elif action == "handoff":
        if tool_action_hint and tool_action_hint != "handoff":
            return None, "handoff_tool_action_hint_conflict"
        resolved_tool_action = "handoff"
    else:
        if not tool_action_hint:
            return None, "tool_action_hint_missing"
        if tool_action_hint in {"collect", "handoff"}:
            return None, f"fact_tool_action_hint_invalid:{tool_action_hint}"
        resolved_tool_action = tool_action_hint

    allowed = {
        value.strip()
        for value in allowed_tool_actions
        if isinstance(value, str) and value.strip()
    }
    if resolved_tool_action not in allowed:
        return None, f"tool_action_not_allowed:{resolved_tool_action}"

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
    if projected_service_query and resolved_tool_action in _SERVICE_QUERY_TOOL_ACTIONS:
        projected_args["service_query"] = projected_service_query

    specialist_payload = referents.get("specialist") or {}
    projected_specialist_name = _normalize_text(specialist_payload.get("value"))
    if projected_specialist_name and resolved_tool_action in _SPECIALIST_TOOL_ACTIONS:
        projected_args["specialist_name"] = projected_specialist_name

    projected_specialist_id = _normalize_text(specialist_payload.get("entity_id"))
    if (
        projected_specialist_id
        and resolved_tool_action in _SPECIALIST_TOOL_ACTIONS
        and _looks_like_uuid(projected_specialist_id)
    ):
        projected_args["specialist_id"] = projected_specialist_id

    booking_ref_payload = referents.get("booking_ref") or {}
    projected_booking_ref = _normalize_text(
        booking_ref_payload.get("entity_id") or booking_ref_payload.get("value")
    )
    if (
        projected_booking_ref
        and resolved_tool_action in _BOOKING_REF_TOOL_ACTIONS
        and _looks_like_uuid(projected_booking_ref)
    ):
        projected_args["appointment_id"] = projected_booking_ref

    customer_name = _normalize_text(slots.get("name"))
    if customer_name and resolved_tool_action in _BOOKING_CUSTOMER_TOOL_ACTIONS:
        projected_args["customer_name"] = customer_name

    customer_phone = _normalize_text(slots.get("phone"))
    if customer_phone and resolved_tool_action in _BOOKING_CUSTOMER_TOOL_ACTIONS:
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


__all__ = ["PolicyToolProjection", "project_policy_tool_binding"]
