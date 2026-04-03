from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.services.interaction_owner_matrix_service import load_interaction_owner_matrix

_SEMANTIC_ENTITY_TYPES_SPECIALIST = frozenset({"specialist", "master"})
_SEMANTIC_EXPECTED_REPLY_TIME = "time"
_SEMANTIC_EXPECTED_REPLY_NAME = "name"
_SEMANTIC_EXPECTED_REPLY_SERVICE = "service_choice"


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
class SemanticContractView:
    subject_kind: str | None
    capability: str | None
    temporal_scope: str | None
    resolution_mode: str | None
    pending_question_act: str | None
    pending_question_target: str | None
    active_question_relation: str | None
    specialist_name: str | None
    specialist_id: str | None


def _normalize_semantic_entity_refs(values: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(values, list):
        return ()
    cleaned: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for item in values:
        if not isinstance(item, dict):
            continue
        entity_id = _clean_text(item.get("entity_id") or item.get("id"))
        entity_type = _normalize_token(item.get("entity_type") or item.get("type"))
        entity_value = _clean_text(item.get("value") or item.get("label"))
        source_ref = _normalize_token(item.get("source_ref"))
        confidence = item.get("confidence")
        row: dict[str, Any] = {}
        if entity_id:
            row["entity_id"] = entity_id
        if entity_type:
            row["entity_type"] = entity_type
        if entity_value:
            row["value"] = entity_value
        if source_ref:
            row["source_ref"] = source_ref
        if isinstance(confidence, (int, float)):
            row["confidence"] = max(0.0, min(float(confidence), 1.0))
        if not row:
            continue
        fingerprint = (
            str(row.get("entity_id") or ""),
            str(row.get("entity_type") or ""),
            str(row.get("value") or ""),
            str(row.get("source_ref") or ""),
        )
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        cleaned.append(row)
    return tuple(cleaned)


def _coerce_uuid_text(value: Any) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    try:
        return str(UUID(cleaned))
    except (TypeError, ValueError):
        return None


def _extract_specialist_from_entity_refs(entity_refs: tuple[dict[str, Any], ...]) -> tuple[str | None, str | None]:
    for row in entity_refs:
        entity_type = _normalize_token(row.get("entity_type"))
        if entity_type not in _SEMANTIC_ENTITY_TYPES_SPECIALIST:
            continue
        specialist_name = _clean_text(row.get("value"))
        entity_id = _clean_text(row.get("entity_id"))
        specialist_id = _coerce_uuid_text(entity_id)
        if specialist_name:
            return specialist_name, specialist_id
        if specialist_id:
            return None, specialist_id
        if entity_id:
            return entity_id, None
    return None, None


def _extract_specialist_from_semantic_contract(
    semantic_contract: dict[str, Any] | None,
    *,
    entity_refs: tuple[dict[str, Any], ...],
) -> tuple[str | None, str | None]:
    if not isinstance(semantic_contract, dict):
        return _extract_specialist_from_entity_refs(entity_refs)
    referents = semantic_contract.get("referents")
    if isinstance(referents, dict):
        specialist_payload = referents.get("specialist")
        if isinstance(specialist_payload, dict):
            specialist_name = _clean_text(specialist_payload.get("value"))
            entity_id = _clean_text(specialist_payload.get("entity_id"))
            specialist_id = _coerce_uuid_text(entity_id)
            if specialist_name:
                return specialist_name, specialist_id
            if specialist_id:
                return None, specialist_id
            if entity_id:
                return entity_id, None
    return _extract_specialist_from_entity_refs(entity_refs)


def extract_specialist_preference(
    *,
    semantic_contract: dict[str, Any] | None = None,
    tool_args: dict[str, Any] | None = None,
    entity_refs: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
) -> tuple[str | None, str | None]:
    if isinstance(tool_args, dict):
        specialist_name = _clean_text(tool_args.get("specialist_name"))
        raw_specialist_id = _clean_text(tool_args.get("specialist_id"))
        specialist_id = _coerce_uuid_text(raw_specialist_id)
        if specialist_name:
            return specialist_name, specialist_id
        if specialist_id:
            return None, specialist_id
        if raw_specialist_id:
            return raw_specialist_id, None
    normalized_refs = _normalize_semantic_entity_refs(list(entity_refs or ()))
    return _extract_specialist_from_semantic_contract(
        semantic_contract,
        entity_refs=normalized_refs,
    )


def build_semantic_contract_view(
    *,
    semantic_contract: dict[str, Any] | None = None,
    tool_args: dict[str, Any] | None = None,
    entity_refs: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
    subject_kind: str | None = None,
    capability: str | None = None,
    temporal_scope: str | None = None,
    resolution_mode: str | None = None,
    pending_question_act: str | None = None,
    pending_question_target: str | None = None,
    active_question_relation: str | None = None,
) -> SemanticContractView:
    contract = dict(semantic_contract) if isinstance(semantic_contract, dict) else {}
    normalized_refs = _normalize_semantic_entity_refs(
        contract.get("entity_refs") or list(entity_refs or ())
    )
    specialist_name, specialist_id = _extract_specialist_from_semantic_contract(
        contract,
        entity_refs=normalized_refs,
    )
    if specialist_name is None and specialist_id is None:
        specialist_name, specialist_id = extract_specialist_preference(
            tool_args=tool_args,
            entity_refs=normalized_refs,
        )
    return SemanticContractView(
        subject_kind=_normalize_token(contract.get("subject_kind")) or _normalize_token(subject_kind),
        capability=_normalize_token(contract.get("capability")) or _normalize_token(capability),
        temporal_scope=_normalize_token(contract.get("temporal_scope")) or _normalize_token(temporal_scope),
        resolution_mode=_normalize_token(contract.get("resolution_mode")) or _normalize_token(resolution_mode),
        pending_question_act=_normalize_token(contract.get("pending_question_act"))
        or _normalize_token(pending_question_act),
        pending_question_target=_normalize_token(contract.get("pending_question_target"))
        or _normalize_token(pending_question_target),
        active_question_relation=_normalize_token(contract.get("active_question_relation"))
        or _normalize_token(active_question_relation),
        specialist_name=specialist_name,
        specialist_id=specialist_id,
    )


def should_preserve_specialist_followup_owner(
    *,
    semantic_view: SemanticContractView,
    policy_goal: str | None,
    policy_collect_slot: str | None,
    expected_reply_type: str | None,
) -> bool:
    normalized_goal = _normalize_token(policy_goal)
    normalized_collect_slot = _normalize_token(policy_collect_slot)
    if normalized_goal != "booking":
        return False
    relation_token = semantic_view.active_question_relation
    if relation_token not in {None, "referent_followup"}:
        return False
    if semantic_view.pending_question_target == "specialist":
        if semantic_view.specialist_name or semantic_view.specialist_id:
            return True
        if normalized_collect_slot not in {None, "datetime"}:
            return False
        if expected_reply_type != _SEMANTIC_EXPECTED_REPLY_TIME:
            return False
        return semantic_view.resolution_mode == "referent_followup"
    if semantic_view.pending_question_target is not None:
        return False
    if normalized_collect_slot not in {None, "datetime"}:
        return False
    if expected_reply_type != _SEMANTIC_EXPECTED_REPLY_TIME:
        return False
    if semantic_view.subject_kind != "specialist" or semantic_view.capability != "bookability":
        return False
    return bool(semantic_view.specialist_name or semantic_view.specialist_id)


def should_preserve_specialist_availability_followup_owner(
    *,
    semantic_view: SemanticContractView,
    policy_goal: str | None,
    policy_collect_slot: str | None,
) -> bool:
    normalized_goal = _normalize_token(policy_goal)
    normalized_collect_slot = _normalize_token(policy_collect_slot)
    if normalized_goal != "booking":
        return False
    if normalized_collect_slot == "name":
        if semantic_view.temporal_scope not in {"specific_time", "day", "weekday", "weekend"}:
            return False
    elif normalized_collect_slot not in {None, "datetime"}:
        return False
    if semantic_view.pending_question_target != "specialist":
        return False
    if semantic_view.subject_kind not in {None, "specialist"}:
        return False
    if semantic_view.capability not in {None, "live_availability", "bookability"}:
        return False
    if semantic_view.temporal_scope not in {
        "specific_time",
        "day",
        "weekday",
        "weekend",
        "date_range",
    }:
        return False
    return semantic_view.active_question_relation == "specialist_availability_followup"


def should_preserve_service_choice_specialist_availability_followup_owner(
    *,
    semantic_view: SemanticContractView,
    policy_goal: str | None,
    policy_collect_slot: str | None,
    expected_reply_type: str | None,
) -> bool:
    normalized_goal = _normalize_token(policy_goal)
    normalized_collect_slot = _normalize_token(policy_collect_slot)
    if normalized_goal != "info":
        return False
    if normalized_collect_slot != "datetime":
        return False
    if expected_reply_type != _SEMANTIC_EXPECTED_REPLY_SERVICE:
        return False
    if semantic_view.pending_question_act != "ask_about_requested_slot":
        return False
    if semantic_view.pending_question_target != "specialist":
        return False
    if semantic_view.subject_kind not in {None, "specialist"}:
        return False
    if semantic_view.capability != "live_availability":
        return False
    if semantic_view.temporal_scope not in {"specific_time", "day", "weekday", "weekend"}:
        return False
    if semantic_view.active_question_relation not in {None, "ask_about_requested_slot"}:
        return False
    return semantic_view.resolution_mode == "clarify_missing_time"


def should_preserve_active_name_time_availability_followup_owner(
    *,
    semantic_view: SemanticContractView,
    policy_goal: str | None,
    policy_collect_slot: str | None,
    expected_reply_type: str | None,
) -> bool:
    normalized_goal = _normalize_token(policy_goal)
    normalized_collect_slot = _normalize_token(policy_collect_slot)
    if normalized_goal != "booking" or normalized_collect_slot != "name":
        return False
    if expected_reply_type != _SEMANTIC_EXPECTED_REPLY_NAME:
        return False
    if semantic_view.subject_kind not in {None, "time", "booking"}:
        return False
    if semantic_view.capability not in {None, "live_availability", "bookability"}:
        return False
    if semantic_view.temporal_scope != "specific_time":
        return False
    if (
        semantic_view.pending_question_act == "ask_about_requested_slot"
        and semantic_view.pending_question_target == "time"
    ):
        return semantic_view.active_question_relation in {None, "ask_about_requested_slot"}
    if (
        semantic_view.pending_question_act is not None
        or semantic_view.pending_question_target is not None
    ):
        return False
    if semantic_view.active_question_relation not in {None, "ask_about_requested_slot"}:
        return False
    return semantic_view.resolution_mode == "referent_followup"


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
    "SemanticContractView",
    "build_semantic_contract_view",
    "build_owner_resolution_input",
    "extract_specialist_preference",
    "resolve_interaction_owner",
    "should_preserve_active_name_time_availability_followup_owner",
    "should_preserve_service_choice_specialist_availability_followup_owner",
    "should_preserve_specialist_availability_followup_owner",
    "should_preserve_specialist_followup_owner",
]
