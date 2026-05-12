from __future__ import annotations

from functools import lru_cache
from itertools import combinations
from typing import Any, Iterable, Mapping

from pydantic import BaseModel, ConfigDict

from app.schemas.intent import (
    SEMANTIC_ACTIVE_QUESTION_RELATION_VALUES,
    SEMANTIC_CAPABILITY_VALUES,
    SEMANTIC_PENDING_QUESTION_ACT_VALUES,
    SEMANTIC_PENDING_QUESTION_TARGET_VALUES,
    SEMANTIC_RESOLUTION_MODE_VALUES,
    SEMANTIC_SUBJECT_KIND_VALUES,
    SEMANTIC_TEMPORAL_SCOPE_VALUES,
)
from app.services.policy_prompt_snapshot_service import (
    policy_core_generated_contract_semantic_tokens,
)


class PolicyCoreVocabularySnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "policy_core_vocabulary_snapshot.v1"
    vocabulary_version: str = "v1"
    intents: tuple[str, ...]
    actions: tuple[str, ...]
    expected_reply_types: tuple[str, ...]
    next_questions: tuple[str, ...]
    subject_kinds: tuple[str, ...]
    capabilities: tuple[str, ...]
    temporal_scopes: tuple[str, ...]
    resolution_modes: tuple[str, ...]
    pending_question_acts: tuple[str, ...]
    pending_question_targets: tuple[str, ...]
    active_question_relations: tuple[str, ...]

    def semantic_contract_allowlists(self) -> dict[str, frozenset[str]]:
        return {
            "subject_kind": frozenset(self.subject_kinds),
            "capability": frozenset(self.capabilities),
            "temporal_scope": frozenset(self.temporal_scopes),
            "resolution_mode": frozenset(self.resolution_modes),
            "requested_effect": frozenset(
                {
                    "collect_missing_input",
                    "commit_booking",
                    "deliver_grounded_fact",
                    "handoff_to_human",
                    "retrieve_booking",
                }
            ),
            "tool_action_hint": frozenset(
                {
                    "calendar.book_slot",
                    "calendar.cancel",
                    "calendar.get_booking",
                    "calendar.list_slots",
                    "calendar.reschedule",
                    "catalog.location",
                    "catalog.portfolio",
                    "catalog.service_query",
                    "collect",
                    "consult",
                    "handoff",
                    "info",
                }
            ),
            "pending_question_act": frozenset(self.pending_question_acts),
            "pending_question_target": frozenset(self.pending_question_targets),
            "active_question_relation": frozenset(self.active_question_relations),
        }


@lru_cache(maxsize=1)
def build_policy_core_vocabulary_snapshot() -> PolicyCoreVocabularySnapshotV1:
    snapshot = PolicyCoreVocabularySnapshotV1(
        intents=(
            "booking",
            "check_booking",
            "verify_booking",
            "pricing",
            "duration",
            "location",
            "hours",
            "promotions",
            "master_query",
            "consult",
            "greeting",
            "thanks",
            "out_of_domain",
            "other",
        ),
        actions=("fact", "collect", "handoff"),
        expected_reply_types=("service_choice", "time", "name", "phone", "media"),
        next_questions=("service", "datetime", "name", "phone", "media"),
        subject_kinds=tuple(sorted(SEMANTIC_SUBJECT_KIND_VALUES)),
        capabilities=tuple(sorted(SEMANTIC_CAPABILITY_VALUES)),
        temporal_scopes=tuple(sorted(SEMANTIC_TEMPORAL_SCOPE_VALUES)),
        resolution_modes=tuple(sorted(SEMANTIC_RESOLUTION_MODE_VALUES)),
        pending_question_acts=tuple(sorted(SEMANTIC_PENDING_QUESTION_ACT_VALUES)),
        pending_question_targets=tuple(sorted(SEMANTIC_PENDING_QUESTION_TARGET_VALUES)),
        active_question_relations=tuple(sorted(SEMANTIC_ACTIVE_QUESTION_RELATION_VALUES)),
    )
    _validate_generated_contract_vocabulary_sync(snapshot)
    return snapshot


def _validate_generated_contract_vocabulary_sync(
    snapshot: PolicyCoreVocabularySnapshotV1,
) -> None:
    required = policy_core_generated_contract_semantic_tokens()
    allowlists = {
        "intents": frozenset(snapshot.intents),
        "actions": frozenset(snapshot.actions),
        "expected_reply_types": frozenset(snapshot.expected_reply_types),
        "next_questions": frozenset(snapshot.next_questions),
        "subject_kinds": frozenset(snapshot.subject_kinds),
        "capabilities": frozenset(snapshot.capabilities),
        "temporal_scopes": frozenset(snapshot.temporal_scopes),
        "resolution_modes": frozenset(snapshot.resolution_modes),
        "pending_question_acts": frozenset(snapshot.pending_question_acts),
        "pending_question_targets": frozenset(snapshot.pending_question_targets),
        "active_question_relations": frozenset(snapshot.active_question_relations),
    }
    missing: dict[str, list[str]] = {}
    for category, values in required.items():
        allowed = allowlists.get(category)
        if allowed is None:
            continue
        missing_values = sorted(value for value in values if value not in allowed)
        if missing_values:
            missing[category] = missing_values
    if missing:
        raise ValueError(
            "policy_core_generated_contract_vocabulary_sync_failed:"
            f" {missing}"
        )


@lru_cache(maxsize=1)
def policy_core_semantic_contract_allowlists() -> dict[str, frozenset[str]]:
    return build_policy_core_vocabulary_snapshot().semantic_contract_allowlists()


def _build_required_object_schema(
    properties: dict[str, Any],
    *,
    required: list[str] | None = None,
) -> dict[str, Any]:
    required_fields = list(required) if required is not None else list(properties.keys())
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required_fields,
        "properties": dict(properties),
    }


def _build_sparse_object_variants(
    properties: dict[str, Any],
    *,
    include_empty: bool = True,
) -> list[dict[str, Any]]:
    ordered_keys = list(properties.keys())
    variants: list[dict[str, Any]] = []
    start_size = 0 if include_empty else 1
    for size in range(start_size, len(ordered_keys) + 1):
        for subset in combinations(ordered_keys, size):
            subset_keys = list(subset)
            variants.append(
                _build_required_object_schema(
                    {key: properties[key] for key in subset_keys},
                    required=subset_keys,
                )
            )
    return variants


def _build_sparse_object_anyof(
    properties: dict[str, Any],
    *,
    include_empty: bool = True,
) -> dict[str, Any]:
    return {
        "anyOf": _build_sparse_object_variants(
            properties,
            include_empty=include_empty,
        )
    }


def _build_strict_response_format_field_schema(value: Any) -> dict[str, Any] | None:
    if isinstance(value, bool):
        return {"type": "boolean", "enum": [value]}
    if isinstance(value, str):
        return {"type": "string", "enum": [value]}
    if value is None:
        return {"type": "null"}
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        normalized_items = [item for item in value if item]
        if not normalized_items:
            return {"type": "array", "items": {"type": "string"}, "maxItems": 0}
        allowed_items = list(dict.fromkeys(normalized_items))
        return {
            "type": "array",
            "items": {"type": "string", "enum": allowed_items},
            "minItems": len(normalized_items),
            "maxItems": len(normalized_items),
        }
    if isinstance(value, Mapping):
        schema_keys = {
            "type",
            "enum",
            "anyOf",
            "allOf",
            "oneOf",
            "properties",
            "required",
            "items",
            "additionalProperties",
            "minLength",
            "maxLength",
            "minItems",
            "maxItems",
            "minimum",
            "maximum",
        }
        if any(key in value for key in schema_keys):
            return dict(value)
        properties: dict[str, Any] = {}
        for key, nested_value in value.items():
            if not isinstance(key, str) or not key.strip():
                continue
            nested_schema = _build_strict_response_format_field_schema(nested_value)
            if nested_schema is None:
                continue
            properties[key] = nested_schema
        if properties:
            return {
                "type": "object",
                "additionalProperties": False,
                "required": list(properties.keys()),
                "properties": properties,
            }
    return None


def build_policy_core_response_format(
    allowed_tool_actions: Iterable[str],
    *,
    forced_field_values: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot = build_policy_core_vocabulary_snapshot()
    allowed_actions = [
        value.strip()
        for value in allowed_tool_actions
        if isinstance(value, str) and value.strip()
    ]
    nullable_string = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    nullable_number = {"anyOf": [{"type": "number", "minimum": 0, "maximum": 1}, {"type": "null"}]}
    nullable_string_list = {
        "anyOf": [
            {"type": "array", "items": {"type": "string"}},
            {"type": "null"},
        ]
    }
    nullable_pack_refs = {
        "anyOf": [
            {"type": "array", "items": {"type": "string"}},
            {"type": "null"},
        ]
    }
    nullable_sparse_slots = {"anyOf": [_build_sparse_object_anyof(
        {
            "service": nullable_string,
            "datetime": nullable_string,
            "name": nullable_string,
            "phone": nullable_string,
        }
    ), {"type": "null"}]}

    def nullable_string_enum(values: Iterable[str]) -> dict[str, Any]:
        return {"anyOf": [{"type": "string", "enum": list(values)}, {"type": "null"}]}

    referent_payload_schema = {
        "anyOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["value", "entity_id", "entity_type", "source_ref"],
                "properties": {
                    "value": nullable_string,
                    "entity_id": nullable_string,
                    "entity_type": nullable_string,
                    "source_ref": nullable_string,
                },
            },
            {"type": "null"},
        ]
    }
    entity_ref_item_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["entity_id", "entity_type", "source_ref", "value", "confidence"],
        "properties": {
            "entity_id": nullable_string,
            "entity_type": nullable_string,
            "source_ref": nullable_string,
            "value": nullable_string,
            "confidence": nullable_number,
        },
    }
    entity_refs_schema = {
        "anyOf": [
            {"type": "array", "items": entity_ref_item_schema},
            {"type": "null"},
        ]
    }
    sparse_referents_schema = {
        "anyOf": [
            _build_sparse_object_anyof(
                {
                    "service": referent_payload_schema,
                    "specialist": referent_payload_schema,
                    "branch": referent_payload_schema,
                    "booking_ref": referent_payload_schema,
                    "customer": referent_payload_schema,
                }
            ),
            {"type": "null"},
        ]
    }
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "intent": {"type": "string", "enum": list(snapshot.intents)},
            "action": {"type": "string", "enum": list(snapshot.actions)},
            "tool_action_hint": {"type": "string", "enum": allowed_actions},
            "pack_refs": nullable_pack_refs,
            "slots": nullable_sparse_slots,
            "expected_reply_type": nullable_string_enum(snapshot.expected_reply_types),
            "next_question": nullable_string_enum(snapshot.next_questions),
            "open_questions": nullable_string_list,
            "needs_manager": {"type": "boolean"},
            "risk_signals": nullable_string_list,
            "language": nullable_string,
            "confidence": nullable_number,
            "reason": nullable_string,
            "goal": nullable_string,
            "entity_refs": entity_refs_schema,
            "referents": sparse_referents_schema,
            "subject_kind": nullable_string_enum(snapshot.subject_kinds),
            "capability": nullable_string_enum(snapshot.capabilities),
            "temporal_scope": nullable_string_enum(snapshot.temporal_scopes),
            "alternate_datetime": nullable_string,
            "resolution_mode": nullable_string_enum(snapshot.resolution_modes),
            "pending_question_act": nullable_string_enum(snapshot.pending_question_acts),
            "pending_question_target": nullable_string_enum(snapshot.pending_question_targets),
            "active_question_relation": nullable_string_enum(snapshot.active_question_relations),
            "resolver_id": nullable_string,
            "resolver_version": nullable_string,
        },
    }
    if isinstance(forced_field_values, Mapping):
        for key, forced_value in forced_field_values.items():
            if key not in schema["properties"]:
                continue
            forced_schema = _build_strict_response_format_field_schema(forced_value)
            if forced_schema is None:
                continue
            schema["properties"][key] = forced_schema
    schema["required"] = list(schema["properties"].keys())
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "llm_policy_core_output",
            "strict": True,
            "schema": schema,
        },
    }


def build_policy_core_focused_response_format(
    allowed_tool_actions: Iterable[str],
    *,
    forced_field_values: Mapping[str, Any],
) -> dict[str, Any]:
    forced_tool_action = forced_field_values.get("tool_action_hint")
    focused_allowed_tool_actions = (
        [forced_tool_action]
        if isinstance(forced_tool_action, str) and forced_tool_action.strip()
        else allowed_tool_actions
    )
    response_format = build_policy_core_response_format(
        focused_allowed_tool_actions,
        forced_field_values=None,
    )
    schema = response_format["json_schema"]["schema"]
    properties = schema["properties"]
    volatile_value_fields = {
        "alternate_datetime",
        "entity_refs",
        "referents",
        "resolver_id",
        "resolver_version",
        "risk_signals",
        "slots",
    }
    focused_properties = {
        key: properties[key]
        for key in forced_field_values
        if key in properties
    }
    for key, forced_value in forced_field_values.items():
        if key not in focused_properties or key in volatile_value_fields:
            continue
        forced_schema = _build_strict_response_format_field_schema(forced_value)
        if forced_schema is not None:
            focused_properties[key] = forced_schema
    schema["properties"] = focused_properties
    schema["required"] = list(focused_properties.keys())
    response_format["json_schema"]["name"] = "llm_policy_core_focused_output"
    return response_format


__all__ = [
    "PolicyCoreVocabularySnapshotV1",
    "build_policy_core_focused_response_format",
    "build_policy_core_response_format",
    "build_policy_core_vocabulary_snapshot",
    "policy_core_semantic_contract_allowlists",
]
