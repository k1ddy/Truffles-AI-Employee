from __future__ import annotations

from functools import lru_cache
from itertools import combinations
from typing import Any, Iterable

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
            "pending_question_act": frozenset(self.pending_question_acts),
            "pending_question_target": frozenset(self.pending_question_targets),
            "active_question_relation": frozenset(self.active_question_relations),
        }


@lru_cache(maxsize=1)
def build_policy_core_vocabulary_snapshot() -> PolicyCoreVocabularySnapshotV1:
    return PolicyCoreVocabularySnapshotV1(
        intents=(
            "booking",
            "check_booking",
            "verify_booking",
            "pricing",
            "duration",
            "location",
            "hours",
            "master_query",
            "consult",
            "greeting",
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


def build_policy_core_response_format(allowed_tool_actions: Iterable[str]) -> dict[str, Any]:
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
            "resolution_mode": nullable_string_enum(snapshot.resolution_modes),
            "pending_question_act": nullable_string_enum(snapshot.pending_question_acts),
            "pending_question_target": nullable_string_enum(snapshot.pending_question_targets),
            "active_question_relation": nullable_string_enum(snapshot.active_question_relations),
            "resolver_id": nullable_string,
            "resolver_version": nullable_string,
        },
    }
    schema["required"] = list(schema["properties"].keys())
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "llm_policy_core_output",
            "strict": True,
            "schema": schema,
        },
    }


__all__ = [
    "PolicyCoreVocabularySnapshotV1",
    "build_policy_core_response_format",
    "build_policy_core_vocabulary_snapshot",
    "policy_core_semantic_contract_allowlists",
]
