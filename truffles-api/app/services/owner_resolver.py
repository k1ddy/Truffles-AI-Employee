from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.interaction_owner_matrix_service import load_interaction_owner_matrix

_TIMEOUT_BOUNDARY_EXPECTED_REPLY_TYPES = frozenset({"service", "time", "name", "phone"})


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_token(value: Any) -> str | None:
    cleaned = _clean_text(value)
    return cleaned.casefold() if cleaned else None


def _normalize_tokens(values: Any) -> tuple[str, ...]:
    if isinstance(values, (list, tuple, set)):
        source = values
    elif values is None:
        source = ()
    else:
        source = (values,)
    tokens: list[str] = []
    seen: set[str] = set()
    for item in source:
        token = _normalize_token(item)
        if not token or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tuple(tokens)


def _normalize_slot_tokens(values: Any) -> tuple[str, ...]:
    if isinstance(values, str):
        source = (values,)
    elif isinstance(values, (list, tuple, set)):
        source = values
    else:
        source = ()
    slots: list[str] = []
    seen: set[str] = set()
    for item in source:
        cleaned = _clean_text(item)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        slots.append(cleaned)
    return tuple(slots)


def _clean_mapping(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return dict(value)


def _normalized_grounded_referents(interaction_state: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(interaction_state, dict):
        return {}
    grounded = interaction_state.get("grounded_referents")
    if not isinstance(grounded, dict):
        return {}
    normalized: dict[str, str] = {}
    for raw_key, raw_value in grounded.items():
        key = _normalize_token(raw_key)
        value = _clean_text(raw_value)
        if key and value:
            normalized[key] = value
    return normalized


@dataclass(frozen=True)
class OwnerResolution:
    row_id: str
    execution_owner: str
    reason_code: str
    service_query: str | None
    preserve_expected_reply_type: str | None
    bypass_service_clarify: bool


@dataclass(frozen=True)
class OwnerResolutionInput:
    tool_action: str | None
    info_refs: tuple[str, ...]
    expected_reply_type: str | None
    expected_reply_reason: str | None
    interaction_target: str | None
    interaction_relation: str | None
    interaction_state: dict[str, Any] | None
    booking_state: dict[str, Any] | None
    service_query: str | None


@dataclass(frozen=True)
class TimeoutOwnerBoundaryInput:
    booking_active: bool
    current_goal: str | None
    matched_booking_followup_state: dict[str, Any] | None = None
    matched_booking_followup_prompt: str | None = None
    matched_booking_followup_expected: str | None = None
    matched_booking_filled_slots: tuple[str, ...] = ()
    slot_fill_followup_state: dict[str, Any] | None = None
    slot_fill_followup_prompt: str | None = None
    slot_fill_followup_expected: str | None = None
    slot_fill_applied: tuple[str, ...] = ()
    resume_contract_state: dict[str, Any] | None = None
    resume_contract_prompt: str | None = None
    resume_contract_expected: str | None = None


@dataclass(frozen=True)
class TimeoutOwnerBoundaryResolution:
    source: str
    execution_owner: str
    reason_code: str
    recovery: str
    trace_decision: str
    expected_reply_type: str
    expected_reply_reason: str
    prompt: str
    booking_state: dict[str, Any]
    filled_slots: tuple[str, ...]
    missing_slot: str | None


def _match_runtime_contract(
    row: dict[str, Any],
    payload: OwnerResolutionInput,
    grounded_referents: dict[str, str],
) -> bool:
    semantic_axes = row.get("semantic_axes") if isinstance(row.get("semantic_axes"), dict) else {}
    row_expected_reply_type = _normalize_token(semantic_axes.get("expected_reply_type"))
    if row_expected_reply_type and row_expected_reply_type != _normalize_token(
        payload.expected_reply_type
    ):
        return False

    runtime_match = row.get("runtime_match") if isinstance(row.get("runtime_match"), dict) else {}
    if not runtime_match:
        return False

    expected_tool_action = _normalize_token(runtime_match.get("tool_action"))
    if expected_tool_action and expected_tool_action != _normalize_token(payload.tool_action):
        return False

    required_info_refs = set(_normalize_tokens(runtime_match.get("info_refs")))
    if required_info_refs and not required_info_refs.issubset(set(payload.info_refs)):
        return False

    expected_reply_reason = _normalize_token(runtime_match.get("expected_reply_reason"))
    if expected_reply_reason and expected_reply_reason != _normalize_token(
        payload.expected_reply_reason
    ):
        return False

    interaction_target = _normalize_token(runtime_match.get("interaction_target"))
    if interaction_target and interaction_target != _normalize_token(payload.interaction_target):
        return False

    interaction_relation = _normalize_token(runtime_match.get("interaction_relation"))
    if interaction_relation and interaction_relation != _normalize_token(
        payload.interaction_relation
    ):
        return False

    if runtime_match.get("require_booking_active") is True:
        if not isinstance(payload.booking_state, dict) or not bool(payload.booking_state.get("active")):
            return False

    if runtime_match.get("require_missing_service_query") is True and _clean_text(payload.service_query):
        return False

    required_grounded = set(_normalize_tokens(runtime_match.get("require_grounded_referents")))
    if required_grounded and not required_grounded.issubset(set(grounded_referents)):
        return False

    return True


def resolve_interaction_owner(payload: OwnerResolutionInput) -> OwnerResolution | None:
    matrix = load_interaction_owner_matrix()
    grounded_referents = _normalized_grounded_referents(payload.interaction_state)
    rows = matrix.payload.get("rows") if isinstance(matrix.payload.get("rows"), list) else []

    for row in rows:
        if not isinstance(row, dict):
            continue
        runtime_match = row.get("runtime_match") if isinstance(row.get("runtime_match"), dict) else {}
        runtime_effects = (
            row.get("runtime_effects") if isinstance(row.get("runtime_effects"), dict) else {}
        )
        if not runtime_match or not runtime_effects:
            continue
        if not _match_runtime_contract(row, payload, grounded_referents):
            continue

        row_id = _clean_text(row.get("row_id")) or "M0"
        service_query = None
        carryover_refs = set(_normalize_tokens(runtime_effects.get("carryover_grounded_referents")))
        if "service" in carryover_refs:
            service_query = grounded_referents.get("service")
            if not service_query and isinstance(payload.booking_state, dict):
                service_query = _clean_text(payload.booking_state.get("service"))

        execution_owner = _clean_text(row.get("execution_owner")) or row_id
        reason_code = _clean_text(runtime_effects.get("reason_code")) or "interaction_owner_resolved"
        preserve_expected_reply_type = _clean_text(
            runtime_effects.get("preserve_expected_reply_type")
        )
        return OwnerResolution(
            row_id=row_id,
            execution_owner=execution_owner,
            reason_code=reason_code,
            service_query=service_query,
            preserve_expected_reply_type=preserve_expected_reply_type,
            bypass_service_clarify=bool(runtime_effects.get("bypass_service_clarify")),
        )
    return None


def _build_timeout_owner_boundary_resolution(
    *,
    source: str,
    booking_active: bool,
    current_goal: str | None,
    booking_state: dict[str, Any] | None,
    prompt: str | None,
    expected_reply_type: str | None,
    filled_slots: Any,
) -> TimeoutOwnerBoundaryResolution | None:
    cleaned_prompt = _clean_text(prompt)
    cleaned_expected_reply_type = _normalize_token(expected_reply_type)
    cleaned_booking_state = _clean_mapping(booking_state)
    if (
        not cleaned_prompt
        or cleaned_expected_reply_type not in _TIMEOUT_BOUNDARY_EXPECTED_REPLY_TYPES
        or not isinstance(cleaned_booking_state, dict)
    ):
        return None
    booking_active_effective = bool(
        booking_active
        or current_goal == "booking"
        or cleaned_booking_state.get("active") is True
    )
    if not booking_active_effective:
        return None

    if source == "matched_expected_reply":
        return TimeoutOwnerBoundaryResolution(
            source=source,
            execution_owner="timeout matched booking collect owner boundary",
            reason_code="timeout_owner_boundary_matched_expected_reply",
            recovery="timeout_owner_boundary_collect",
            trace_decision="timeout_owner_boundary_collect",
            expected_reply_type=cleaned_expected_reply_type,
            expected_reply_reason="policy_core_timeout_owner_boundary",
            prompt=cleaned_prompt,
            booking_state=cleaned_booking_state,
            filled_slots=_normalize_slot_tokens(filled_slots),
            missing_slot=_clean_text(cleaned_booking_state.get("last_question")),
        )
    if source == "slot_fill_followup":
        return TimeoutOwnerBoundaryResolution(
            source=source,
            execution_owner="timeout booking slot-fill owner boundary",
            reason_code="timeout_owner_boundary_slot_fill_followup",
            recovery="timeout_booking_slot_fill_followup",
            trace_decision="timeout_booking_slot_fill_followup",
            expected_reply_type=cleaned_expected_reply_type,
            expected_reply_reason="policy_core_timeout_booking_slot_fill_followup",
            prompt=cleaned_prompt,
            booking_state=cleaned_booking_state,
            filled_slots=_normalize_slot_tokens(filled_slots),
            missing_slot=_clean_text(cleaned_booking_state.get("last_question")),
        )
    if source == "resume_contract":
        return TimeoutOwnerBoundaryResolution(
            source=source,
            execution_owner="timeout booking resume contract boundary",
            reason_code="timeout_owner_boundary_resume_contract",
            recovery="timeout_owner_boundary_collect",
            trace_decision="timeout_owner_boundary_collect",
            expected_reply_type=cleaned_expected_reply_type,
            expected_reply_reason="policy_core_timeout_owner_boundary",
            prompt=cleaned_prompt,
            booking_state=cleaned_booking_state,
            filled_slots=_normalize_slot_tokens(filled_slots),
            missing_slot=_clean_text(cleaned_booking_state.get("last_question")),
        )
    return None


def resolve_timeout_owner_boundary(
    payload: TimeoutOwnerBoundaryInput,
) -> TimeoutOwnerBoundaryResolution | None:
    for source, booking_state, prompt, expected_reply_type, filled_slots in (
        (
            "matched_expected_reply",
            payload.matched_booking_followup_state,
            payload.matched_booking_followup_prompt,
            payload.matched_booking_followup_expected,
            payload.matched_booking_filled_slots,
        ),
        (
            "slot_fill_followup",
            payload.slot_fill_followup_state,
            payload.slot_fill_followup_prompt,
            payload.slot_fill_followup_expected,
            payload.slot_fill_applied,
        ),
        (
            "resume_contract",
            payload.resume_contract_state,
            payload.resume_contract_prompt,
            payload.resume_contract_expected,
            (),
        ),
    ):
        resolution = _build_timeout_owner_boundary_resolution(
            source=source,
            booking_active=payload.booking_active,
            current_goal=payload.current_goal,
            booking_state=booking_state,
            prompt=prompt,
            expected_reply_type=expected_reply_type,
            filled_slots=filled_slots,
        )
        if resolution is not None:
            return resolution
    return None


def build_owner_resolution_input(
    *,
    tool_action: str | None,
    info_refs: Any,
    expected_reply_type: str | None,
    expected_reply_reason: str | None,
    interaction_state: dict[str, Any] | None,
    booking_state: dict[str, Any] | None,
    service_query: str | None,
) -> OwnerResolutionInput:
    interaction_state_payload = interaction_state if isinstance(interaction_state, dict) else {}
    return OwnerResolutionInput(
        tool_action=_clean_text(tool_action),
        info_refs=_normalize_tokens(info_refs),
        expected_reply_type=_clean_text(expected_reply_type),
        expected_reply_reason=_clean_text(expected_reply_reason),
        interaction_target=_clean_text(interaction_state_payload.get("interaction_target")),
        interaction_relation=_clean_text(interaction_state_payload.get("interaction_relation")),
        interaction_state=interaction_state_payload,
        booking_state=booking_state if isinstance(booking_state, dict) else None,
        service_query=_clean_text(service_query),
    )


__all__ = [
    "OwnerResolution",
    "OwnerResolutionInput",
    "TimeoutOwnerBoundaryInput",
    "TimeoutOwnerBoundaryResolution",
    "build_owner_resolution_input",
    "resolve_interaction_owner",
    "resolve_timeout_owner_boundary",
]
