from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator, FormatChecker, RefResolver, ValidationError
from pydantic import ValidationError as PydanticValidationError

from app.core import (
    BindingPlanV1,
    BlockBoundaryRequest,
    BoundaryOverride,
    BoundaryValidator,
    ConversationProjectionV1,
    DegradeBoundaryRequest,
    DialogState,
    DialogStateService,
    FactContractV1,
    FactManifestV1,
    FactPlanV1,
    FactRequestV1,
    FactResultV1,
    PendingQuestionContract,
    PolicyDecision,
    ResponseRealizer,
    RuntimeTraceContractV1,
    SemanticDecisionV1,
    SemanticFrame,
    TurnExecutor,
    TurnJournalV1,
    TurnPlanner,
)
from app.core.consultant_runtime import ConsultantRuntime, LoadedRuntimeState
from app.core.policy_tool_projector import build_binding_plan
from app.core.turn_executor import RuntimeExecutionResult
from app.services.policy_validation_boundary_service import (
    PolicyValidationBoundaryRuntimeHooks,
    PolicyValidationBoundaryRuntimeInput,
    handle_policy_validation_boundary,
)
from tests import build_test_policy_override_decision, build_test_semantic_decision_payload


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _runtime_schema_store() -> dict[str, dict]:
    runtime_dir = _repo_root() / "contracts/runtime"
    store: dict[str, dict] = {}

    for schema_path in runtime_dir.glob("*.jsonschema"):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        store[schema_path.resolve().as_uri()] = schema

        schema_id = schema.get("$id")
        if isinstance(schema_id, str) and schema_id:
            store[schema_id] = schema

    return store


def _load_schema(relative_path: str) -> Draft202012Validator:
    schema_path = _repo_root() / relative_path
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    resolver = RefResolver(
        base_uri=schema_path.resolve().as_uri(),
        referrer=schema,
        store=_runtime_schema_store(),
    )
    return Draft202012Validator(schema, resolver=resolver, format_checker=FormatChecker())


def _policy_payload() -> dict:
    return {
        "schema_version": "policy_decision.v1",
        "outcome": "COLLECT",
        "action": "booking_prompt",
        "intent": "booking",
        "source": "policy_core",
        "tool_action": "calendar.list_slots",
        "tool_args": {"service": "manicure"},
        "slots": {"service": "manicure"},
        "pack_refs": ["services.manicure"],
        "fact_refs": ["info.hours"],
        "capability_refs": ["calendar.list_slots"],
        "risk_signals": [],
        "interaction": {
            "owner": "booking_time_followup",
            "target": "time",
            "relation": "ask_about_requested_slot",
        },
        "pending_question_contract": {
            "expected_reply_type": "time",
            "reason": "booking_time_availability_followup",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        "meta": {"reason_code": "owner_matrix_m27"},
    }


def _binding_plan_payload() -> dict:
    return {
        "schema_version": "binding_plan.v1",
        "binding_id": "binding-001",
        "decision_id": "decision-001",
        "binding_outcome_type": "tool_call",
        "capability_id": "catalog.search",
        "selected_tool_or_workflow_ref": "catalog.service_query",
        "authz_scope": {},
        "resolved_args": {"service_query": "manicure"},
        "timeout_policy": {},
        "retry_policy": {},
        "idempotency_key": "decision-001",
        "deny_reason_code": None,
        "degrade_reason_code": None,
        "handoff_reason_code": None,
    }


def _fact_manifest_payload() -> dict:
    return {
        "schema_version": "fact_manifest.v1",
        "manifest_id": "default_fact_manifest.v1",
        "namespace": "consultant_core",
        "entries": [
            {
                "canonical_ref": "pricing",
                "scope_namespace": "info",
                "aliases": ["payment"],
                "resolver_id": "catalog.service_query",
                "renderer_id": "catalog.service_query.reply",
                "provenance_sources": ["service_catalog", "pack_manifest"],
                "companion_group_id": None,
            },
            {
                "canonical_ref": "parking",
                "scope_namespace": "info",
                "aliases": ["parking_info"],
                "resolver_id": "catalog.location",
                "renderer_id": "catalog.location.reply",
                "provenance_sources": ["branch_catalog", "pack_manifest"],
                "companion_group_id": "location_base_bundle",
            },
        ],
        "companion_groups": [
            {
                "group_id": "location_base_bundle",
                "members": ["location", "hours", "parking"],
                "requested_ref_policies": {
                    "location": ["location", "hours"],
                    "hours": ["location", "hours"],
                    "parking": ["location", "hours", "parking"],
                },
                "composition_mode": "companion_allowed",
                "renderer_id": "catalog.location.reply",
                "provenance_sources": ["branch_catalog", "pack_manifest"],
            }
        ],
    }


def _fact_request_payload() -> dict:
    return {
        "schema_version": "fact_request.v1",
        "manifest_id": "default_fact_manifest.v1",
        "request_id": "fact-request-001",
        "decision_id": "decision-001",
        "intent": "pricing",
        "scope_namespace": "info",
        "requested_fact_refs": ["pricing"],
        "requested_scopes": ["info.pricing"],
        "supporting_pack_refs": ["pricing"],
        "supporting_capability_refs": ["pricing"],
        "subject_kind": "service",
        "subject_scope": "service",
        "resolution_mode": "policy_fact",
        "composition_mode": "single_only",
        "locale_hint": "ru-kz",
        "format_hint": "concise_text",
        "owner_source": "policy_core",
    }


def _fact_plan_payload() -> dict:
    return {
        "schema_version": "fact_plan.v1",
        "manifest_id": "default_fact_manifest.v1",
        "plan_id": "fact-plan-001",
        "request_id": "fact-request-001",
        "decision_id": "decision-001",
        "binding_id": "binding-001",
        "selected_tool_or_workflow_ref": "catalog.service_query",
        "selected_resolver": "catalog.service_query",
        "renderer_id": "catalog.service_query.reply",
        "scope_namespace": "info",
        "requested_fact_refs": ["pricing"],
        "requested_scopes": ["info.pricing"],
        "composition_mode": "single_only",
        "allowed_emitted_sets": [["pricing"]],
        "allowed_emitted_fact_refs": ["pricing"],
        "allowed_emitted_scopes": ["info.pricing"],
        "blocked_scopes": [],
        "bundle_policy": "requested_only",
        "scope_policy_source": "default",
        "fallback_policy": "deny_out_of_plan",
        "provenance_sources": ["service_catalog", "pack_manifest"],
    }


def _fact_result_payload() -> dict:
    return {
        "schema_version": "fact_result.v1",
        "result_id": "fact-result-001",
        "plan_id": "fact-plan-001",
        "decision_id": "decision-001",
        "selected_tool_or_workflow_ref": "catalog.service_query",
        "selected_source": "tool_registry",
        "resolution_source": "tool_registry",
        "retrieval_mode": "resolved",
        "renderer_id": "catalog.service_query.reply",
        "scope_namespace": "info",
        "emitted_fact_refs": ["pricing"],
        "emitted_scopes": ["info.pricing"],
        "omitted_fact_refs": [],
        "out_of_scope_fact_refs": [],
        "scope_verdict": "ok",
        "response_generated": True,
        "resolution_reason": "pricing",
        "fallback_reason": None,
        "provenance": ["service_catalog", "pack_manifest"],
    }


def _fact_contract_payload() -> dict:
    return {
        "schema_version": "fact_contract.v1",
        "manifest_id": "default_fact_manifest.v1",
        "request": _fact_request_payload(),
        "plan": _fact_plan_payload(),
        "result": _fact_result_payload(),
    }


def _dialog_state_payload() -> dict:
    return {
        "schema_version": "dialog_state.v1",
        "semantic_state": {
            "schema_version": "canonical_semantic_state.v1",
            "materialized_frame": {
                "schema_version": "semantic_frame.v2",
                "user_goal": "booking",
                "requested_effect": "collect_missing_input",
                "subject": {},
                "referents": {
                    "branch": {
                        "value": "almaty-center",
                        "entity_type": "branch",
                        "source_ref": "carryover",
                    }
                },
                "constraints": {},
                "preferences": {},
                "continuation": {
                    "expected_reply_type": "time",
                    "reason": "booking_time_availability_followup",
                    "pending_question_act": "ask_about_requested_slot",
                    "pending_question_target": "time",
                    "active_question_relation": "ask_about_requested_slot",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                },
                "capability_selection": {},
                "needs_human": False,
                "reason": "booking_time_availability_followup",
            },
            "event_log": [],
        },
        "current_referents": {
            "service": "manicure",
            "specialist": None,
            "branch": "almaty-center",
            "booking": None,
            "customer": None,
        },
        "pending_question_contract": {
            "expected_reply_type": "time",
            "reason": "booking_time_availability_followup",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        "interaction_state": {
            "resume_slot": "time",
            "interaction_target": "time",
            "interaction_relation": "ask_about_requested_slot",
            "interaction_owner": "booking_time_followup",
            "grounded_referents": {"service": "manicure", "branch": "almaty-center"},
            "confirmation_state": None,
            "degrade_reason": None,
        },
        "projections": {
            "expected_reply_type": "time",
            "expected_reply_reason": "booking_time_availability_followup",
            "session_memory_interaction_state": {
                "resume_slot": "time",
                "interaction_target": "time",
                "interaction_relation": "ask_about_requested_slot",
                "interaction_owner": "booking_time_followup",
                "grounded_referents": {"service": "manicure", "branch": "almaty-center"},
                "confirmation_state": None,
                "degrade_reason": None,
            },
        },
        "meta": {"writer": "dialog_state_service"},
    }


def _boundary_override_payload() -> dict:
    return {
        "schema_version": "boundary_override.v1",
        "decision": "degrade",
        "reason_code": "policy_timeout",
        "preserve_fields": [
            "outcome",
            "interaction_owner",
            "interaction_target",
            "interaction_relation",
            "pending_question_contract",
        ],
        "public_message": "Подберите, пожалуйста, удобное время.",
        "trace_message": "preserve relation under timeout",
        "replan_hints": ["preserve active pending-question relation"],
        "meta": {"source": "boundary_validator"},
    }


def _turn_result_payload() -> dict:
    return {
        "schema_version": "turn_result.v1",
        "outcome": "COLLECT",
        "contract_status": "degraded",
        "policy_decision": _policy_payload(),
        "boundary_override": _boundary_override_payload(),
        "reply": {
            "channel": "whatsapp",
            "reply_kind": "collect",
            "text": "Подберите, пожалуйста, удобное время.",
            "meta": {"outcome": "COLLECT"},
        },
        "tool_outcomes": [
            {
                "tool": "calendar.list_slots",
                "status": "degraded",
                "reason_code": "policy_timeout",
                "payload": {},
            }
        ],
        "dialog_state": _dialog_state_payload(),
        "observability": {
            "reason_code": "policy_timeout",
            "decision_stage": "executor",
            "meta": {"outcome": "COLLECT"},
        },
        "trace": {
            "reason_code": "policy_timeout",
            "stages": ["planner", "boundary", "executor", "realizer"],
        },
    }


def test_consultant_runtime_plan_turn_passes_dialog_state_continuity_to_policy_core() -> None:
    runtime = ConsultantRuntime()
    captured: dict[str, object] = {}

    def _fake_plan(**kwargs):
        captured.update(kwargs)
        semantic_decision = SemanticDecisionV1.from_policy_core_payload(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "next_question": "datetime",
                "open_questions": ["datetime"],
            }
        )
        return TurnPlanner().build_from_semantic_decision(
            semantic_decision,
            binding_tool_action="collect",
            interaction_owner="llm_policy_core_booking",
            source="llm_policy_core",
        )

    runtime.planner.plan = _fake_plan
    runtime._build_memory_summary = lambda *_args, **_kwargs: "user: test"
    state = DialogState.model_validate(_dialog_state_payload())
    state.current_referents.specialist = "Айгерим"
    state.current_referents.customer = "Марина"
    state.interaction_state.grounded_referents = {
        "service": "manicure",
        "specialist": "Айгерим",
        "customer": "Марина",
    }
    state.semantic_state.materialized_frame.subject = {
        "kind": "specialist",
        "value": "Айгерим",
        "entity_refs": [
            {
                "entity_id": "svc:manicure",
                "entity_type": "service",
                "value": "manicure",
                "source_ref": "carryover",
            },
            {
                "entity_id": "spec:aigerim",
                "entity_type": "specialist",
                "value": "Айгерим",
                "source_ref": "carryover",
            },
        ],
    }
    state.semantic_state.materialized_frame.capability_selection = {
        "capability": "bookability",
        "resolution_mode": "referent_followup",
    }
    state.semantic_state.materialized_frame.referents = {
        "service": {
            "value": "manicure",
            "entity_id": "svc:manicure",
            "entity_type": "service",
            "source_ref": "carryover",
        },
        "specialist": {
            "value": "Айгерим",
            "entity_id": "spec:aigerim",
            "entity_type": "specialist",
            "source_ref": "carryover",
        },
        "branch": {
            "value": "almaty-center",
            "entity_type": "branch",
            "source_ref": "carryover",
        },
        "customer": {
            "value": "Марина",
            "entity_type": "customer",
            "source_ref": "carryover",
        },
    }

    decision, override = runtime._plan_turn(
        db=None,
        payload=SimpleNamespace(
            client_slug="demo_salon",
            body=SimpleNamespace(message="Можно выбрать Айгерим?"),
        ),
        prepared=SimpleNamespace(
            conversation=SimpleNamespace(state="bot_active"),
            branch_id=uuid4(),
        ),
        runtime_state=SimpleNamespace(
            dialog_state=state,
            booking_state={"service": "manicure", "active": True},
            expected_reply_type="time",
            expected_reply_reason="collect:datetime",
            current_goal="booking",
        ),
    )

    memory_profile = captured["memory_profile"]
    assert memory_profile == {
        "active_goal": "booking",
        "slot_state": {"service": "manicure"},
        "pending_question_contract": {
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "expected_reply_type": "time",
            "reason": "booking_time_availability_followup",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
        },
            "semantic_contract": {
                "contract_version": "semantic_contract.v1",
                "subject_kind": "specialist",
                "capability": "bookability",
                "resolution_mode": "referent_followup",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
                "entity_refs": [
                    {
                        "entity_id": "svc:manicure",
                        "entity_type": "service",
                        "value": "manicure",
                    "source_ref": "carryover",
                },
                {
                    "entity_id": "spec:aigerim",
                    "entity_type": "specialist",
                    "value": "Айгерим",
                    "source_ref": "carryover",
                },
            ],
            "referents": {
                "service": {
                    "value": "manicure",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "specialist": {
                    "value": "Айгерим",
                    "entity_id": "spec:aigerim",
                    "entity_type": "specialist",
                    "source_ref": "carryover",
                },
                "branch": {
                    "value": "almaty-center",
                    "entity_type": "branch",
                    "source_ref": "carryover",
                },
                "customer": {
                    "value": "Марина",
                    "entity_type": "customer",
                    "source_ref": "carryover",
                },
            },
        },
    }
    assert decision.interaction.owner == "llm_policy_core_booking"
    assert override is None


def test_consultant_runtime_plan_turn_does_not_prefill_service_from_raw_message() -> None:
    runtime = ConsultantRuntime()
    captured: dict[str, object] = {}

    def _fake_plan(**kwargs):
        captured.update(kwargs)
        semantic_decision = SemanticDecisionV1.from_policy_core_payload(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "slots": {"service": "маникюр"},
                "next_question": "datetime",
                "open_questions": ["datetime"],
            }
        )
        return TurnPlanner().build_from_semantic_decision(
            semantic_decision,
            binding_tool_action="collect",
            interaction_owner="llm_policy_core_booking",
            source="llm_policy_core",
        )

    runtime.planner.plan = _fake_plan
    runtime._build_memory_summary = lambda *_args, **_kwargs: "user: test"
    state = DialogState.model_validate(_dialog_state_payload())
    state.current_referents.service = None

    decision, override = runtime._plan_turn(
        db=None,
        payload=SimpleNamespace(
            client_slug="demo_salon",
            body=SimpleNamespace(message="Хотел бы записаться на маникюр."),
        ),
        prepared=SimpleNamespace(
            conversation=SimpleNamespace(state="bot_active"),
            branch_id=uuid4(),
        ),
        runtime_state=SimpleNamespace(
            dialog_state=state,
            booking_state={},
            expected_reply_type=None,
            expected_reply_reason=None,
            current_goal=None,
        ),
    )

    assert captured["booking_state"] == {}
    assert captured["memory_profile"]["semantic_contract"] == {
        "contract_version": "semantic_contract.v1",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
        "referents": {
            "branch": {
                "value": "almaty-center",
                "entity_type": "branch",
                "source_ref": "carryover",
            }
        },
    }
    assert TurnPlanner().canonical_pending_question_contract(decision).next_question == "datetime"
    assert override is None


def test_consultant_runtime_plan_turn_degrades_synthetic_decision_without_semantic_owner() -> None:
    runtime = ConsultantRuntime()

    runtime.planner.plan = lambda **_kwargs: build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "goal": "booking",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="fill_requested_slot",
        source="llm_policy_core",
    )
    runtime._build_memory_summary = lambda *_args, **_kwargs: "user: test"

    decision, override = runtime._plan_turn(
        db=None,
        payload=SimpleNamespace(
            client_slug="demo_salon",
            body=SimpleNamespace(message="Хочу записаться."),
        ),
        prepared=SimpleNamespace(
            conversation=SimpleNamespace(state="bot_active"),
            branch_id=uuid4(),
        ),
        runtime_state=SimpleNamespace(
            dialog_state=DialogState.model_validate(_dialog_state_payload()),
            booking_state={},
            expected_reply_type=None,
            expected_reply_reason=None,
            current_goal=None,
        ),
    )

    assert decision.meta["degrade_path"] is True
    assert decision.meta["reason_code"] == "planner:missing_semantic_owner"
    assert decision.intent == "system_control"
    assert decision.interaction.owner == "semantic_owner_guard"
    assert decision.source == "planner_control"
    assert decision.meta["control_label"] == "planner_missing_semantic_owner"
    assert decision.meta["missing_semantic_owner_guard"] == {
        "reason_code": "missing_semantic_owner",
        "source": "llm_policy_core",
        "outcome": "COLLECT",
        "action": "collect",
        "tool_action": "collect",
        "synthetic_policy_decision": True,
    }
    assert override is not None
    assert override.reason_code == "planner:missing_semantic_owner"
    assert override.meta["missing_semantic_owner_guard"]["source"] == "llm_policy_core"


def test_consultant_runtime_plan_turn_degrades_owner_backed_decision_without_binding_plan() -> None:
    runtime = ConsultantRuntime()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "goal": "booking",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        }
    )
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "goal": "booking",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="fill_requested_slot",
        source="llm_policy_core",
    )
    decision.semantic_decision = semantic_decision
    decision.binding_plan = None

    runtime.planner.plan = lambda **_kwargs: decision
    runtime._build_memory_summary = lambda *_args, **_kwargs: "user: test"

    planned, override = runtime._plan_turn(
        db=None,
        payload=SimpleNamespace(
            client_slug="demo_salon",
            body=SimpleNamespace(message="Хочу записаться."),
        ),
        prepared=SimpleNamespace(
            conversation=SimpleNamespace(state="bot_active"),
            branch_id=uuid4(),
        ),
        runtime_state=SimpleNamespace(
            dialog_state=DialogState.model_validate(_dialog_state_payload()),
            booking_state={},
            expected_reply_type=None,
            expected_reply_reason=None,
            current_goal=None,
        ),
    )

    assert planned.meta["degrade_path"] is True
    assert planned.meta["reason_code"] == "planner:missing_binding_plan"
    assert planned.intent == "system_control"
    assert planned.source == "planner_control"
    assert planned.meta["control_label"] == "planner_missing_binding_plan"
    assert planned.meta["missing_binding_plan_guard"] == {
        "reason_code": "missing_binding_plan",
        "semantic_decision_id": semantic_decision.decision_id,
        "tool_action": "collect",
        "source": "llm_policy_core",
    }
    assert override is not None
    assert override.reason_code == "planner:missing_binding_plan"


def test_consultant_runtime_plan_turn_invalid_outcome_degrades_with_explicit_override() -> None:
    runtime = ConsultantRuntime()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "goal": "booking",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        }
    )
    decision = TurnPlanner().build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        interaction_owner="llm_policy_core_booking",
        source="llm_policy_core",
    )
    decision.outcome = "UNSUPPORTED"

    runtime.planner.plan = lambda **_kwargs: decision
    runtime._build_memory_summary = lambda *_args, **_kwargs: "user: test"

    planned, override = runtime._plan_turn(
        db=None,
        payload=SimpleNamespace(
            client_slug="demo_salon",
            body=SimpleNamespace(message="Хочу записаться."),
        ),
        prepared=SimpleNamespace(
            conversation=SimpleNamespace(state="bot_active"),
            branch_id=uuid4(),
        ),
        runtime_state=SimpleNamespace(
            dialog_state=DialogState.model_validate(_dialog_state_payload()),
            booking_state={},
            expected_reply_type=None,
            expected_reply_reason=None,
            current_goal=None,
        ),
    )

    assert planned.meta["degrade_path"] is True
    assert planned.meta["reason_code"] == "planner:invalid_outcome"
    assert planned.intent == "system_control"
    assert planned.interaction.owner == "turn_planner"
    assert planned.source == "planner_control"
    assert planned.meta["control_label"] == "planner_invalid_outcome"
    assert override is not None
    assert override.reason_code == "planner:invalid_outcome"
    assert override.meta == {
        "activate_handoff": True,
        "reply_kind": "handoff",
        "degrade_stage": "planner",
    }


def test_consultant_runtime_plan_turn_preserves_explicit_boundary_handoff_on_existing_degrade_path() -> None:
    runtime = ConsultantRuntime()
    decision = TurnPlanner().build_controlled_degrade(
        reason_code="planner:existing_degrade",
        control_label="planner_existing_degrade",
        interaction_owner="turn_planner",
    )

    runtime.planner.plan = lambda **_kwargs: decision
    runtime._build_memory_summary = lambda *_args, **_kwargs: "user: test"

    planned, override = runtime._plan_turn(
        db=None,
        payload=SimpleNamespace(
            client_slug="demo_salon",
            body=SimpleNamespace(message="Что-то пошло не так."),
        ),
        prepared=SimpleNamespace(
            conversation=SimpleNamespace(state="bot_active"),
            branch_id=uuid4(),
        ),
        runtime_state=SimpleNamespace(
            dialog_state=DialogState.model_validate(_dialog_state_payload()),
            booking_state={},
            expected_reply_type=None,
            expected_reply_reason=None,
            current_goal=None,
        ),
    )

    assert planned.meta["degrade_path"] is True
    assert planned.meta["reason_code"] == "planner:existing_degrade"
    assert override is not None
    assert override.reason_code == "planner:existing_degrade"
    assert override.meta == {
        "activate_handoff": True,
        "reply_kind": "handoff",
        "degrade_stage": "planner",
    }


@pytest.mark.parametrize(
    ("mutation_kind", "expected_diff_key"),
    [
        ("intent", "intent"),
        ("interaction_target", "interaction.target"),
        ("shadow_pending_question", "pending_question_contract"),
        ("shadow_semantic_frame", "semantic_frame"),
        ("shadow_semantic_contract", "meta.semantic_contract"),
    ],
)
def test_consultant_runtime_plan_turn_degrades_on_post_owner_semantic_mutation(
    mutation_kind: str,
    expected_diff_key: str,
) -> None:
    runtime = ConsultantRuntime()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "goal": "booking",
            "slots": {"service": "Маникюр"},
            "capability": "booking_manage",
            "subject_kind": "booking",
            "resolution_mode": "ask_about_requested_slot",
            "expected_reply_type": "time",
            "reason": "collect:datetime",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        }
    )
    decision = TurnPlanner().build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        interaction_owner="llm_policy_core_booking",
        source="llm_policy_core",
    )
    if mutation_kind == "intent":
        decision.intent = "hours"
    elif mutation_kind == "interaction_target":
        decision.interaction.target = "service"
    elif mutation_kind == "shadow_pending_question":
        decision.pending_question_contract = PendingQuestionContract(
            expected_reply_type="time",
            next_question="datetime",
            open_questions=["datetime"],
        )
    elif mutation_kind == "shadow_semantic_frame":
        decision.semantic_frame = SemanticFrame(
            user_goal="booking",
            requested_effect="commit_booking",
            subject={"kind": "service", "value": "Маникюр"},
        )
    elif mutation_kind == "shadow_semantic_contract":
        decision.meta["semantic_contract"] = {
            "contract_version": "semantic_contract.v1",
            "capability": "booking_manage",
            "subject_kind": "service",
        }
    else:
        raise AssertionError(f"unsupported mutation_kind: {mutation_kind}")

    runtime.planner.plan = lambda **_kwargs: decision
    runtime._build_memory_summary = lambda *_args, **_kwargs: "user: test"

    planned, override = runtime._plan_turn(
        db=None,
        payload=SimpleNamespace(
            client_slug="demo_salon",
            body=SimpleNamespace(message="Хочу записаться."),
        ),
        prepared=SimpleNamespace(
            conversation=SimpleNamespace(state="bot_active"),
            branch_id=uuid4(),
        ),
        runtime_state=SimpleNamespace(
            dialog_state=DialogState.model_validate(_dialog_state_payload()),
            booking_state={},
            expected_reply_type=None,
            expected_reply_reason=None,
            current_goal=None,
        ),
    )

    assert planned.meta["degrade_path"] is True
    assert planned.meta["reason_code"] == "planner:semantic_decision_post_owner_mutation"
    assert planned.intent == "system_control"
    assert planned.interaction.owner == "semantic_decision_guard"
    assert planned.source == "planner_control"
    assert planned.meta["control_label"] == "planner_semantic_decision_guard"
    mutation_guard = planned.meta["semantic_mutation_guard"]
    assert mutation_guard["reason_code"] == "semantic_decision_post_owner_mutation"
    assert mutation_guard["semantic_decision_id"] == semantic_decision.decision_id
    assert expected_diff_key in mutation_guard["diffs"]
    assert override is not None
    assert override.reason_code == "planner:semantic_decision_post_owner_mutation"
    assert override.meta["semantic_mutation_guard"]["reason_code"] == "semantic_decision_post_owner_mutation"
    assert expected_diff_key in override.meta["semantic_mutation_guard"]["diffs"]


def _build_boundary_turn_result(
    *,
    decision: PolicyDecision,
    override: BoundaryOverride,
    contract_status: str,
    text: str,
):
    state = DialogState.model_validate(_dialog_state_payload())
    reply = ResponseRealizer().realize(decision, override=override, text=text)
    executor = TurnExecutor()
    if contract_status == "blocked":
        return executor.build_block_boundary_turn_result(
            decision=decision,
            dialog_state=state,
            reply=reply,
            boundary_override=override,
        )
    if contract_status == "degraded":
        return executor.build_degrade_boundary_turn_result(
            decision=decision,
            dialog_state=state,
            reply=reply,
            boundary_override=override,
        )
    raise ValueError(f"unsupported_contract_status:{contract_status}")


def _build_boundary_artifact(
    *,
    decision: PolicyDecision,
    override: BoundaryOverride,
    contract_status: str,
    text: str,
    tool_action: str,
    ignored: bool = False,
):
    state = DialogState.model_validate(_dialog_state_payload())
    executor = TurnExecutor()
    if contract_status == "blocked":
        return executor.build_block_boundary_artifact(
            decision=decision,
            dialog_state=state,
            boundary_override=override,
            tool_action=tool_action,
            text=text,
            ignored=ignored,
        )
    if contract_status == "degraded":
        return executor.build_degrade_boundary_artifact(
            decision=decision,
            dialog_state=state,
            boundary_override=override,
            text=text,
            transport_status="failed",
            transport_reason="fallback_send_failed",
    )
    raise ValueError(f"unsupported_contract_status:{contract_status}")


def _build_owner_cutover_artifact(
    *,
    decision: PolicyDecision,
    action: str = "reply",
):
    state = DialogState.model_validate(_dialog_state_payload())
    return TurnExecutor().build_owner_cutover_artifact(
        decision=decision,
        dialog_state=state,
        text="Подберите, пожалуйста, удобное время.",
        owner_cutover="turn_planner.safe_owner_cutover.v1",
        transport_status="delivered",
        transport_reason=None,
        downstream_tool_decision="service_match",
        followup_type="time",
        followup_reason="booking_prompt",
        reason_code="service_match",
        stages=["ingress", "turn_planner", "executor", "realizer", "owner_cutover"],
        action=action,
        source="consultant_core_runtime",
    )


def test_runtime_contract_schemas_validate_example_payloads() -> None:
    _load_schema("contracts/runtime/binding_plan.v1.jsonschema").validate(_binding_plan_payload())
    _load_schema("contracts/runtime/fact_manifest.v1.jsonschema").validate(_fact_manifest_payload())
    _load_schema("contracts/runtime/fact_request.v1.jsonschema").validate(_fact_request_payload())
    _load_schema("contracts/runtime/fact_plan.v1.jsonschema").validate(_fact_plan_payload())
    _load_schema("contracts/runtime/fact_result.v1.jsonschema").validate(_fact_result_payload())
    _load_schema("contracts/runtime/fact_contract.v1.jsonschema").validate(_fact_contract_payload())
    _load_schema("contracts/runtime/policy_decision.v1.jsonschema").validate(_policy_payload())
    _load_schema("contracts/runtime/dialog_state.v1.jsonschema").validate(_dialog_state_payload())
    _load_schema("contracts/runtime/boundary_override.v1.jsonschema").validate(_boundary_override_payload())
    _load_schema("contracts/runtime/turn_result.v1.jsonschema").validate(_turn_result_payload())


def test_fact_plane_contract_models_validate_scope_chain() -> None:
    fact_manifest = FactManifestV1.model_validate(_fact_manifest_payload())
    fact_request = FactRequestV1.model_validate(_fact_request_payload())
    fact_plan = FactPlanV1.model_validate(_fact_plan_payload())
    fact_result = FactResultV1.model_validate(_fact_result_payload())
    fact_contract = FactContractV1.model_validate(_fact_contract_payload())

    assert fact_manifest.manifest_id == "default_fact_manifest.v1"
    assert fact_request.requested_fact_refs == ["pricing"]
    assert fact_request.composition_mode == "single_only"
    assert fact_plan.allowed_emitted_fact_refs == ["pricing"]
    assert fact_plan.allowed_emitted_sets == [["pricing"]]
    assert fact_plan.allowed_info_sections == ["pricing"]
    assert fact_result.emitted_fact_refs == ["pricing"]
    assert fact_result.selected_source == "tool_registry"
    assert fact_result.scope_verdict == "ok"
    assert fact_contract.plan.allowed_emitted_sets == [["pricing"]]


def test_fact_result_contract_rejects_ok_verdict_with_out_of_scope_refs() -> None:
    with pytest.raises(PydanticValidationError):
        FactResultV1.model_validate(
            _fact_result_payload()
            | {
                "scope_verdict": "ok",
                "out_of_scope_fact_refs": ["promotions"],
            }
        )


def test_fact_result_contract_marks_unplanned_bundle_as_out_of_scope() -> None:
    fact_plan = FactPlanV1.model_validate(
        _fact_plan_payload()
        | {
            "allowed_emitted_sets": [["location", "hours"]],
            "allowed_emitted_fact_refs": ["location", "hours"],
            "allowed_emitted_scopes": ["info.location", "info.hours"],
            "bundle_policy": "location_base_bundle",
            "renderer_id": "catalog.location.reply",
        }
    )

    fact_result = FactResultV1.build_from_runtime_payload(
        fact_plan,
        resolution_source="tool_registry",
        response_text="Есть парковка и работаем до 22:00.",
        meta={"info_sections": ["hours"]},
    )

    assert fact_result.scope_verdict == "out_of_scope"
    assert fact_result.out_of_scope_fact_refs == ["hours"]


def test_fact_plan_materializes_location_base_bundle_authority() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "parking",
            "action": "fact",
            "tool_action": "catalog.location",
            "fact_refs": ["parking"],
            "reason": "parking_question",
            "goal": "info",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    fact_request = FactRequestV1.build_from_policy_decision(decision)
    fact_plan = FactPlanV1.build_from_request(fact_request, decision=decision)

    assert fact_request.requested_fact_refs == ["parking"]
    assert fact_request.composition_mode == "companion_allowed"
    assert fact_plan.bundle_policy == "location_base_bundle"
    assert fact_plan.allowed_emitted_sets == [["parking"]]
    assert fact_plan.allowed_emitted_fact_refs == ["parking"]
    assert fact_plan.allowed_emitted_scopes == ["info.parking"]


def test_policy_decision_schema_requires_binding_plan_for_semantic_decision() -> None:
    payload = _policy_payload() | {
        "semantic_decision": build_test_semantic_decision_payload(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action_hint": "collect",
                "goal": "booking",
                "next_question": "datetime",
                "open_questions": ["datetime"],
            }
        ),
        "binding_plan": None,
    }

    with pytest.raises(ValidationError):
        _load_schema("contracts/runtime/policy_decision.v1.jsonschema").validate(payload)


def test_policy_decision_schema_requires_binding_plan_for_synthetic_decision() -> None:
    payload = _policy_payload() | {
        "meta": {"synthetic_policy_decision": True, "reason_code": "missing_remote_jid"},
        "binding_plan": None,
    }

    with pytest.raises(ValidationError):
        _load_schema("contracts/runtime/policy_decision.v1.jsonschema").validate(payload)


def test_policy_decision_model_requires_binding_plan_for_semantic_decision() -> None:
    payload = _policy_payload() | {
        "semantic_decision": build_test_semantic_decision_payload(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action_hint": "collect",
                "goal": "booking",
                "next_question": "datetime",
                "open_questions": ["datetime"],
            }
        ),
        "binding_plan": None,
    }

    with pytest.raises(PydanticValidationError, match="binding_plan_required_for_semantic_decision"):
        PolicyDecision.model_validate(payload)


def test_policy_decision_model_requires_binding_plan_for_synthetic_decision() -> None:
    payload = _policy_payload() | {
        "meta": {"synthetic_policy_decision": True, "reason_code": "missing_remote_jid"},
        "binding_plan": None,
    }

    with pytest.raises(PydanticValidationError, match="binding_plan_required_for_synthetic_decision"):
        PolicyDecision.model_validate(payload)


def test_runtime_core_scaffolding_round_trips_contract_payloads() -> None:
    planner = TurnPlanner()
    decision = planner.coerce(_policy_payload())
    assert isinstance(decision, PolicyDecision)
    assert decision.interaction.owner == "booking_time_followup"

    state = DialogState.model_validate(_dialog_state_payload())
    override = BoundaryOverride.model_validate(_boundary_override_payload())
    reply = ResponseRealizer().realize(decision, override=override, text=override.public_message or "")
    result = TurnExecutor().assemble(
        decision=decision,
        dialog_state=state,
        reply=reply,
        boundary_override=override,
        contract_status="degraded",
        reason_code="policy_timeout",
        stages=["planner", "boundary", "executor", "realizer"],
    )

    assert result.schema_version == "turn_result.v1"
    assert result.contract_status == "degraded"
    assert result.dialog_state.interaction_state.interaction_owner == "booking_time_followup"
    assert result.reply.reply_kind == "handoff"


def test_turn_planner_builds_binding_plan_for_owner_backed_decision() -> None:
    planner = TurnPlanner()
    semantic_payload = build_test_semantic_decision_payload(
        {
            "intent": "promotions",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "reason": "promo_question",
            "subject_kind": "service",
            "capability": "promotions",
            "resolution_mode": "policy_fact",
            "slots": {"service": "Маникюр"},
        }
    )

    decision = planner._build_policy_core_decision(
        semantic_payload,
        binding_plan_payload=_binding_plan_payload() | {"decision_id": semantic_payload["decision_id"]},
    )

    assert decision.binding_plan is not None
    assert decision.binding_plan.selected_tool_or_workflow_ref == "catalog.service_query"
    assert decision.binding_plan.decision_id == decision.semantic_decision.decision_id
    assert decision.binding_plan.binding_outcome_type == "tool_call"
    assert decision.tool_action == "catalog.service_query"
    assert decision.tool_args == {"service_query": "manicure"}


def test_policy_tool_projector_uses_snapshot_owner_for_info_ref_mapping(monkeypatch) -> None:
    semantic_payload = build_test_semantic_decision_payload(
        {
            "intent": "custom_info",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["custom_info"],
            "reason": "custom_info_question",
            "subject_kind": "service",
            "capability": "custom_info",
            "resolution_mode": "policy_fact",
            "slots": {"service": "Маникюр"},
        }
    )

    monkeypatch.setattr(
        "app.core.policy_tool_projector.resolve_policy_info_tool_action",
        lambda info_ref: "catalog.portfolio" if info_ref == "custom_info" else None,
    )

    binding_plan, projection_trace, error = build_binding_plan(
        semantic_decision=semantic_payload,
        allowed_tool_actions={"catalog.portfolio"},
    )

    assert error is None
    assert binding_plan is not None
    assert binding_plan.selected_tool_or_workflow_ref == "catalog.portfolio"
    assert projection_trace == {
        "status": "ok",
        "projection_source": "policy_tool_projector",
        "tool_action_hint": "info",
        "tool_action": "catalog.portfolio",
        "tool_args": {"service_query": "Маникюр"},
    }


def test_policy_tool_projector_normalizes_collect_context_hint_to_collect_binding() -> None:
    semantic_payload = build_test_semantic_decision_payload(
        {
            "intent": "check_booking",
            "action": "collect",
            "tool_action_hint": "calendar.get_booking",
            "reason": "calendar_get_booking_collect_reference",
            "subject_kind": "booking",
            "capability": "booking_manage",
            "resolution_mode": "direct",
            "next_question": "name",
            "open_questions": ["name"],
        }
    )

    binding_plan, projection_trace, error = build_binding_plan(
        semantic_decision=semantic_payload,
        allowed_tool_actions={"collect", "calendar.get_booking"},
    )

    assert error is None
    assert binding_plan is not None
    assert binding_plan.binding_outcome_type == "workflow_advance"
    assert binding_plan.selected_tool_or_workflow_ref == "collect"
    assert projection_trace == {
        "status": "ok",
        "projection_source": "policy_tool_projector",
        "tool_action_hint": "calendar.get_booking",
        "tool_action": "collect",
        "collect_context_hint": "calendar.get_booking",
    }


def test_turn_planner_rejects_binding_plan_outcome_conflict() -> None:
    planner = TurnPlanner()
    semantic_payload = build_test_semantic_decision_payload(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "calendar.list_slots",
            "reason": "collect:datetime",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "policy_collect",
            "slots": {"service": "Маникюр"},
            "next_question": "datetime",
            "open_questions": ["datetime"],
        }
    )

    with pytest.raises(ValueError, match="binding_outcome_conflict"):
        planner._build_policy_core_decision(
            semantic_payload,
            binding_plan_payload=_binding_plan_payload()
            | {
                "decision_id": semantic_payload["decision_id"],
                "binding_outcome_type": "tool_call",
                "selected_tool_or_workflow_ref": "calendar.list_slots",
                "capability_id": "bookability",
                "resolved_args": {"service_query": "Маникюр"},
            },
        )


def test_test_support_builds_policy_decision_from_policy_override_payload() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "contact",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": ["contact"],
            "reason": "contact_question",
            "goal": "info",
            "needs_manager": False,
            "confidence": 0.95,
        },
        interaction_owner="turn_planner.safe_info_fact.v1",
        interaction_relation="turn_planner_safe_info_fact",
    )

    _load_schema("contracts/runtime/policy_decision.v1.jsonschema").validate(
        decision.model_dump(mode="json")
    )
    assert decision.outcome == "FACT"
    assert decision.intent == "contact"
    assert decision.tool_action == "info"
    assert decision.pack_refs == ["contact"]
    assert decision.interaction.owner == "turn_planner.safe_info_fact.v1"
    assert decision.meta["reason"] == "contact_question"


def test_turn_planner_preserves_policy_core_followup_contract_for_fact_action() -> None:
    planner = TurnPlanner()

    decision = planner._build_policy_core_decision(
        build_test_semantic_decision_payload(
            {
                "intent": "duration",
                "action": "fact",
                "tool_action": "catalog.service_query",
                "reason": "collect:name",
                "subject_kind": "service",
                "capability": "duration",
                "resolution_mode": "policy_fact",
                "expected_reply_type": "name",
                "next_question": "name",
                "open_questions": ["name"],
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "generic_info_interrupt",
            }
        ),
        binding_payload={"tool_action": "catalog.service_query", "tool_args": {}},
    )

    pending_question = planner.canonical_pending_question_contract(decision)

    assert decision.outcome == "FACT"
    assert decision.pending_question_contract.model_dump(mode="python", exclude_none=True) == {
        "open_questions": []
    }
    assert pending_question.expected_reply_type == "name"
    assert pending_question.reason == "collect:name"
    assert pending_question.pending_question_act == "ask_about_requested_slot"
    assert pending_question.pending_question_target == "time"
    assert pending_question.active_question_relation == "generic_info_interrupt"
    assert pending_question.next_question == "name"
    assert pending_question.open_questions == ["name"]


def test_turn_planner_rejects_legacy_policy_shape_payload_for_policy_core_decision() -> None:
    planner = TurnPlanner()

    with pytest.raises(ValueError, match="semantic_decision_required"):
        planner._build_policy_core_decision(
            {
                "intent": "duration",
                "action": "fact",
                "tool_action": "catalog.service_query",
                "expected_reply_type": "name",
            },
            binding_payload={"tool_action": "catalog.service_query", "tool_args": {}},
        )


def test_turn_planner_detects_owner_adjacent_shadow_carrier_mutation() -> None:
    planner = TurnPlanner()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "calendar.book_slot",
            "goal": "booking",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "policy_collect",
            "slots": {"service": "Маникюр"},
            "expected_reply_type": "name",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "fill_requested_slot",
            "next_question": "name",
            "open_questions": ["name"],
        }
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="calendar.book_slot",
        interaction_owner="llm_policy_core",
        source="policy_core",
    )
    decision.pending_question_contract = PendingQuestionContract(
        expected_reply_type="name",
        next_question="name",
        open_questions=["name"],
    )
    decision.semantic_frame = SemanticFrame(
        user_goal="booking",
        requested_effect="commit_booking",
        continuation={"next_question": "name"},
    )
    decision.meta["semantic_contract"] = {
        "contract_version": "semantic_contract.v1",
        "capability": "bookability",
    }

    mutation = planner.detect_semantic_mutation(decision)

    assert mutation is not None
    assert mutation["reason_code"] == "semantic_decision_post_owner_mutation"
    assert mutation["diffs"]["pending_question_contract"]["expected"] == {"open_questions": []}
    assert mutation["diffs"]["semantic_frame"]["expected"] == {
        "schema_version": "semantic_frame.v2",
        "subject": {},
        "referents": {},
        "constraints": {},
        "preferences": {},
        "continuation": {},
        "capability_selection": {},
        "needs_human": False,
    }
    assert mutation["diffs"]["meta.semantic_contract"]["expected"] == {}


def test_turn_planner_builds_shadow_only_owner_adjacent_carriers_for_semantic_decision() -> None:
    planner = TurnPlanner()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "booking",
            "action": "fact",
            "tool_action": "calendar.book_slot",
            "tool_action_hint": "calendar.book_slot",
            "goal": "booking",
            "reason": "final_name_collected",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "direct",
            "temporal_scope": "specific_time",
            "slots": {
                "service": "Маникюр",
                "datetime": "2026-03-27T15:00:00+05:00",
                "name": "Алина",
            },
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "memory",
                }
            },
            "entity_refs": [
                {
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "value": "Маникюр",
                    "source_ref": "memory",
                }
            ],
            "expected_reply_type": "name",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "fill_requested_slot",
            "next_question": "name",
            "open_questions": ["name"],
        }
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="calendar.book_slot",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    canonical_frame = planner.canonical_semantic_frame(decision)
    canonical_contract = planner.canonical_semantic_contract(decision)

    assert decision.semantic_frame.model_dump(mode="python", exclude_none=True) == {
        "schema_version": "semantic_frame.v2",
        "subject": {},
        "referents": {},
        "constraints": {},
        "preferences": {},
        "continuation": {},
        "capability_selection": {},
        "needs_human": False,
    }
    assert decision.pending_question_contract.model_dump(mode="python", exclude_none=True) == {
        "open_questions": []
    }
    assert "semantic_contract" not in decision.meta
    assert canonical_frame.subject["kind"] == "service"
    assert canonical_frame.continuation["next_question"] == "name"
    assert canonical_contract["capability"] == "bookability"


def test_policy_decision_schema_rejects_owner_backed_populated_shadow_carriers() -> None:
    planner = TurnPlanner()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "goal": "booking",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "policy_collect",
            "slots": {"service": "Маникюр"},
            "expected_reply_type": "time",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        }
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )
    decision.pending_question_contract = PendingQuestionContract(
        expected_reply_type="time",
        next_question="datetime",
        open_questions=["datetime"],
    )
    decision.meta["semantic_contract"] = {
        "contract_version": "semantic_contract.v1",
        "capability": "bookability",
    }

    with pytest.raises(ValidationError):
        _load_schema("contracts/runtime/policy_decision.v1.jsonschema").validate(
            decision.model_dump(mode="json")
        )


def test_policy_decision_schema_rejects_owner_backed_meta_semantic_contract_only() -> None:
    planner = TurnPlanner()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "goal": "booking",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "policy_collect",
            "slots": {"service": "Маникюр"},
            "expected_reply_type": "time",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        }
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )
    decision.meta["semantic_contract"] = {
        "contract_version": "semantic_contract.v1",
        "capability": "bookability",
        "subject_kind": "service",
    }

    with pytest.raises(ValidationError):
        _load_schema("contracts/runtime/policy_decision.v1.jsonschema").validate(
            decision.model_dump(mode="json")
        )


def test_policy_decision_schema_rejects_owner_backed_populated_semantic_frame() -> None:
    planner = TurnPlanner()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "goal": "booking",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "policy_collect",
            "slots": {"service": "Маникюр"},
            "expected_reply_type": "time",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        }
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )
    decision.semantic_frame = SemanticFrame(
        user_goal="booking",
        requested_effect="collect_missing_input",
        continuation={"next_question": "datetime"},
    )

    with pytest.raises(ValidationError):
        _load_schema("contracts/runtime/policy_decision.v1.jsonschema").validate(
            decision.model_dump(mode="json")
        )


def test_boundary_validator_builds_typed_block_override() -> None:
    boundary = BoundaryValidator()

    override = boundary.build_block_override(
        reason_code="missing_remote_jid",
        trace_message="reasoning_core blocked inbound without metadata.remoteJid",
        replan_hints=["require metadata.remoteJid"],
        meta={"source": "reasoning_core"},
    )

    _load_schema("contracts/runtime/boundary_override.v1.jsonschema").validate(
        override.model_dump(mode="json")
    )
    assert override.decision == "block"
    assert override.reason_code == "missing_remote_jid"
    assert override.preserve_fields == [
        "outcome",
        "interaction_owner",
        "interaction_target",
        "interaction_relation",
        "pending_question_contract",
    ]
    assert override.replan_hints == ["require metadata.remoteJid"]


def test_boundary_validator_strips_semantic_meta_from_override() -> None:
    boundary = BoundaryValidator()

    override = boundary.build_degrade_override(
        reason_code="runtime_exception",
        public_message="Fallback response skipped",
        trace_message="reasoning_core exception degraded through new core",
        meta={
            "reply_kind": "handoff",
            "activate_handoff": True,
            "semantic_contract": {"capability": "duration"},
            "pending_question_contract": {"expected_reply_type": "time"},
            "tool_args": {"service_query": "Маникюр"},
        },
    )

    assert override.meta == {
        "reply_kind": "handoff",
        "activate_handoff": True,
    }


def test_boundary_validator_strips_non_boundary_reply_kind_override() -> None:
    boundary = BoundaryValidator()

    override = boundary.build_degrade_override(
        reason_code="runtime_exception",
        public_message="Fallback response skipped",
        trace_message="reasoning_core exception degraded through new core",
        meta={
            "reply_kind": "fact",
            "activate_handoff": True,
        },
    )

    assert override.meta == {
        "activate_handoff": True,
    }


def test_boundary_validator_validate_normalizes_override_surface() -> None:
    boundary = BoundaryValidator()
    decision = TurnPlanner().build_controlled_degrade(
        reason_code="runtime_exception",
        control_label="runtime_error",
        interaction_owner="reasoning_core_exception_degrade",
        interaction_relation="runtime_exception",
    )
    override = BoundaryOverride.model_validate(
        {
            "decision": "degrade",
            "reason_code": "runtime_exception",
            "preserve_fields": ["outcome", "tool_args", "outcome"],
            "meta": {
                "reply_kind": "handoff",
                "semantic_contract": {"capability": "duration"},
            },
        }
    )

    validated = boundary.validate(decision, override=override)

    assert validated.override is not None
    assert validated.override.preserve_fields == ["outcome"]
    assert validated.override.meta == {"reply_kind": "handoff"}


def test_turn_executor_builds_typed_block_boundary_turn_result() -> None:
    planner = TurnPlanner()
    boundary = BoundaryValidator()
    decision = planner.build_preflight_reject(
        reason_code="missing_remote_jid",
        control_label="missing_remote_jid",
        interaction_owner="reasoning_core_missing_remote_jid",
        interaction_relation="missing_remote_jid",
    )
    override = boundary.build_block_override(
        reason_code="missing_remote_jid",
        trace_message="reasoning_core blocked inbound without metadata.remoteJid",
        replan_hints=["require metadata.remoteJid"],
        meta={"source": "reasoning_core"},
    )
    state = DialogState.model_validate(_dialog_state_payload())
    reply = ResponseRealizer().realize(decision, override=override, text="")

    turn_result = TurnExecutor().build_block_boundary_turn_result(
        decision=decision,
        dialog_state=state,
        reply=reply,
        boundary_override=override,
    )

    assert decision.binding_plan is not None
    assert decision.binding_plan.binding_outcome_type == "deny"
    assert decision.binding_plan.deny_reason_code == "missing_remote_jid"
    assert turn_result.contract_status == "blocked"
    assert turn_result.boundary_override is not None
    assert turn_result.boundary_override.reason_code == "missing_remote_jid"
    assert turn_result.observability.reason_code == "missing_remote_jid"
    assert turn_result.trace.stages == ["ingress", "planner", "boundary", "executor", "realizer"]


def test_turn_executor_builds_typed_degrade_boundary_turn_result() -> None:
    planner = TurnPlanner()
    boundary = BoundaryValidator()
    decision = planner.build_controlled_degrade(
        reason_code="runtime_exception",
        control_label="runtime_error",
        interaction_owner="reasoning_core_exception_degrade",
        interaction_relation="runtime_exception",
    )
    override = boundary.build_degrade_override(
        reason_code="runtime_exception",
        public_message="Fallback response skipped",
        trace_message="reasoning_core exception degraded through new core",
        meta={"source": "reasoning_core"},
    )
    state = DialogState.model_validate(_dialog_state_payload())
    reply = ResponseRealizer().realize(decision, override=override, text="Fallback response skipped")

    turn_result = TurnExecutor().build_degrade_boundary_turn_result(
        decision=decision,
        dialog_state=state,
        reply=reply,
        boundary_override=override,
    )

    assert decision.binding_plan is not None
    assert decision.binding_plan.binding_outcome_type == "degrade"
    assert decision.binding_plan.degrade_reason_code == "runtime_exception"
    assert turn_result.contract_status == "degraded"
    assert turn_result.boundary_override is not None
    assert turn_result.boundary_override.reason_code == "runtime_exception"
    assert turn_result.observability.reason_code == "runtime_exception"
    assert turn_result.trace.stages == [
        "planner",
        "boundary",
        "executor",
        "realizer",
        "reasoning_core_exception",
    ]


def test_turn_executor_builds_typed_block_boundary_artifact() -> None:
    planner = TurnPlanner()
    boundary = BoundaryValidator()
    decision = planner.build_preflight_reject(
        reason_code="missing_remote_jid",
        control_label="missing_remote_jid",
        interaction_owner="reasoning_core_missing_remote_jid",
        interaction_relation="missing_remote_jid",
    )
    override = boundary.build_block_override(
        reason_code="missing_remote_jid",
        trace_message="reasoning_core blocked inbound without metadata.remoteJid",
        replan_hints=["require metadata.remoteJid"],
        meta={"source": "reasoning_core"},
    )

    artifact = _build_boundary_artifact(
        decision=decision,
        override=override,
        contract_status="blocked",
        text="",
        tool_action="preflight.missing_remote_jid",
    )

    assert artifact.turn_result.contract_status == "blocked"
    assert artifact.turn_result.observability.reason_code == "missing_remote_jid"
    assert artifact.turn_outcome.action == "reject"
    assert artifact.turn_outcome.tool_action == "preflight.missing_remote_jid"
    assert artifact.turn_outcome.meta["preflight_path"] is True


def test_turn_executor_builds_typed_degrade_boundary_artifact() -> None:
    planner = TurnPlanner()
    boundary = BoundaryValidator()
    decision = planner.build_controlled_degrade(
        reason_code="runtime_exception",
        control_label="runtime_error",
        interaction_owner="reasoning_core_exception_degrade",
        interaction_relation="runtime_exception",
    )
    override = boundary.build_degrade_override(
        reason_code="runtime_exception",
        public_message="Fallback response skipped",
        trace_message="reasoning_core exception degraded through new core",
        meta={"source": "reasoning_core"},
    )

    artifact = _build_boundary_artifact(
        decision=decision,
        override=override,
        contract_status="degraded",
        text="Fallback response skipped",
        tool_action="handoff",
    )

    assert artifact.turn_result.contract_status == "degraded"
    assert artifact.turn_result.observability.reason_code == "runtime_exception"
    assert artifact.turn_outcome.action == "handoff"
    assert artifact.turn_outcome.tool_action == "handoff"
    assert artifact.turn_outcome.meta["degrade_path"] is True
    assert artifact.turn_outcome.observability.transport_reason == "fallback_send_failed"


def test_turn_executor_builds_typed_block_boundary_artifact_from_request() -> None:
    artifact = TurnExecutor().build_block_boundary_artifact_from_request(
        request=BlockBoundaryRequest(
            reason_code="missing_remote_jid",
            intent="missing_remote_jid",
            interaction_owner="reasoning_core_missing_remote_jid",
            interaction_relation="missing_remote_jid",
            trace_message="reasoning_core blocked inbound without metadata.remoteJid",
            replan_hints=["require metadata.remoteJid"],
            tool_action="preflight.missing_remote_jid",
            override_meta={"source": "reasoning_core"},
        )
    )

    _load_schema("contracts/runtime/turn_result.v1.jsonschema").validate(
        artifact.turn_result.model_dump(mode="json")
    )
    assert artifact.turn_result.contract_status == "blocked"
    assert artifact.turn_result.policy_decision.action == "preflight_reject"
    assert artifact.turn_result.policy_decision.binding_plan is not None
    assert artifact.turn_result.policy_decision.binding_plan.binding_outcome_type == "deny"
    assert artifact.turn_result.policy_decision.binding_plan.deny_reason_code == "missing_remote_jid"
    assert artifact.turn_result.boundary_override is not None
    assert artifact.turn_result.boundary_override.reason_code == "missing_remote_jid"
    assert artifact.turn_result.dialog_state.meta["block_path"] is True
    assert artifact.turn_result.policy_decision.intent == "system_control"
    assert artifact.turn_result.policy_decision.meta["control_label"] == "missing_remote_jid"
    assert artifact.turn_outcome.tool_action == "preflight.missing_remote_jid"
    assert artifact.turn_outcome.meta["preflight_path"] is True
    assert artifact.turn_outcome.meta["control_label"] == "missing_remote_jid"


def test_turn_executor_builds_typed_degrade_boundary_artifact_from_request() -> None:
    artifact = TurnExecutor().build_degrade_boundary_artifact_from_request(
        request=DegradeBoundaryRequest(
            reason_code="runtime_exception",
            intent="runtime_error",
            interaction_owner="reasoning_core_exception_degrade",
            interaction_relation="runtime_exception",
            public_message="Fallback response skipped",
            trace_message="reasoning_core exception degraded through new core",
            transport_status="failed",
            transport_reason="fallback_send_failed",
            override_meta={"source": "reasoning_core"},
        )
    )

    _load_schema("contracts/runtime/turn_result.v1.jsonschema").validate(
        artifact.turn_result.model_dump(mode="json")
    )
    assert artifact.turn_result.contract_status == "degraded"
    assert artifact.turn_result.policy_decision.action == "handoff"
    assert artifact.turn_result.policy_decision.binding_plan is not None
    assert artifact.turn_result.policy_decision.binding_plan.binding_outcome_type == "degrade"
    assert artifact.turn_result.policy_decision.binding_plan.degrade_reason_code == "runtime_exception"
    assert artifact.turn_result.boundary_override is not None
    assert artifact.turn_result.boundary_override.reason_code == "runtime_exception"
    assert artifact.turn_result.dialog_state.meta["degrade_path"] is True
    assert artifact.turn_result.policy_decision.intent == "system_control"
    assert artifact.turn_result.policy_decision.meta["control_label"] == "runtime_error"
    assert artifact.turn_outcome.tool_action == "handoff"
    assert artifact.turn_outcome.meta["degrade_path"] is True
    assert artifact.turn_outcome.meta["control_label"] == "runtime_error"
    assert artifact.turn_outcome.observability.transport_reason == "fallback_send_failed"


def test_turn_executor_builds_typed_owner_cutover_artifact() -> None:
    planner = TurnPlanner()
    decision = planner.coerce(_policy_payload())

    artifact = _build_owner_cutover_artifact(
        decision=decision,
        action="booking_prompt",
    )

    _load_schema("contracts/runtime/turn_result.v1.jsonschema").validate(
        artifact.turn_result.model_dump(mode="json")
    )
    assert artifact.turn_result.contract_status == "ok"
    assert artifact.turn_result.reply.reply_kind == "collect"
    assert artifact.turn_outcome.action == "booking_prompt"
    assert artifact.turn_outcome.intent == "booking"
    assert artifact.turn_outcome.tool_action == "calendar.list_slots"
    assert artifact.turn_outcome.expected_reply_type == "time"
    assert artifact.turn_outcome.expected_reply_reason == "booking_prompt"
    assert artifact.turn_outcome.meta["owner_cutover"] == "turn_planner.safe_owner_cutover.v1"
    assert artifact.turn_outcome.meta["downstream_tool_decision"] == "service_match"
    assert artifact.runtime_meta["owner_cutover"] == "turn_planner.safe_owner_cutover.v1"
    assert artifact.runtime_meta["downstream_tool_decision"] == "service_match"


def test_turn_executor_builds_typed_tool_reply_owner_cutover_artifact() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "service_duration",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "reason": "duration_question",
            "goal": "info",
            "tool_args": {"service_query": "Маникюр"},
            "slots": {"service": "Маникюр"},
            "pack_refs": ["duration"],
        },
        interaction_owner="tool_registry.reply_owner.v1",
        interaction_relation="tool_reply",
    )
    state = DialogState.model_validate(_dialog_state_payload())

    artifact = TurnExecutor().build_owner_cutover_artifact(
        decision=decision,
        dialog_state=state,
        text="Маникюр занимает около 90 минут.",
        owner_cutover="turn_executor.tool_reply_turn_outcome.v1",
        transport_status="failed",
        transport_reason="provider_send_failed",
        downstream_tool_decision="contract_invalid",
        reason_code="duration_question",
        stages=["ingress", "decision", "executor", "realizer", "llm_policy_core_tool"],
        action="reply",
        source="tool_registry",
        intent="service_duration",
        tool_action="catalog.service_query",
        tool_decision="contract_invalid",
        followup_prompt="Если хотите, подскажу свободное время.",
        contract_status="degraded",
        meta={"services_overview_followup": True},
    )

    _load_schema("contracts/runtime/turn_result.v1.jsonschema").validate(
        artifact.turn_result.model_dump(mode="json")
    )
    assert artifact.turn_result.contract_status == "degraded"
    assert artifact.turn_result.reply.reply_kind == "fact"
    assert artifact.turn_outcome.action == "reply"
    assert artifact.turn_outcome.intent == "service_duration"
    assert artifact.turn_outcome.source == "tool_registry"
    assert artifact.turn_outcome.tool_action == "catalog.service_query"
    assert artifact.turn_outcome.tool_decision == "contract_invalid"
    assert artifact.turn_outcome.followup_prompt == "Если хотите, подскажу свободное время."
    assert artifact.turn_outcome.contract_status == "degraded"
    assert artifact.turn_outcome.observability.reply_observed is False
    assert artifact.turn_outcome.observability.transport_status == "failed"
    assert artifact.turn_outcome.observability.transport_reason == "provider_send_failed"
    assert artifact.turn_outcome.meta["owner_cutover"] == "turn_executor.tool_reply_turn_outcome.v1"
    assert artifact.turn_outcome.meta["downstream_tool_decision"] == "contract_invalid"
    assert artifact.turn_outcome.meta["services_overview_followup"] is True
    assert artifact.runtime_meta["owner_cutover"] == "turn_executor.tool_reply_turn_outcome.v1"
    assert artifact.runtime_meta["contract_status"] == "degraded"
    assert artifact.runtime_meta["downstream_tool_decision"] == "contract_invalid"






def test_policy_validation_boundary_fact_guard_uses_owner_primitives() -> None:
    captured: dict[str, object] = {}

    def _record_decision_trace(conversation, payload):
        captured["trace"] = payload

    def _record_message_decision_meta(saved_message, **payload):
        captured["message_meta"] = payload

    def _update_message_decision_metadata(saved_message, payload):
        captured["meta_updates"] = payload

    response = handle_policy_validation_boundary(
        runtime_input=PolicyValidationBoundaryRuntimeInput(
            mode="fact_guard",
            validation_error="missing_fact_payload",
            guard_reason="missing_fact_payload",
            trace_decision="clarify_missing_fact_payload",
            conversation=SimpleNamespace(
                id="00000000-0000-0000-0000-000000000001",
                state="bot_active",
            ),
            saved_message=SimpleNamespace(id="msg-1"),
            now=SimpleNamespace(isoformat=lambda: "2026-03-20T12:00:00+00:00"),
            llm_policy_core_meta=None,
            msg_fact_guard_clarify="Уточните, пожалуйста.",
            trace_source="tool_registry",
            clarify_intent="fact_guard",
            clarify_max_attempts=2,
            fact_source="truth",
            fact_evidence_refs=["hours"],
        ),
        hooks=PolicyValidationBoundaryRuntimeHooks(
            classify_policy_core_degrade_reason=lambda *_args, **_kwargs: None,
            sync_semantic_arbiter_meta=lambda *_args, **_kwargs: None,
            sync_policy_plan_audit=lambda *_args, **_kwargs: None,
            backfill_policy_degraded_referent_evidence=lambda *_args, **_kwargs: None,
            update_message_decision_metadata=_update_message_decision_metadata,
            apply_policy_guard_override=lambda *_args, **_kwargs: None,
            record_decision_trace=_record_decision_trace,
            record_message_decision_meta=_record_message_decision_meta,
            get_conversation_context=lambda *_args, **_kwargs: {"context_manager": {}},
            get_context_manager=lambda context: context.get("context_manager", {}),
            get_clarify_attempt_state=lambda *_args, **_kwargs: (0, None),
            record_context_manager_decision=lambda *_args, **_kwargs: None,
            handle_clarify_limit_escalation=lambda **_kwargs: None,
            register_clarify_attempt=lambda **kwargs: captured.setdefault("attempt", kwargs),
            set_booking_context=lambda context, *_args, **_kwargs: context,
            set_service_hint=lambda context, *_args, **_kwargs: context,
            set_expected_reply_context=lambda **kwargs: kwargs["context"],
            set_conversation_context=lambda *_args, **_kwargs: None,
            expected_reply_for_booking_question=lambda *_args, **_kwargs: None,
            booking_prompt_for_expected_reply_type=lambda *_args, **_kwargs: None,
            reset_low_confidence_retry=lambda conversation: captured.setdefault(
                "retry_reset",
                conversation.id,
            ),
            combine_sidecar=lambda *parts: "\n".join(part for part in parts if part),
            maybe_apply_consult_return=lambda **kwargs: kwargs["bot_response"],
            send_and_save=lambda text: (text, True),
            commit=lambda: captured.setdefault("committed", True),
        ),
    )

    assert response.bot_response == "Уточните, пожалуйста."
    assert captured["attempt"]["intent"] == "fact_guard"
    assert captured["trace"] == {
        "stage": "fact_guard",
        "decision": "clarify_missing_fact_payload",
        "state": "bot_active",
        "fact_source": "truth",
        "fact_guard_reason": "missing_fact_payload",
        "fact_evidence_refs": ["hours"],
        "source": "tool_registry",
    }
    assert captured["message_meta"] == {
        "action": "reply",
        "intent": "fact_guard",
        "source": "fact_guard",
        "fast_intent": False,
    }
    assert captured["meta_updates"] == {
        "clarify_reason": "fact_guard",
        "fact_guard": True,
        "fact_guard_reason": "missing_fact_payload",
        "fact_evidence_refs": ["hours"],
    }
    assert captured["retry_reset"] == "00000000-0000-0000-0000-000000000001"
    assert "committed" not in captured


def test_policy_validation_boundary_fact_guard_escalates_at_limit() -> None:
    captured: dict[str, object] = {}
    sentinel = object()

    def _handle_clarify_limit_escalation(**kwargs):
        captured["escalation"] = kwargs
        return sentinel

    response = handle_policy_validation_boundary(
        runtime_input=PolicyValidationBoundaryRuntimeInput(
            mode="fact_guard",
            validation_error="missing_fact_payload",
            guard_reason="missing_fact_payload",
            trace_decision="clarify_missing_fact_payload",
            conversation=SimpleNamespace(
                id="00000000-0000-0000-0000-000000000002",
                state="bot_active",
            ),
            saved_message=SimpleNamespace(id="msg-1"),
            now=SimpleNamespace(isoformat=lambda: "2026-03-20T12:00:00+00:00"),
            llm_policy_core_meta=None,
            msg_fact_guard_clarify="Уточните, пожалуйста.",
            message_text="Сколько стоит?",
            user=SimpleNamespace(id="user-1"),
            db=SimpleNamespace(),
            allow_handover=True,
            escalation_source="fact_guard",
            clarify_intent="fact_guard",
            clarify_max_attempts=2,
            send_response=lambda *_args, **_kwargs: True,
        ),
        hooks=PolicyValidationBoundaryRuntimeHooks(
            classify_policy_core_degrade_reason=lambda *_args, **_kwargs: None,
            sync_semantic_arbiter_meta=lambda *_args, **_kwargs: None,
            sync_policy_plan_audit=lambda *_args, **_kwargs: None,
            backfill_policy_degraded_referent_evidence=lambda *_args, **_kwargs: None,
            update_message_decision_metadata=lambda *_args, **_kwargs: None,
            apply_policy_guard_override=lambda *_args, **_kwargs: None,
            record_decision_trace=lambda *_args, **_kwargs: None,
            record_message_decision_meta=lambda *_args, **_kwargs: None,
            get_conversation_context=lambda *_args, **_kwargs: {"context_manager": {}},
            get_context_manager=lambda context: context.get("context_manager", {}),
            get_clarify_attempt_state=lambda *_args, **_kwargs: (2, "2026-03-20T12:00:00+00:00"),
            record_context_manager_decision=lambda conversation, saved_message, **payload: captured.setdefault(
                "context_decision",
                payload,
            ),
            handle_clarify_limit_escalation=_handle_clarify_limit_escalation,
            register_clarify_attempt=lambda **kwargs: captured.setdefault("attempt", kwargs),
            set_booking_context=lambda context, *_args, **_kwargs: context,
            set_service_hint=lambda context, *_args, **_kwargs: context,
            set_expected_reply_context=lambda **kwargs: kwargs["context"],
            set_conversation_context=lambda *_args, **_kwargs: None,
            expected_reply_for_booking_question=lambda *_args, **_kwargs: None,
            booking_prompt_for_expected_reply_type=lambda *_args, **_kwargs: None,
            reset_low_confidence_retry=lambda *_args, **_kwargs: None,
            combine_sidecar=lambda *parts: "\n".join(part for part in parts if part),
            maybe_apply_consult_return=lambda **kwargs: kwargs["bot_response"],
            send_and_save=lambda text: (text, True),
            commit=lambda: captured.setdefault("committed", True),
        ),
    )

    assert response is sentinel
    assert captured["context_decision"] == {
        "decision": "clarify_limit",
        "updates": {
            "clarify_attempt": {"intent": "fact_guard", "count": 2},
            "clarify_reason": "fact_guard",
            "clarify_limit": True,
            "fact_guard_reason": "missing_fact_payload",
        },
    }
    assert captured["escalation"]["source"] == "fact_guard"
    assert captured["escalation"]["allow_handover"] is True
    assert "attempt" not in captured
    assert "committed" not in captured



def test_turn_executor_builds_typed_booking_prompt_owner_cutover_artifact() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "reason": "booking_prompt",
            "goal": "booking",
            "slots": {"service": "Маникюр"},
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="turn_planner.safe_booking_prompt_owner.v1",
        interaction_relation="turn_planner_safe_booking_prompt_owner",
    )
    state = DialogState.model_validate(_dialog_state_payload())

    artifact = TurnExecutor().build_owner_cutover_artifact(
        decision=decision,
        dialog_state=state,
        text="Подскажите, пожалуйста, удобные дату и время.",
        owner_cutover="turn_planner.safe_booking_prompt_owner.v1",
        transport_status="delivered",
        transport_reason=None,
        followup_type="time",
        followup_reason="booking_prompt",
        action="booking_prompt",
        source="booking_prompt_owner",
    )

    _load_schema("contracts/runtime/turn_result.v1.jsonschema").validate(
        artifact.turn_result.model_dump(mode="json")
    )
    assert artifact.turn_result.contract_status == "ok"
    assert artifact.turn_result.reply.reply_kind == "collect"
    assert artifact.turn_outcome.action == "booking_prompt"
    assert artifact.turn_outcome.intent == "booking"
    assert artifact.turn_outcome.tool_action == "collect"
    assert artifact.turn_outcome.expected_reply_type == "time"
    assert artifact.turn_outcome.expected_reply_reason == "booking_prompt"
    assert artifact.turn_outcome.meta["owner_cutover"] == "turn_planner.safe_booking_prompt_owner.v1"
    assert artifact.runtime_meta["owner_cutover"] == "turn_planner.safe_booking_prompt_owner.v1"


def test_turn_executor_builds_typed_check_booking_prompt_owner_cutover_artifact() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "check_booking",
            "action": "collect",
            "tool_action": "collect",
            "reason": "booking_verification_collect_prompt",
            "goal": "booking",
            "slots": {"service": "Маникюр", "datetime": "2026-03-18 15:00"},
            "next_question": "name",
            "open_questions": ["name"],
        },
        interaction_owner="turn_planner.safe_booking_prompt_owner.v1",
        interaction_relation="turn_planner_safe_booking_prompt_owner",
    )
    state = DialogState.model_validate(_dialog_state_payload())

    artifact = TurnExecutor().build_owner_cutover_artifact(
        decision=decision,
        dialog_state=state,
        text="Чтобы проверить, перенести или отменить запись, подскажите номер телефона и примерную дату/время записи.",
        owner_cutover="turn_planner.safe_booking_prompt_owner.v1",
        transport_status="delivered",
        transport_reason=None,
        followup_type="name",
        followup_reason="calendar_get_booking_collect_reference",
        action="check_booking_prompt",
        source="booking_verification",
    )

    _load_schema("contracts/runtime/turn_result.v1.jsonschema").validate(
        artifact.turn_result.model_dump(mode="json")
    )
    assert artifact.turn_result.contract_status == "ok"
    assert artifact.turn_result.reply.reply_kind == "collect"
    assert artifact.turn_outcome.action == "check_booking_prompt"
    assert artifact.turn_outcome.intent == "check_booking"
    assert artifact.turn_outcome.tool_action == "collect"
    assert artifact.turn_outcome.expected_reply_type == "name"
    assert artifact.turn_outcome.expected_reply_reason == "calendar_get_booking_collect_reference"
    assert artifact.turn_outcome.meta["owner_cutover"] == "turn_planner.safe_booking_prompt_owner.v1"
    assert artifact.runtime_meta["owner_cutover"] == "turn_planner.safe_booking_prompt_owner.v1"


def test_turn_executor_returns_reference_prompt_for_check_booking_fact() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "check_booking",
            "action": "fact",
            "tool_action": "calendar.get_booking",
            "reason": "calendar_get_booking_collect_reference",
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "goal": "booking",
            "subject_kind": "booking",
            "capability": "booking_manage",
            "resolution_mode": "direct",
        },
        interaction_owner="turn_planner_intent_routing",
        interaction_relation="grounded_fact",
        source="turn_planner_intent_routing",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Проверьте мою запись на четверг.",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert "Чтобы проверить запись" in result.text
    assert result.tool_action == "calendar.get_booking"
    assert result.tool_decision == "not_found"
    assert result.meta["pending_question_contract"] == {
        "expected_reply_type": "name",
        "reason": "calendar_get_booking_collect_reference",
        "next_question": "name",
        "open_questions": ["name"],
    }
    assert result.meta["semantic_contract"]["capability"] == "booking_manage"


def test_turn_executor_semantic_decision_emits_enrichment_only_meta() -> None:
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "action": "collect",
            "intent": "booking",
            "goal": "booking",
            "capability": "booking_manage",
            "tool_action": "calendar.book_slot",
            "slots": {"service": "Маникюр"},
            "subject_kind": "booking",
            "resolution_mode": "ask_about_requested_slot",
            "expected_reply_type": "time",
            "reason": "collect:datetime",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "memory",
                }
            },
            "entity_refs": [
                {
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "memory",
                    "value": "Маникюр",
                }
            ],
        }
    )
    decision = TurnPlanner().build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="calendar.book_slot",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Хочу записаться на маникюр.",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "Маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime(2026, 3, 27, 13, 0, tzinfo=timezone.utc),
    )

    assert "semantic_contract" not in result.meta
    assert "pending_question_contract" not in result.meta
    assert "semantic_enrichment" not in result.meta


def test_turn_executor_routes_master_query_through_master_catalog() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "master_query",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "tool_args": {"service_query": "Маникюр"},
            "pack_refs": ["master"],
            "reason": "master_question",
            "goal": "booking",
        },
        interaction_owner="turn_planner_intent_routing",
        interaction_relation="generic_info_interrupt",
        source="turn_planner_intent_routing",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="А какие мастера делают маникюр?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "Маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert "маник" in result.text.casefold()
    assert "мастер" in result.text.casefold()
    assert result.tool_decision == "master"
    assert result.meta.get("master_query_contract") == "masters_catalog.v1"
    assert "master" in (result.meta.get("info_sections") or [])


def test_turn_executor_keeps_slot_constraint_collect_contract() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "tool_args": {"candidate_datetime": "15:00"},
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "goal": "booking",
            "reason": "question_contract_slot_constraint",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "question_contract": True,
            "alternate_datetime": "15:00",
        },
        interaction_owner="question_contract",
        interaction_relation="slot_constraint",
        source="question_contract",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Есть ли место завтра в 15:00?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "Маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert "15:00" in result.text
    assert result.tool_decision == "slot_constraint"
    assert result.meta.get("pending_question_act") == "slot_constraint"
    assert result.meta.get("pending_question_target") == "time"
    assert result.meta.get("question_contract") is True


def test_turn_executor_realizes_specialist_followup_collect_prompt_from_canonical_contract() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "reason": "user_requested_specific_master_keep_datetime_collect",
            "goal": "booking",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "referents": {
                "service": {
                    "value": "Наращивание гелем",
                    "entity_id": "svc:gel_extension",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "specialist": {
                    "value": "Айгерим",
                    "entity_id": "spec:aigerim",
                    "entity_type": "specialist",
                    "source_ref": "user_request",
                },
            },
            "subject_kind": "specialist",
            "capability": "bookability",
            "resolution_mode": "referent_followup",
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="referent_followup",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Мне нужно, чтобы мастер был Айгерим.",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "Наращивание гелем"},
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert "Айгерим" in result.text
    assert "мастер" in result.text.casefold()
    assert "дат" in result.text.casefold()
    assert result.tool_decision == "datetime"
    assert result.meta["pending_question_contract"]["pending_question_target"] == "specialist"
    assert result.meta["pending_question_contract"]["active_question_relation"] == "referent_followup"


def test_turn_executor_adds_pricing_info_sections_for_price_reply() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "pricing",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "fact_refs": ["pricing"],
            "reason": "pricing_question",
            "goal": "booking",
        },
        interaction_owner="turn_planner_intent_routing",
        interaction_relation="generic_info_interrupt",
        source="turn_planner_intent_routing",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Сколько стоит маникюр с дизайном ногтей?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "Маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.tool_decision in {"price_query", "price_manicure"}
    assert "pricing" in (result.meta.get("info_sections") or [])


def test_turn_executor_routes_booking_info_interrupts_through_catalog_tool_registry(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _execute_tool_action(db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Официальные акции: первое посещение 10%.",
            error_code=None,
            decision_meta={
                "tool_action": "catalog.service_query",
                "tool_decision": "promotions",
                "info_sections": ["promotions"],
            },
            trace={"stage": "tool_registry", "decision": "promotions"},
        )

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "info",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "tool_args": {},
            "pack_refs": ["promotions"],
            "entity_refs": [
                {
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "value": "маникюр",
                    "source_ref": "message",
                }
            ],
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "subject_kind": "service",
            "capability": "promotions",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "reason": "promo_interrupt",
            "goal": "info",
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="generic_info_interrupt",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Есть ли акции?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert captured["tool_action"] == "catalog.service_query"
    assert captured["service_query"] == "маникюр"
    assert captured["tool_args"] == {"service_query": "маникюр"}
    assert captured["info_sections_hint"] == ["promotions"]
    assert captured["allowed_fact_refs"] == ["promotions"]
    assert result.text == "Официальные акции: первое посещение 10%."
    assert result.tool_decision == "promotions"
    assert result.tool_action == "catalog.service_query"
    projection = result.meta.get("tool_execution_projection") or {}
    assert projection["projection_source"] == "binding_plan.v1"
    assert projection["tool_action"] == "catalog.service_query"
    assert projection["service_query"] == "маникюр"
    assert projection.get("binding_id")
    assert result.meta["semantic_contract"]["referents"]["service"] == {
        "value": "маникюр",
        "entity_id": "svc:manicure",
        "entity_type": "service",
        "source_ref": "message",
    }


def test_turn_executor_uses_binding_plan_for_owner_backed_fact_execution(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _execute_tool_action(db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Маникюр стоит от 9000 тг.",
            error_code=None,
            decision_meta={
                "tool_action": kwargs["tool_action"],
                "tool_decision": "pricing",
                "info_sections": ["pricing"],
            },
            trace={"stage": "tool_registry", "decision": "pricing"},
        )

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    planner = TurnPlanner()
    semantic_payload = build_test_semantic_decision_payload(
        {
            "intent": "pricing",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "slots": {"service": "Маникюр"},
            "reason": "pricing_question",
            "subject_kind": "service",
            "capability": "pricing",
            "resolution_mode": "policy_fact",
        }
    )
    binding_payload = {
        "schema_version": "binding_plan.v1",
        "binding_id": "binding-owner-pricing",
        "decision_id": semantic_payload["decision_id"],
        "binding_outcome_type": "tool_call",
        "capability_id": "pricing",
        "selected_tool_or_workflow_ref": "catalog.service_query",
        "authz_scope": {},
        "resolved_args": {"service_query": "Маникюр"},
        "timeout_policy": {},
        "retry_policy": {},
        "idempotency_key": semantic_payload["decision_id"],
        "deny_reason_code": None,
        "degrade_reason_code": None,
        "handoff_reason_code": None,
    }
    decision = planner._build_policy_core_decision(
        semantic_payload,
        binding_plan_payload=binding_payload,
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Сколько стоит маникюр?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert captured["tool_action"] == "catalog.service_query"
    assert captured["tool_args"] == {"service_query": "Маникюр"}
    assert captured["allowed_fact_refs"] == ["pricing"]
    assert result.tool_action == "catalog.service_query"
    assert result.tool_decision == "pricing"
    projection = result.meta["tool_execution_projection"]
    assert projection["projection_source"] == "binding_plan.v1"
    assert projection["binding_id"] == "binding-owner-pricing"
    assert projection["tool_action"] == "catalog.service_query"
    assert projection["service_query"] == "Маникюр"
    assert result.meta["fact_manifest_id"] == "default_fact_manifest.v1"
    assert result.meta["fact_requested_refs"] == ["pricing"]
    assert result.meta["fact_allowed_refs"] == ["pricing"]
    assert result.meta["fact_allowed_sets"] == [["pricing"]]
    assert result.meta["fact_emitted_refs"] == ["pricing"]
    fact_contract = result.meta["fact_contract"]
    assert fact_contract["manifest_id"] == "default_fact_manifest.v1"
    assert fact_contract["request"]["requested_fact_refs"] == ["pricing"]
    assert fact_contract["plan"]["allowed_emitted_fact_refs"] == ["pricing"]
    assert fact_contract["plan"]["allowed_emitted_sets"] == [["pricing"]]
    assert fact_contract["result"]["emitted_fact_refs"] == ["pricing"]
    assert fact_contract["result"]["scope_verdict"] == "ok"


def test_turn_executor_rejects_out_of_plan_tool_fact_scope(monkeypatch) -> None:
    def _execute_tool_action(db, **kwargs):
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Есть акция 10%.",
            error_code=None,
            decision_meta={
                "tool_action": kwargs["tool_action"],
                "tool_decision": "promotions",
                "info_sections": ["promotions"],
            },
            trace={"stage": "tool_registry", "decision": "promotions"},
        )

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )
    monkeypatch.setattr(
        "app.services.pack_runtime_service.get_pack_decision",
        lambda *args, **kwargs: SimpleNamespace(response="", intent=None, meta={}, action="reply"),
    )

    planner = TurnPlanner()
    semantic_payload = build_test_semantic_decision_payload(
        {
            "intent": "pricing",
            "action": "fact",
            "tool_action_hint": "catalog.service_query",
            "slots": {"service": "Маникюр"},
            "reason": "pricing_question",
            "subject_kind": "service",
            "capability": "pricing",
            "resolution_mode": "policy_fact",
        }
    )
    binding_payload = {
        "schema_version": "binding_plan.v1",
        "binding_id": "binding-owner-pricing",
        "decision_id": semantic_payload["decision_id"],
        "binding_outcome_type": "tool_call",
        "capability_id": "pricing",
        "selected_tool_or_workflow_ref": "catalog.service_query",
        "authz_scope": {},
        "resolved_args": {"service_query": "Маникюр"},
        "timeout_policy": {},
        "retry_policy": {},
        "idempotency_key": semantic_payload["decision_id"],
        "deny_reason_code": None,
        "degrade_reason_code": None,
        "handoff_reason_code": None,
    }
    decision = planner._build_policy_core_decision(
        semantic_payload,
        binding_plan_payload=binding_payload,
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Сколько стоит маникюр?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.text == "Я уточню это для вас."
    assert result.tool_decision == "info_ref_unresolved"
    assert result.meta["fact_fallback"] is True
    assert result.meta["fact_fallback_reason"] == "policy_info_unresolved"
    assert result.meta["fact_scope_violations"] == [
        {
            "resolution_source": "tool_registry",
            "out_of_scope_fact_refs": ["promotions"],
        }
    ]
    assert result.meta["fact_requested_refs"] == ["pricing"]
    assert result.meta["fact_allowed_refs"] == ["pricing"]
    assert result.meta["fact_emitted_refs"] == []
    assert result.meta["fact_contract"]["result"]["scope_verdict"] == "empty"


def test_tool_registry_catalog_service_query_blocks_out_of_plan_fact_reply(monkeypatch) -> None:
    from app.services import tool_registry_service

    branch = SimpleNamespace(booking_settings={}, client_id=uuid4(), id=uuid4())
    monkeypatch.setattr(tool_registry_service, "_resolve_branch", lambda db, branch_id: branch)
    monkeypatch.setattr(
        tool_registry_service,
        "resolve_tool_protocol_decision",
        lambda tool_action: SimpleNamespace(
            allowed=True,
            reason=None,
            source="test",
            enforcement_enabled=True,
            deny_by_default=False,
        ),
    )
    monkeypatch.setattr(
        tool_registry_service,
        "resolve_tool_certification_decision",
        lambda db, tool_action, scope: SimpleNamespace(
            allowed=True,
            reason=None,
            source="test",
            registry_status="ready",
            certification_status="ready",
            health_status="ready",
            allowed_scopes=[],
        ),
    )
    monkeypatch.setattr(
        tool_registry_service,
        "_detect_promotion_intent",
        lambda normalized, client_slug=None: "promotions",
    )
    monkeypatch.setattr(
        tool_registry_service,
        "format_reply_from_truth",
        lambda *args, **kwargs: "Есть акция 10%.",
    )

    result = tool_registry_service.execute_tool_action(
        object(),
        tool_action="catalog.service_query",
        tool_args={},
        conversation_id=None,
        branch_id=uuid4(),
        client_slug="demo_salon",
        service_query=None,
        info_sections_hint=["promotions"],
        message_text="Есть ли акции?",
        expected_reply_type=None,
        now=datetime.now(timezone.utc),
        allowed_fact_refs=["pricing"],
    )

    assert result.handled is True
    assert result.ok is False
    assert result.response_text is None
    assert result.error_code == "fact_scope_not_allowed"
    assert result.decision_meta["tool_decision"] == "fact_scope_not_allowed"


def test_turn_executor_first_fact_family_reroutes_stale_service_query_binding(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _execute_tool_action(db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Работаем ежедневно с 10:00 до 20:00.",
            error_code=None,
            decision_meta={
                "tool_action": kwargs["tool_action"],
                "tool_decision": "hours",
                "info_sections": ["hours"],
            },
            trace={"stage": "tool_registry", "decision": "hours"},
        )

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "hours",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "tool_args": {"service_query": "маникюр"},
            "pack_refs": ["hours"],
            "fact_refs": ["hours"],
            "slots": {"service": "маникюр"},
            "reason": "hours_lookup",
            "goal": "info",
            "capability": "hours",
            "subject_kind": "branch",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="До скольки вы сегодня работаете?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert captured["tool_action"] == "catalog.location"
    assert captured["tool_args"] == {}
    assert captured["allowed_fact_refs"] == ["hours"]
    assert result.tool_action == "catalog.location"
    assert result.tool_decision == "hours"
    projection = result.meta["tool_execution_projection"]
    assert projection["projection_source"] == "binding_plan.v1"
    assert projection["tool_action"] == "catalog.location"
    assert projection["fact_family_cutover"] == "location_hours_parking"
    assert projection["fact_family_bundle_policy"] == "location_base_bundle"
    assert "service_query" not in projection
    assert result.meta["fact_manifest_id"] == "default_fact_manifest.v1"
    assert result.meta["fact_requested_refs"] == ["hours"]
    assert result.meta["fact_allowed_refs"] == ["hours"]
    assert result.meta["fact_allowed_sets"] == [["hours"]]
    assert result.meta["fact_emitted_refs"] == ["hours"]
    fact_contract = result.meta["fact_contract"]
    assert fact_contract["plan"]["bundle_policy"] == "location_base_bundle"
    assert fact_contract["plan"]["allowed_emitted_sets"] == [["hours"]]
    assert fact_contract["result"]["emitted_fact_refs"] == ["hours"]


def test_turn_executor_first_fact_family_blocks_direct_truth_and_pack_bypass(monkeypatch) -> None:
    calls = {"direct_truth": 0, "pack_runtime": 0}

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        lambda db, **kwargs: SimpleNamespace(
            handled=False,
            ok=False,
            response_text=None,
            error_code=None,
            decision_meta={},
            trace={},
        ),
    )

    def _format_reply_from_truth(*args, **kwargs):
        calls["direct_truth"] += 1
        return "Есть парковка рядом с салоном."

    def _get_pack_decision(*args, **kwargs):
        calls["pack_runtime"] += 1
        return SimpleNamespace(
            response="Есть парковка рядом с салоном.",
            intent="parking",
            meta={"info_sections": ["parking"]},
            action="reply",
        )

    monkeypatch.setattr(
        "app.services.pack_runtime_service.format_reply_from_truth",
        _format_reply_from_truth,
    )
    monkeypatch.setattr(
        "app.services.pack_runtime_service.get_pack_decision",
        _get_pack_decision,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "parking",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": ["parking"],
            "fact_refs": ["parking"],
            "reason": "parking_question",
            "goal": "info",
            "capability": "parking",
            "subject_kind": "branch",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="У вас есть парковка?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == {"direct_truth": 0, "pack_runtime": 0}
    assert result.text == "Я уточню это для вас."
    assert result.tool_action == "catalog.location"
    assert result.tool_decision == "fact_family_unresolved"
    assert result.meta["fact_fallback"] is True
    assert result.meta["fact_fallback_reason"] == "first_fact_family_cutover_unresolved"
    assert result.meta["fact_family_cutover"] == "location_hours_parking"
    assert result.meta["required_tool_action"] == "catalog.location"
    assert result.meta["fact_manifest_id"] == "default_fact_manifest.v1"
    assert result.meta["fact_requested_refs"] == ["parking"]
    assert result.meta["fact_allowed_refs"] == ["parking"]
    assert result.meta["fact_allowed_sets"] == [["parking"]]
    assert result.meta["fact_emitted_refs"] == []


def test_turn_executor_first_fact_family_blocks_mixed_scope_direct_truth_and_pack_bypass(monkeypatch) -> None:
    calls = {"direct_truth": 0, "pack_runtime": 0}

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        lambda db, **kwargs: SimpleNamespace(
            handled=False,
            ok=False,
            response_text=None,
            error_code=None,
            decision_meta={},
            trace={},
        ),
    )

    def _format_reply_from_truth(*args, **kwargs):
        calls["direct_truth"] += 1
        return "Адрес: Абая 10."

    def _get_pack_decision(*args, **kwargs):
        calls["pack_runtime"] += 1
        return SimpleNamespace(
            response="Адрес: Абая 10.",
            intent="location",
            meta={"info_sections": ["location"]},
            action="reply",
        )

    monkeypatch.setattr(
        "app.services.pack_runtime_service.format_reply_from_truth",
        _format_reply_from_truth,
    )
    monkeypatch.setattr(
        "app.services.pack_runtime_service.get_pack_decision",
        _get_pack_decision,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "other",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": ["parking", "promotions"],
            "fact_refs": ["parking", "promotions"],
            "reason": "mixed_scope_question",
            "goal": "info",
            "capability": "parking",
            "subject_kind": "branch",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Подскажите парковку и акции.",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == {"direct_truth": 0, "pack_runtime": 0}
    assert result.text == "Я уточню это для вас."
    assert result.tool_decision == "fact_family_unresolved"
    assert result.meta["fact_fallback"] is True
    assert result.meta["fact_fallback_reason"] == "first_fact_family_mixed_scope_unresolved"
    assert result.meta["fact_family_cutover"] == "location_hours_parking"
    assert result.meta["family_overlap_fact_refs"] == ["parking"]
    assert result.meta["fact_requested_refs"] == ["parking", "promotions"]
    assert result.meta["fact_allowed_refs"] == ["parking", "promotions"]
    assert result.meta["fact_emitted_refs"] == []


def test_tool_registry_catalog_location_does_not_reinfer_parking_outside_allowed_scope(monkeypatch) -> None:
    from app.services import tool_registry_service

    monkeypatch.setattr(tool_registry_service, "_resolve_branch", lambda db, branch_id: None)

    result = tool_registry_service.execute_tool_action(
        object(),
        tool_action="catalog.location",
        tool_args={},
        conversation_id=None,
        branch_id=None,
        client_slug="demo_salon",
        service_query=None,
        info_sections_hint=["location", "hours"],
        message_text="У вас есть парковка?",
        expected_reply_type=None,
        now=datetime.now(timezone.utc),
        allowed_fact_refs=["location", "hours"],
    )

    assert result.handled is True
    assert result.ok is True
    assert "parking" not in (result.decision_meta.get("info_sections") or [])


def test_turn_executor_routes_owner_backed_collect_by_binding_outcome(monkeypatch) -> None:
    planner = TurnPlanner()
    semantic_payload = build_test_semantic_decision_payload(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "calendar.list_slots",
            "reason": "collect:datetime",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "policy_collect",
            "slots": {"service": "Маникюр"},
            "next_question": "datetime",
            "open_questions": ["datetime"],
        }
    )
    binding_payload = {
        "schema_version": "binding_plan.v1",
        "binding_id": "binding-owner-collect",
        "decision_id": semantic_payload["decision_id"],
        "binding_outcome_type": "workflow_advance",
        "capability_id": "bookability",
        "selected_tool_or_workflow_ref": "calendar.list_slots",
        "authz_scope": {},
        "resolved_args": {"service_query": "Маникюр"},
        "timeout_policy": {},
        "retry_policy": {},
        "idempotency_key": semantic_payload["decision_id"],
        "deny_reason_code": None,
        "degrade_reason_code": None,
        "handoff_reason_code": None,
    }
    decision = planner._build_policy_core_decision(
        semantic_payload,
        binding_plan_payload=binding_payload,
    )
    decision.outcome = "FACT"

    monkeypatch.setattr(
        TurnExecutor,
        "_execute_collect",
        lambda self, decision, *, booking_state: SimpleNamespace(
            text="На какую дату и время вам удобно?",
            tool_action="collect",
            tool_decision="datetime",
            meta={"binding_outcome_test": "collect"},
        ),
    )
    monkeypatch.setattr(
        TurnExecutor,
        "_execute_fact",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("owner-backed collect must not route through FACT compatibility path")
        ),
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Хочу записаться",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.tool_action == "collect"
    assert result.meta["binding_outcome_test"] == "collect"


def test_turn_executor_routes_binding_plan_collect_without_semantic_owner(monkeypatch) -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "fact",
            "tool_action": "calendar.list_slots",
        },
        interaction_owner="legacy_booking_flow",
        interaction_relation="ask_about_requested_slot",
        source="legacy_runtime",
    )
    decision.outcome = "FACT"
    decision.binding_plan = BindingPlanV1.model_validate(
        _binding_plan_payload()
        | {
            "decision_id": "binding-non-owner-collect",
            "binding_outcome_type": "workflow_advance",
            "capability_id": "bookability",
            "selected_tool_or_workflow_ref": "collect",
            "resolved_args": {},
            "idempotency_key": "binding-non-owner-collect",
        }
    )

    monkeypatch.setattr(
        TurnExecutor,
        "_execute_collect",
        lambda *args, **kwargs: RuntimeExecutionResult(
            text="На какую дату и время вам удобно?",
            tool_action="collect",
            tool_decision="datetime",
            meta={"binding_outcome_test": "non_owner_collect"},
        ),
    )
    monkeypatch.setattr(
        TurnExecutor,
        "_execute_fact",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("binding_plan must route non-owner collect before FACT compatibility fallback")
        ),
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Хочу записаться",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.tool_action == "collect"
    assert result.meta["binding_outcome_test"] == "non_owner_collect"


def test_turn_executor_routes_owner_backed_handoff_by_binding_outcome() -> None:
    planner = TurnPlanner()
    semantic_payload = build_test_semantic_decision_payload(
        {
            "intent": "manager",
            "action": "handoff",
            "tool_action_hint": "handoff",
            "reason": "manager_requested",
            "subject_kind": "conversation",
            "capability": "handoff",
            "resolution_mode": "policy_handoff",
        }
    )
    binding_payload = {
        "schema_version": "binding_plan.v1",
        "binding_id": "binding-owner-handoff",
        "decision_id": semantic_payload["decision_id"],
        "binding_outcome_type": "handoff",
        "capability_id": "handoff",
        "selected_tool_or_workflow_ref": "handoff",
        "authz_scope": {},
        "resolved_args": {},
        "timeout_policy": {},
        "retry_policy": {},
        "idempotency_key": semantic_payload["decision_id"],
        "deny_reason_code": None,
        "degrade_reason_code": None,
        "handoff_reason_code": "manager_requested",
    }
    decision = planner._build_policy_core_decision(
        semantic_payload,
        binding_plan_payload=binding_payload,
    )
    decision.outcome = "FACT"

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Позовите менеджера",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.tool_action == "handoff"
    assert result.request_handoff is True
    assert result.meta["handoff_requested"] is True


def test_consultant_runtime_binding_plan_handoff_skips_execution_boundary_degrade() -> None:
    runtime = ConsultantRuntime()
    decision = build_test_policy_override_decision(
        {
            "intent": "manager",
            "action": "fact",
            "tool_action": "catalog.service_query",
        },
        interaction_owner="legacy_manager_path",
        interaction_relation="manager_requested",
        source="legacy_runtime",
    )
    decision.outcome = "FACT"
    decision.binding_plan = BindingPlanV1.model_validate(
        _binding_plan_payload()
        | {
            "decision_id": "binding-non-owner-handoff",
            "binding_outcome_type": "handoff",
            "capability_id": "other",
            "selected_tool_or_workflow_ref": "handoff",
            "resolved_args": {},
            "idempotency_key": "binding-non-owner-handoff",
            "handoff_reason_code": "manager_requested",
        }
    )
    execution = RuntimeExecutionResult(
        text="Передаю диалог менеджеру. Он скоро подключится.",
        tool_action="handoff",
        tool_decision="pending",
        meta={"handoff_requested": True},
        request_handoff=True,
    )

    preserved_decision, override = runtime._apply_execution_boundary_override(
        decision=decision,
        execution=execution,
        boundary_override=None,
    )

    assert preserved_decision == decision
    assert override is None
    assert runtime._should_activate_handoff(
        decision=preserved_decision,
        boundary_override=override,
    ) is True


def test_turn_executor_ignores_stale_compat_control_fields_when_binding_tool_call_exists(
    monkeypatch,
) -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "pricing",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "slots": {"service": "Маникюр"},
            "reason": "pricing_question",
            "goal": "info",
            "subject_kind": "service",
            "capability": "pricing",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="legacy_info_path",
        interaction_relation="generic_info_interrupt",
        source="legacy_runtime",
    )
    decision.outcome = "COLLECT"
    decision.tool_action = "calendar.book_slot"

    monkeypatch.setattr(
        TurnExecutor,
        "_execute_collect",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("stale COLLECT outcome must not override tool-call binding")
        ),
    )
    monkeypatch.setattr(
        TurnExecutor,
        "_execute_booking_confirmation",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("stale tool_action must not override tool-call binding")
        ),
    )
    monkeypatch.setattr(
        TurnExecutor,
        "_execute_fact",
        lambda *args, **kwargs: RuntimeExecutionResult(
            text="Маникюр стоит от 9000 тг.",
            tool_action="catalog.service_query",
            tool_decision="pricing",
            meta={"binding_only_route": True},
        ),
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Сколько стоит маникюр?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.tool_action == "catalog.service_query"
    assert result.meta["binding_only_route"] is True


def test_turn_executor_routes_degrade_binding_even_when_outcome_is_stale_fact() -> None:
    decision = TurnPlanner().build_controlled_degrade(
        reason_code="planner_timeout",
        control_label="planner_timeout",
        interaction_owner="turn_planner",
    )
    decision.outcome = "FACT"

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="ignored",
        client_slug=None,
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.tool_action == "handoff"
    assert result.tool_decision == "degrade"
    assert result.request_handoff is True
    assert result.meta["reason_code"] == "planner_timeout"


def test_consultant_runtime_collect_and_handoff_predicates_use_binding_only() -> None:
    collect_decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "fact",
            "tool_action": "calendar.list_slots",
        },
        interaction_owner="legacy_booking_flow",
        interaction_relation="ask_about_requested_slot",
        source="legacy_runtime",
    )
    collect_decision.outcome = "HANDOFF"
    collect_decision.binding_plan = BindingPlanV1.model_validate(
        _binding_plan_payload()
        | {
            "decision_id": "binding-only-collect",
            "binding_outcome_type": "workflow_advance",
            "capability_id": "bookability",
            "selected_tool_or_workflow_ref": "collect",
            "resolved_args": {},
            "idempotency_key": "binding-only-collect",
        }
    )

    handoff_decision = build_test_policy_override_decision(
        {
            "intent": "manager",
            "action": "fact",
            "tool_action": "catalog.service_query",
        },
        interaction_owner="legacy_manager_flow",
        interaction_relation="manager_requested",
        source="legacy_runtime",
    )
    handoff_decision.outcome = "FACT"
    handoff_decision.binding_plan = BindingPlanV1.model_validate(
        _binding_plan_payload()
        | {
            "decision_id": "binding-only-handoff",
            "binding_outcome_type": "handoff",
            "capability_id": "handoff",
            "selected_tool_or_workflow_ref": "handoff",
            "resolved_args": {},
            "idempotency_key": "binding-only-handoff",
            "handoff_reason_code": "manager_requested",
        }
    )

    assert ConsultantRuntime._decision_collects(collect_decision) is True
    assert ConsultantRuntime._decision_requests_handoff(collect_decision) is False
    assert ConsultantRuntime._decision_requests_handoff(handoff_decision) is True
    assert ConsultantRuntime._decision_collects(handoff_decision) is False


def test_turn_executor_projects_policy_info_refs_into_catalog_execution(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _execute_tool_action(db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Официальные акции: первое посещение 10%.",
            error_code=None,
            decision_meta={
                "tool_action": kwargs["tool_action"],
                "tool_decision": "promotions",
                "info_sections": ["promotions"],
            },
            trace={"stage": "tool_registry", "decision": "promotions"},
        )

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )
    monkeypatch.setattr(
        "app.services.pack_runtime_service.get_pack_decision",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("raw pack fallback should not run")),
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "other",
            "action": "fact",
            "tool_action": "info",
            "tool_args": {"info_refs": ["promotions"]},
            "subject_kind": "service",
            "capability": "promotions",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "goal": "info",
        },
        interaction_owner="llm_policy_core",
        interaction_relation="generic_info_interrupt",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="У вас есть промо-коды?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert captured["tool_action"] == "catalog.service_query"
    assert captured["info_sections_hint"] == ["promotions"]
    assert captured["allowed_fact_refs"] == ["promotions"]
    assert result.tool_action == "catalog.service_query"
    assert result.tool_decision == "promotions"
    assert result.text == "Официальные акции: первое посещение 10%."


def test_turn_executor_uses_policy_owned_info_truth_fallback_without_echo(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.pack_runtime_service.get_pack_decision",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("raw pack fallback should not run")),
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "other",
            "action": "fact",
            "tool_action": "info",
            "tool_args": {"info_ref": "promotions"},
            "subject_kind": "service",
            "capability": "promotions",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "goal": "info",
        },
        interaction_owner="llm_policy_core",
        interaction_relation="generic_info_interrupt",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="У вас есть промо-коды?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.tool_action == "catalog.service_query"
    assert result.tool_decision == "promotions"
    assert result.text != "У вас есть промо-коды?"
    assert "10%" in result.text
    assert result.meta.get("info_sections") == ["promotions"]
    assert result.meta.get("info_ref_execution") is True
    assert result.meta.get("info_ref_source") == "policy_core"
    assert result.meta.get("fact_fallback") is None


def test_turn_executor_uses_governed_logical_info_tool_candidates_without_echo(monkeypatch) -> None:
    captured: list[tuple[str, dict[str, object]]] = []

    def _execute_tool_action(db, **kwargs):
        captured.append((kwargs["tool_action"], dict(kwargs)))
        if kwargs["tool_action"] == "catalog.service_query":
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Официальные акции: первое посещение 10%.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "promotions",
                    "info_sections": ["promotions"],
                },
                trace={"stage": "tool_registry", "decision": "promotions"},
            )
        return SimpleNamespace(
            handled=True,
            ok=False,
            response_text="Адрес сейчас недоступен. Напишите, пожалуйста, какой район удобен.",
            error_code="not_found",
            decision_meta={"tool_action": kwargs["tool_action"], "tool_decision": "not_found"},
            trace={"stage": "tool_registry", "decision": "not_found"},
        )

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )
    monkeypatch.setattr(
        "app.services.pack_runtime_service.get_pack_decision",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("raw pack fallback should not run")),
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "other",
            "action": "fact",
            "tool_action": "info",
            "subject_kind": "service",
            "capability": "bookability",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "goal": "info",
            "reason": "user_asked_promotions_generic_info_interrupt_preserve_booking_time_collect",
            "entity_refs": [
                {
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "value": "маникюр",
                    "source_ref": "carryover",
                }
            ],
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "pending_question_target": "time",
        },
        interaction_owner="llm_policy_core",
        interaction_relation="generic_info_interrupt",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Есть ли акции?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state={"service": "маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert captured
    assert captured[0][0] == "catalog.service_query"
    assert captured[0][1]["service_query"] == "маникюр"
    assert result.tool_action == "info"
    assert result.tool_decision == "info_ref_unresolved"
    assert result.text == "Я уточню это для вас."
    assert result.meta.get("fact_fallback_reason") == "policy_info_unresolved"
    assert result.meta.get("policy_info_refs") == ["other", "bookability"]


def test_turn_executor_projects_specialist_referent_into_tool_args(monkeypatch) -> None:
    captured: dict[str, object] = {}
    specialist_id = str(uuid4())

    def _execute_tool_action(db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Есть окно у Айгерим завтра в 15:00.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.list_slots",
                "tool_decision": "availability_found",
            },
            trace={"stage": "tool_registry", "decision": "availability_found"},
        )

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "fact",
            "tool_action": "calendar.list_slots",
            "tool_args": {},
            "slots": {},
            "entity_refs": [
                {
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "value": "маникюр",
                    "source_ref": "message",
                },
                {
                    "entity_id": specialist_id,
                    "entity_type": "specialist",
                    "value": "Айгерим",
                    "source_ref": "message",
                },
            ],
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                },
                "specialist": {
                    "value": "Айгерим",
                    "entity_id": specialist_id,
                    "entity_type": "specialist",
                    "source_ref": "message",
                },
            },
            "subject_kind": "specialist",
            "capability": "live_availability",
            "temporal_scope": "specific_time",
            "resolution_mode": "live_calendar",
            "reason": "specialist_availability",
            "goal": "booking",
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="specialist_availability_interrupt",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="А у Айгерим есть окна завтра?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert captured["tool_action"] == "calendar.list_slots"
    assert captured["service_query"] == "маникюр"
    assert captured["tool_args"] == {
        "service_query": "маникюр",
        "specialist_name": "Айгерим",
        "specialist_id": specialist_id,
    }
    assert result.tool_action == "calendar.list_slots"
    assert result.tool_decision == "availability_found"
    projection = result.meta.get("tool_execution_projection") or {}
    assert projection["projection_source"] == "binding_plan.v1"
    assert projection["tool_action"] == "calendar.list_slots"
    assert projection["service_query"] == "маникюр"
    assert projection["specialist_name"] == "Айгерим"
    assert projection["specialist_id"] == specialist_id
    assert projection.get("binding_id")


def test_turn_executor_prunes_legacy_info_args_when_resolving_catalog_service_query(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _execute_tool_action(db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Маникюр длится около 60 минут.",
            error_code=None,
            decision_meta={
                "tool_action": "catalog.service_query",
                "tool_decision": "duration",
            },
            trace={"stage": "tool_registry", "decision": "duration"},
        )

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "duration",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "tool_args": {},
            "pack_refs": ["duration"],
            "slots": {"service": "маникюр"},
            "open_questions": ["datetime"],
            "needs_manager": False,
            "risk_signals": [],
            "reason": "duration_interrupt",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "subject_kind": "service",
            "capability": "duration",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="generic_info_interrupt",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Как долго длится маникюр?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert captured["tool_action"] == "catalog.service_query"
    assert captured["tool_args"] == {"service_query": "маникюр"}
    assert result.tool_action == "catalog.service_query"
    assert result.tool_decision == "duration"
    projection = result.meta.get("tool_execution_projection") or {}
    assert projection["projection_source"] == "binding_plan.v1"
    assert projection["tool_action"] == "catalog.service_query"
    assert projection["service_query"] == "маникюр"
    assert projection.get("binding_id")


def test_turn_executor_does_not_project_service_shadow_into_catalog_location(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _execute_tool_action(db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Мы находимся на Абая 10.",
            error_code=None,
            decision_meta={
                "tool_action": "catalog.location",
                "tool_decision": "location",
            },
            trace={"stage": "tool_registry", "decision": "location"},
        )

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "location",
            "action": "fact",
            "tool_action": "catalog.location",
            "tool_args": {},
            "pack_refs": ["location"],
            "slots": {"service": "маникюр"},
            "open_questions": ["service"],
            "needs_manager": False,
            "risk_signals": [],
            "reason": "location_interrupt",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "subject_kind": "branch",
            "capability": "location",
            "temporal_scope": "none",
            "resolution_mode": "direct",
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="generic_info_interrupt",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Какой адрес вашего салона?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert captured["tool_action"] == "catalog.location"
    assert captured["tool_args"] == {}
    assert result.tool_action == "catalog.location"
    assert result.tool_decision == "location"
    projection = result.meta.get("tool_execution_projection") or {}
    assert projection["projection_source"] == "binding_plan.v1"
    assert projection["tool_action"] == "catalog.location"
    assert projection.get("binding_id")
    assert "service_query" not in projection


def test_turn_executor_keeps_original_fact_query_text_without_semantic_rewrite(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def _get_pack_decision(query_text: str, client_slug: str | None = None):
        captured["query_text"] = query_text
        return SimpleNamespace(response="Цена зависит от услуги.", intent="price_query", meta={}, action="reply")

    monkeypatch.setattr("app.services.pack_runtime_service.get_pack_decision", _get_pack_decision)

    decision = build_test_policy_override_decision(
        {
            "intent": "pricing",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "fact_refs": ["pricing"],
            "reason": "pricing_question",
            "goal": "booking",
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="И сколько это будет?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "Маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert captured["query_text"] == "И сколько это будет?"
    assert result.tool_decision == "price_query"


def test_turn_executor_pricing_fact_uses_public_pack_runtime_seam_without_adapter_runtime_fallback(
    monkeypatch,
) -> None:
    def _runtime_pack_decision(*_args, **_kwargs):
        raise AssertionError("default adapter fallback should stay unused on the active pricing seam")

    monkeypatch.setattr(
        "app.services.pack_runtime_service._runtime_get_pack_decision",
        _runtime_pack_decision,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "pricing",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "fact_refs": ["pricing"],
            "reason": "pricing_question",
            "goal": "info",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Сколько стоит маникюр?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.tool_decision == "price_query"
    assert "маникюр" in (result.text or "").lower()
    semantic_contract = result.meta.get("semantic_contract") or {}
    assert semantic_contract.get("referents", {}).get("service", {}).get("value") == "Маникюр"


def test_pack_grounding_flows_into_runtime_state_trace_and_meta(monkeypatch) -> None:
    def _get_pack_decision(query_text: str, client_slug: str | None = None):
        assert query_text == "Сколько стоит маникюр?"
        assert client_slug == "demo_salon"
        return SimpleNamespace(
            response="Маникюр стоит 10000 тг.",
            intent="price_query",
            action="reply",
            meta={
                "semantic_grounding": {
                    "contract_version": "semantic_contract.v1",
                    "entity_refs": [
                        {
                            "entity_id": "service:manikyur",
                            "entity_type": "service",
                            "value": "Маникюр",
                            "source_ref": "truth:pricing",
                            "confidence": 0.91,
                        }
                    ],
                    "referents": {
                        "service": {
                            "value": "Маникюр",
                            "entity_id": "service:manikyur",
                            "entity_type": "service",
                            "source_ref": "truth:pricing",
                        }
                    },
                    "grounding_provenance": {
                        "pack_id": "demo_salon",
                        "entity_id": "price_item:manikyur",
                        "source_ref": "truth:pricing",
                        "resolver_id": "pack_query_engine",
                        "resolver_version": "2026-03-25",
                        "confidence": 0.91,
                    },
                }
            },
        )

    monkeypatch.setattr("app.services.pack_runtime_service.get_pack_decision", _get_pack_decision)

    decision = build_test_policy_override_decision(
        {
            "intent": "pricing",
            "action": "fact",
            "tool_action": "info",
            "tool_args": {},
            "subject_kind": "service",
            "capability": "pricing",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "goal": "info",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Сколько стоит маникюр?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    expected_service_referent = {
        "value": "Маникюр",
        "entity_id": "service:manikyur",
        "entity_type": "service",
        "source_ref": "truth:pricing",
    }
    assert result.meta["semantic_contract"]["referents"]["service"] == expected_service_referent
    assert result.meta["semantic_contract"]["entity_refs"] == [
        {
            "entity_id": "service:manikyur",
            "entity_type": "service",
            "value": "Маникюр",
            "source_ref": "truth:pricing",
            "confidence": 0.91,
        }
    ]
    assert result.meta["semantic_contract"]["grounding_provenance"] == {
        "pack_id": "demo_salon",
        "entity_id": "price_item:manikyur",
        "source_ref": "truth:pricing",
        "resolver_id": "pack_query_engine",
        "resolver_version": "2026-03-25",
        "confidence": 0.91,
    }

    now = datetime.now(timezone.utc)
    updated, dialog_state, _ = DialogStateService().write_runtime_payload(
        {},
        decision=decision,
        execution_meta=result.meta,
        now=now,
    )
    runtime_payload = updated["consultant_runtime"]
    assert dialog_state.current_referents.service == "Маникюр"
    assert "semantic_contract" not in runtime_payload
    assert dialog_state.meta["semantic_contract"]["referents"]["service"] == expected_service_referent
    assert dialog_state.meta["semantic_contract"]["grounding_provenance"]["pack_id"] == "demo_salon"

    runtime = ConsultantRuntime()
    conversation = SimpleNamespace(context={}, state="bot_active")
    user_message = SimpleNamespace(message_metadata={})
    execution = SimpleNamespace(
        tool_action=result.tool_action,
        tool_decision=result.tool_decision,
        meta=result.meta,
    )
    turn_result = SimpleNamespace(dialog_state=dialog_state, reply=SimpleNamespace(reply_kind="fact"))

    runtime._record_turn_trace(
        conversation=conversation,
        user_message=user_message,
        bot_response=None,
        decision=decision,
        execution=execution,
        turn_result=turn_result,
        delivered=True,
    )

    trace = conversation.context.get("decision_trace") or []
    assert any(
        entry.get("stage") == "consultant_runtime"
        and entry.get("semantic_contract", {}).get("referents", {}).get("service")
        == expected_service_referent
        and entry.get("semantic_contract", {}).get("grounding_provenance", {}).get("pack_id")
        == "demo_salon"
        for entry in trace
    )
    decision_meta = (user_message.message_metadata or {}).get("decision_meta") or {}
    assert decision_meta["semantic_contract"]["referents"]["service"] == expected_service_referent
    assert decision_meta["semantic_contract"]["grounding_provenance"]["pack_id"] == "demo_salon"


def test_turn_executor_does_not_use_truth_semantic_fallback_when_pack_misses(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.pack_runtime_service.get_pack_decision",
        lambda *args, **kwargs: SimpleNamespace(response="", intent=None, meta={}, action="reply"),
    )

    def _format_reply_from_truth(*args, **kwargs):
        raise AssertionError("truth fallback should not run")

    monkeypatch.setattr(
        "app.services.pack_runtime_service.format_reply_from_truth",
        _format_reply_from_truth,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "promotions",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "fact_refs": ["promotions"],
            "reason": "promotions_question",
            "goal": "info",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Есть ли акции?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.text == "Я уточню это для вас."
    assert result.tool_decision == "fact_unresolved"
    assert result.meta["fact_fallback"] is True
    assert result.meta["fact_fallback_reason"] == "fact_execution_unresolved"
    assert result.meta["fact_allowed_refs"] == ["promotions"]
    assert result.meta["fact_allowed_sets"] == [["promotions"]]
    assert result.meta["fact_emitted_refs"] == []


def test_consultant_runtime_records_question_contract_trace_entries() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "tool_args": {"candidate_datetime": "15:00"},
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "goal": "booking",
            "reason": "question_contract_slot_constraint",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "question_contract": True,
            "alternate_datetime": "15:00",
        },
        interaction_owner="question_contract",
        interaction_relation="slot_constraint",
        source="question_contract",
    )
    execution_meta = {
        "slot_values": {"service": "Маникюр", "datetime": "15:00"},
        "next_slot": "datetime",
        "pending_question_act": "slot_constraint",
        "pending_question_target": "time",
        "question_contract": True,
        "alternate_datetime": "15:00",
    }
    now = datetime.now(timezone.utc)
    _, dialog_state, _ = DialogStateService().write_runtime_payload(
        {},
        decision=decision,
        execution_meta=execution_meta,
        now=now,
    )
    runtime = ConsultantRuntime()
    conversation = SimpleNamespace(context={}, state="bot_active")
    user_message = SimpleNamespace(message_metadata={})
    execution = SimpleNamespace(tool_action="collect", tool_decision="slot_constraint", meta=execution_meta)
    turn_result = SimpleNamespace(dialog_state=dialog_state, reply=SimpleNamespace(reply_kind="collect"))

    runtime._record_turn_trace(
        conversation=conversation,
        user_message=user_message,
        bot_response=None,
        decision=decision,
        execution=execution,
        turn_result=turn_result,
        delivered=True,
    )

    trace = conversation.context.get("decision_trace") or []
    assert any(
        entry.get("stage") == "pending_question_interaction"
        and entry.get("pending_question_act") == "slot_constraint"
        and entry.get("pending_question_target") == "time"
        for entry in trace
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        and entry.get("pending_question_contract", {}).get("next_question") == "datetime"
        for entry in trace
    )
    decision_meta = (user_message.message_metadata or {}).get("decision_meta") or {}
    assert decision_meta.get("pending_question_act") == "slot_constraint"
    assert decision_meta.get("question_contract") is True
    assert decision_meta.get("pending_question_contract") == {
        "expected_reply_type": "time",
        "reason": "question_contract_slot_constraint",
        "pending_question_act": "slot_constraint",
        "pending_question_target": "time",
        "active_question_relation": "slot_constraint",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }


def test_consultant_runtime_trace_prefers_canonical_question_contract_over_stale_projection() -> None:
    runtime = ConsultantRuntime()
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "goal": "booking",
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="fill_requested_slot",
        source="llm_policy_core",
    )
    dialog_state = DialogState.model_validate(
        {
            "pending_question_contract": {
                "expected_reply_type": "time",
                "reason": "collect:datetime",
                "next_question": "datetime",
                "open_questions": ["datetime"],
            },
            "projections": {
                "expected_reply_type": "name",
                "expected_reply_reason": "stale_projection",
            },
            "meta": {"current_goal": "booking"},
        }
    )
    conversation = SimpleNamespace(context={}, state="bot_active")
    user_message = SimpleNamespace(message_metadata={})
    execution = SimpleNamespace(tool_action="collect", tool_decision="datetime", meta={})
    turn_result = SimpleNamespace(dialog_state=dialog_state, reply=SimpleNamespace(reply_kind="collect"))

    runtime._record_turn_trace(
        conversation=conversation,
        user_message=user_message,
        bot_response=None,
        decision=decision,
        execution=execution,
        turn_result=turn_result,
        delivered=True,
    )

    trace = conversation.context.get("decision_trace") or []
    assert any(
        entry.get("stage") == "consultant_runtime"
        and entry.get("expected_reply_type") == "time"
        and entry.get("expected_reply_reason") == "collect:datetime"
        for entry in trace
    )
    decision_meta = (user_message.message_metadata or {}).get("decision_meta") or {}
    assert decision_meta.get("expected_reply_type") == "time"
    assert decision_meta.get("expected_reply_reason") == "collect:datetime"
    assert decision_meta.get("pending_question_contract") == {
        "expected_reply_type": "time",
        "reason": "collect:datetime",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }


def test_consultant_runtime_trace_emits_question_contract_for_collect_pending_contract_without_flag() -> None:
    runtime = ConsultantRuntime()
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "goal": "booking",
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="ask_about_requested_slot",
        source="llm_policy_core",
    )
    dialog_state = DialogState.model_validate(
        {
            "pending_question_contract": {
                "expected_reply_type": "time",
                "reason": "collect:datetime",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
                "next_question": "datetime",
                "open_questions": ["datetime"],
            },
            "projections": {
                "expected_reply_type": "time",
                "expected_reply_reason": "collect:datetime",
            },
            "meta": {"current_goal": "booking"},
        }
    )
    conversation = SimpleNamespace(context={}, state="bot_active")
    user_message = SimpleNamespace(message_metadata={})
    execution = SimpleNamespace(tool_action="collect", tool_decision="datetime", meta={})
    turn_result = SimpleNamespace(dialog_state=dialog_state, reply=SimpleNamespace(reply_kind="collect"))

    runtime._record_turn_trace(
        conversation=conversation,
        user_message=user_message,
        bot_response=None,
        decision=decision,
        execution=execution,
        turn_result=turn_result,
        delivered=True,
    )

    trace = conversation.context.get("decision_trace") or []
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        and entry.get("reason") == "collect:datetime"
        for entry in trace
    )
    decision_meta = (user_message.message_metadata or {}).get("decision_meta") or {}
    assert decision_meta.get("question_contract") is True


def test_consultant_runtime_trace_emits_reason_code_for_controlled_degrade() -> None:
    runtime = ConsultantRuntime()
    decision = TurnPlanner().build_controlled_degrade(
        reason_code="planner:invalid_schema",
        control_label="planner_degrade",
        interaction_owner="turn_planner_degrade",
    )
    dialog_state = DialogState.model_validate({"meta": {"current_goal": "booking"}})
    conversation = SimpleNamespace(context={}, state="pending")
    user_message = SimpleNamespace(message_metadata={})
    execution = SimpleNamespace(tool_action="handoff", tool_decision="pending", meta={})
    turn_result = SimpleNamespace(
        dialog_state=dialog_state,
        reply=SimpleNamespace(reply_kind="handoff"),
        observability=SimpleNamespace(reason_code="planner:invalid_schema"),
    )

    runtime._record_turn_trace(
        conversation=conversation,
        user_message=user_message,
        bot_response=None,
        decision=decision,
        execution=execution,
        turn_result=turn_result,
        delivered=True,
    )

    trace = conversation.context.get("decision_trace") or []
    assert any(
        entry.get("stage") == "consultant_runtime"
        and entry.get("reason_code") == "planner:invalid_schema"
        and entry.get("control_label") == "planner_degrade"
        for entry in trace
    )
    runtime_entries = [
        entry for entry in trace if entry.get("stage") == "consultant_runtime"
    ]
    assert runtime_entries
    assert all("semantic_contract" not in entry for entry in runtime_entries)
    assert all("pending_question_contract" not in entry for entry in runtime_entries)
    decision_meta = (user_message.message_metadata or {}).get("decision_meta") or {}
    assert decision_meta.get("reason_code") == "planner:invalid_schema"
    assert decision_meta.get("intent") == "system_control"
    assert decision_meta.get("control_label") == "planner_degrade"
    assert "semantic_contract" not in decision_meta
    assert "pending_question_contract" not in decision_meta


def test_consultant_runtime_trace_records_policy_core_causal_bundle() -> None:
    runtime = ConsultantRuntime()
    decision = TurnPlanner().build_controlled_degrade(
        reason_code="planner:invalid_schema",
        control_label="planner_degrade",
        interaction_owner="turn_planner_degrade",
    )
    decision.meta["earliest_failed_stage"] = "policy_core"
    decision.meta["root_reason_code"] = "policy_core:invalid_schema"
    decision.meta["policy_core_trace"] = {
        "attempted": True,
        "status": "error",
        "schema_verdict": "invalid_schema",
        "projection_verdict": "skipped",
        "input": {"message": "Когда запись?"},
        "raw_output": '{"broken":true}',
        "error": "invalid_schema",
        "schema_error": "tool_action_missing",
        "elapsed_ms": 143.2,
        "model_name": "gpt-5.4-nano-2026-03-17",
        "attempt_count": 1,
    }
    dialog_state = DialogState.model_validate({"meta": {"current_goal": "booking"}})
    conversation = SimpleNamespace(context={}, state="pending")
    user_message = SimpleNamespace(message_metadata={})
    execution = SimpleNamespace(tool_action="handoff", tool_decision="pending", meta={})
    turn_result = SimpleNamespace(
        dialog_state=dialog_state,
        reply=SimpleNamespace(reply_kind="handoff"),
        observability=SimpleNamespace(reason_code="planner:invalid_schema"),
    )

    runtime._record_turn_trace(
        conversation=conversation,
        user_message=user_message,
        bot_response=None,
        decision=decision,
        execution=execution,
        turn_result=turn_result,
        delivered=True,
    )

    trace = conversation.context.get("decision_trace") or []
    assert any(
        entry.get("stage") == "policy_core"
        and entry.get("schema_verdict") == "invalid_schema"
        and entry.get("projection_verdict") == "skipped"
        and entry.get("input") == {"message": "Когда запись?"}
        and entry.get("raw_output") == '{"broken":true}'
        for entry in trace
    )
    assert any(
        entry.get("stage") == "consultant_runtime"
        and entry.get("semantic_runtime_path") == "consultant_core_v2"
        and entry.get("earliest_failed_stage") == "policy_core"
        and entry.get("root_reason_code") == "policy_core:invalid_schema"
        for entry in trace
    )
    decision_meta = (user_message.message_metadata or {}).get("decision_meta") or {}
    assert decision_meta.get("semantic_runtime_path") == "consultant_core_v2"
    assert decision_meta.get("earliest_failed_stage") == "policy_core"
    assert decision_meta.get("root_reason_code") == "policy_core:invalid_schema"
    assert decision_meta.get("policy_core_trace", {}).get("schema_error") == "tool_action_missing"


def test_consultant_runtime_write_runtime_state_persists_semantic_runtime_path() -> None:
    runtime = ConsultantRuntime()
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "goal": "booking",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="fill_requested_slot",
        source="llm_policy_core",
    )

    updated_context, _dialog_state = runtime._write_runtime_state(
        prepared=SimpleNamespace(),
        runtime_state=SimpleNamespace(
            context={},
            dialog_state=DialogState.model_validate({}),
            booking_state={},
        ),
        decision=decision,
        execution=SimpleNamespace(
            meta={},
            clear_booking=False,
            tool_decision="datetime",
        ),
        now=datetime.now(timezone.utc),
    )

    assert updated_context["consultant_runtime"]["semantic_runtime_path"] == "consultant_core_v2"


def test_consultant_runtime_write_runtime_state_projects_touched_slice_class_carryover() -> None:
    runtime = ConsultantRuntime()
    decision = build_test_policy_override_decision(
        {
            "intent": "hours",
            "action": "fact",
            "tool_action": "catalog.location",
            "fact_refs": ["hours"],
            "reason": "hours_lookup",
            "goal": "info",
            "capability": "hours",
            "subject_kind": "branch",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    updated_context, dialog_state = runtime._write_runtime_state(
        prepared=SimpleNamespace(),
        runtime_state=SimpleNamespace(
            context={
                "context_manager": {
                    "message_count": 7,
                    "canonical_dialog_state": {
                        "owner_id": "context_manager.dialog_state.v1",
                        "version": "v1",
                    },
                }
            },
            dialog_state=DialogState.model_validate({}),
            booking_state={},
        ),
        decision=decision,
        execution=SimpleNamespace(
            meta={
                "fact_family_cutover": "location_hours_parking",
                "info_sections": ["address", "hours"],
                "fact_emitted_refs": ["location", "hours"],
            },
            clear_booking=False,
            tool_decision="location_bundle",
        ),
        now=datetime.now(timezone.utc),
    )

    expected = {
        "class": "info_bundle",
        "intents": ["location", "hours"],
        "info_sections": ["address", "hours"],
        "message_count": 7,
        "ttl": 4,
    }

    assert dialog_state.meta["class_carryover"] == expected
    assert updated_context["context_manager"]["class_carryover"] == expected
    assert updated_context["context_manager"]["canonical_dialog_state"]["meta"]["class_carryover"] == expected


def test_consultant_runtime_write_runtime_state_reprojects_compatibility_continuity_from_canonical_runtime_state() -> None:
    runtime = ConsultantRuntime()
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "tool_action_hint": "calendar.list_slots",
            "goal": "booking",
            "reason": "collect_datetime",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "ask_about_requested_slot",
            "slots": {"service": "Маникюр"},
            "expected_reply_type": "time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="ask_about_requested_slot",
        source="llm_policy_core",
    )

    updated_context, dialog_state = runtime._write_runtime_state(
        prepared=SimpleNamespace(),
        runtime_state=SimpleNamespace(
            context={
                "context_manager": {
                    "message_count": 4,
                    "current_goal": "handoff",
                    "canonical_dialog_state": {
                        "owner_id": "context_manager.dialog_state.v1",
                        "version": "v1",
                        "pending_question_contract": {
                            "expected_reply_type": "name",
                            "reason": "stale_projection",
                            "next_question": "name",
                            "open_questions": ["name"],
                        },
                    },
                },
                "expected_reply_type": "name",
                "expected_reply_reason": "stale_projection",
                "current_goal": "handoff",
                "session_memory": {
                    "active_goal": "handoff",
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "reason": "stale_projection",
                        "next_question": "name",
                        "open_questions": ["name"],
                    },
                },
            },
            dialog_state=DialogState.model_validate({}),
            booking_state={},
        ),
        decision=decision,
        execution=SimpleNamespace(
            meta={},
            clear_booking=False,
            tool_decision="datetime",
        ),
        now=datetime(2026, 3, 31, 8, 0, tzinfo=timezone.utc),
    )

    expected_pending_question = {
        "expected_reply_type": "time",
        "reason": "collect_datetime",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }

    assert "expected_reply_type" not in updated_context
    assert "expected_reply_reason" not in updated_context
    assert "current_goal" not in updated_context
    assert dialog_state.pending_question_contract.model_dump(mode="json", exclude_none=True) == expected_pending_question
    assert updated_context["context_manager"]["current_goal"] == "booking"
    assert (
        updated_context["context_manager"]["canonical_dialog_state"]["pending_question_contract"]
        == expected_pending_question
    )
    assert updated_context["session_memory"]["active_goal"] == "booking"
    assert updated_context["session_memory"]["pending_question_contract"] == expected_pending_question


def test_consultant_runtime_control_turn_gate_does_not_claim_first_fact_family_question() -> None:
    runtime = ConsultantRuntime()
    runtime_state = SimpleNamespace(context={}, dialog_state=DialogState.model_validate({}), booking_state={})

    response, returned_state = runtime._handle_control_turn(
        object(),
        payload=SimpleNamespace(body=SimpleNamespace(message="До скольки вы сегодня работаете?")),
        prepared=SimpleNamespace(),
        runtime_state=runtime_state,
        now=datetime(2026, 3, 30, 14, 0, tzinfo=timezone.utc),
        enqueue_only=False,
        skip_persist=False,
    )

    assert response is None
    assert returned_state is runtime_state


def test_consultant_runtime_control_turn_reset_records_control_only_metadata() -> None:
    runtime = ConsultantRuntime()
    conversation = SimpleNamespace(
        id=uuid4(),
        channel="whatsapp",
        context={"session_memory": {"active_goal": "booking"}},
    )
    user_message = SimpleNamespace(message_metadata={})
    bot_response = SimpleNamespace(message_metadata={})
    loaded_state = SimpleNamespace(
        context=conversation.context,
        dialog_state=DialogState.model_validate({}),
        booking_state={},
    )

    runtime._load_runtime_state = lambda *_args, **_kwargs: loaded_state
    runtime._send_and_persist_reply = lambda *args, **kwargs: bot_response

    response, _returned_state = runtime._handle_control_turn(
        object(),
        payload=SimpleNamespace(body=SimpleNamespace(message="новый вопрос")),
        prepared=SimpleNamespace(conversation=conversation, user_message=user_message),
        runtime_state=loaded_state,
        now=datetime(2026, 3, 31, 12, 0, tzinfo=timezone.utc),
        enqueue_only=False,
        skip_persist=False,
    )

    assert response is not None
    expected_meta = {
        "source": "consultant_runtime",
        "control_action": "session_reset",
        "control_reason": "explicit_reset",
        "control_source": "session_memory",
        "session_memory_reset": "explicit_reset",
    }
    assert user_message.message_metadata["decision_meta"] == expected_meta
    assert bot_response.message_metadata["decision_meta"] == expected_meta
    assert "action" not in expected_meta
    assert "intent" not in expected_meta
    assert "outcome" not in expected_meta


def test_consultant_runtime_reset_runtime_context_clears_touched_slice_carryover() -> None:
    runtime = ConsultantRuntime()
    conversation = SimpleNamespace(
        context={
            "context_manager": {
                "message_count": 7,
                "class_carryover": {
                    "class": "info_bundle",
                    "message_count": 7,
                    "ttl": 4,
                },
                "canonical_dialog_state": {
                    "owner_id": "context_manager.dialog_state.v1",
                    "version": "v1",
                    "meta": {
                        "class_carryover": {
                            "class": "info_bundle",
                            "message_count": 7,
                            "ttl": 4,
                        }
                    },
                },
            },
            "session_memory": {"active_goal": "info"},
        }
    )

    snapshot = runtime._reset_runtime_context(
        conversation,
        now=datetime(2026, 3, 30, 14, 0, tzinfo=timezone.utc),
        reason="explicit_reset",
    )

    assert snapshot["active_goal"] == "info"
    assert "session_memory" not in conversation.context
    assert conversation.context["context_manager"] == {
        "message_count": 7,
        "canonical_dialog_state": {
            "owner_id": "context_manager.dialog_state.v1",
            "version": "v1",
            "current_referents": {},
        },
    }


def test_consultant_runtime_trace_prefers_policy_core_semantic_contract_over_runtime_projection() -> None:
    runtime = ConsultantRuntime()
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "goal": "booking",
            "capability": "bookability",
            "subject_kind": "service",
            "entity_refs": [
                {
                    "entity_type": "service",
                    "value": "Покрытие гель-лак",
                    "source_ref": "user_intent",
                }
            ],
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="ask_about_requested_slot",
        source="llm_policy_core",
    )
    dialog_state = DialogState.model_validate(
        {
            "pending_question_contract": {
                "expected_reply_type": "time",
                "reason": "collect:datetime",
                "next_question": "datetime",
                "open_questions": ["datetime"],
            },
            "projections": {
                "expected_reply_type": "time",
                "expected_reply_reason": "collect:datetime",
            },
            "meta": {
                "current_goal": "booking",
                "semantic_contract": {
                    "capability": "bookability",
                    "subject_kind": "service",
                    "referents": {
                        "service": {
                            "value": "Покрытие гель-лак",
                            "source_ref": "runtime_grounding",
                        }
                    },
                },
            },
        }
    )
    conversation = SimpleNamespace(context={}, state="bot_active")
    user_message = SimpleNamespace(message_metadata={})
    execution = SimpleNamespace(tool_action="collect", tool_decision="datetime", meta={})
    turn_result = SimpleNamespace(dialog_state=dialog_state, reply=SimpleNamespace(reply_kind="collect"))

    runtime._record_turn_trace(
        conversation=conversation,
        user_message=user_message,
        bot_response=None,
        decision=decision,
        execution=execution,
        turn_result=turn_result,
        delivered=True,
    )

    trace = conversation.context.get("decision_trace") or []
    assert any(
        entry.get("stage") == "consultant_runtime"
        and (
            (entry.get("semantic_contract", {}).get("entity_refs") or [{}])[0].get("source_ref")
            == "user_intent"
        )
        for entry in trace
    )
    decision_meta = (user_message.message_metadata or {}).get("decision_meta") or {}
    assert (
        decision_meta.get("semantic_contract", {})
        .get("entity_refs", [{}])[0]
        .get("source_ref")
        == "user_intent"
    )


def test_consultant_runtime_trace_prefers_materialized_frame_over_stale_legacy_carriers() -> None:
    runtime = ConsultantRuntime()
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "goal": "booking",
            "reason": "collect:datetime",
            "capability": "bookability",
            "subject_kind": "service",
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "expected_reply_type": "time",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="ask_about_requested_slot",
        source="llm_policy_core",
    )
    now = datetime.now(timezone.utc)
    _, dialog_state, _ = DialogStateService().write_runtime_payload(
        {},
        decision=decision,
        execution_meta={"next_slot": "datetime"},
        now=now,
    )
    dialog_state.meta["current_goal"] = "handoff"
    dialog_state.meta["semantic_contract"] = {
        "contract_version": "semantic_contract.v1",
        "capability": "stale_meta",
        "referents": {
            "service": {
                "value": "Педикюр",
                "entity_type": "service",
                "source_ref": "stale_meta",
            }
        },
    }
    dialog_state.current_referents.service = "Педикюр"
    dialog_state.pending_question_contract.expected_reply_type = "name"
    dialog_state.pending_question_contract.reason = "stale_projection"
    dialog_state.pending_question_contract.next_question = "name"
    dialog_state.pending_question_contract.open_questions = ["name"]
    dialog_state.projections.expected_reply_type = "name"
    dialog_state.projections.expected_reply_reason = "stale_projection"

    conversation = SimpleNamespace(context={}, state="bot_active")
    user_message = SimpleNamespace(message_metadata={})
    execution = SimpleNamespace(tool_action="collect", tool_decision="datetime", meta={})
    turn_result = SimpleNamespace(dialog_state=dialog_state, reply=SimpleNamespace(reply_kind="collect"))

    runtime._record_turn_trace(
        conversation=conversation,
        user_message=user_message,
        bot_response=None,
        decision=decision,
        execution=execution,
        turn_result=turn_result,
        delivered=True,
    )

    trace = conversation.context.get("decision_trace") or []
    assert any(
        entry.get("stage") == "consultant_runtime"
        and entry.get("semantic_contract", {}).get("capability") == "bookability"
        and entry.get("semantic_contract", {}).get("referents", {}).get("service", {}).get("value")
        == "Маникюр"
        and entry.get("pending_question_contract", {}).get("next_question") == "datetime"
        and entry.get("expected_reply_type") == "time"
        for entry in trace
    )
    decision_meta = (user_message.message_metadata or {}).get("decision_meta") or {}
    assert decision_meta["semantic_contract"]["capability"] == "bookability"
    assert decision_meta["semantic_contract"]["referents"]["service"] == {
        "value": "Маникюр",
        "entity_id": "svc:manicure",
        "entity_type": "service",
        "source_ref": "message",
    }
    assert decision_meta["pending_question_contract"] == {
        "expected_reply_type": "time",
        "reason": "collect:datetime",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }


def test_turn_executor_omits_empty_pending_question_contract_from_execution_meta() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "hours",
            "action": "fact",
            "tool_action": "catalog.service_query",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    assert TurnExecutor._build_execution_pending_question_contract(decision) is None


def test_turn_executor_realizes_consult_media_followup_on_owner_path() -> None:
    planner = TurnPlanner()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "consult",
            "action": "collect",
            "tool_action": "consult",
            "goal": "consult",
            "reason": "user_offers_photos_for_style_reference",
            "capability": "consultation",
            "pack_refs": ["style_reference"],
            "expected_reply_type": "media",
            "next_question": "media",
            "open_questions": ["media"],
        }
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Я могу прислать фото своих ногтей.",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime(2026, 3, 30, 12, 0, tzinfo=timezone.utc),
    )

    assert result.text == "Пришлите, пожалуйста, фото-пример желаемого результата."
    assert result.tool_action == "collect"
    assert result.tool_decision == "media"
    assert result.meta["next_slot"] == "media"


def test_dialog_state_service_projects_booking_resume_contract_for_active_media_followup() -> None:
    resume_contract = DialogStateService().project_interrupt_resume_pending_question_contract(
        {
            "expected_reply_type": "media",
            "next_question": "media",
            "open_questions": ["media"],
        },
        current_goal="booking",
        booking_payload={"service": "Маникюр"},
    )

    assert resume_contract == {
        "expected_reply_type": "time",
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
    }


def test_consultant_runtime_exposes_resume_contract_for_active_media_followup() -> None:
    planner = TurnPlanner()
    runtime = ConsultantRuntime()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "consult",
            "action": "collect",
            "tool_action": "consult",
            "goal": "booking",
            "reason": "user_offers_photo_reference_before_time_selection",
            "capability": "bookability",
            "pack_refs": ["style_reference"],
            "expected_reply_type": "media",
            "next_question": "media",
            "open_questions": ["media"],
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
        }
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )
    execution = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Вот фото референса",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "Маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc),
    )

    updated, dialog_state, booking_payload = DialogStateService().write_runtime_payload(
        {},
        decision=decision,
        execution_meta=execution.meta,
        now=datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc),
    )
    runtime_state = LoadedRuntimeState(
        context=updated,
        dialog_state=dialog_state,
        booking_state=booking_payload or {},
    )

    profile = runtime._build_policy_core_memory_profile(runtime_state)

    assert profile["pending_question_contract"] == {
        "expected_reply_type": "media",
        "reason": "user_offers_photo_reference_before_time_selection",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
        "next_question": "media",
        "open_questions": ["media"],
    }
    assert profile["resume_pending_question_contract"] == {
        "expected_reply_type": "time",
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
    }


def test_consultant_runtime_preserves_consult_media_followup_without_booking_goal_pollution() -> None:
    planner = TurnPlanner()
    service = DialogStateService()
    runtime = ConsultantRuntime()
    now = datetime(2026, 3, 30, 12, 5, tzinfo=timezone.utc)
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "consult",
            "action": "collect",
            "tool_action": "consult",
            "goal": "consult",
            "reason": "user_offers_photos_for_style_reference",
            "capability": "consultation",
            "pack_refs": ["style_reference"],
            "expected_reply_type": "media",
            "next_question": "media",
            "open_questions": ["media"],
        }
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )
    execution = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Я могу прислать фото своих ногтей.",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=now,
    )

    updated, dialog_state, booking_payload = service.write_runtime_payload(
        {},
        decision=decision,
        execution_meta=execution.meta,
        now=now,
    )

    assert booking_payload is None
    assert "booking" not in updated["consultant_runtime"]
    assert dialog_state.pending_question_contract.model_dump(mode="json", exclude_none=True) == {
        "expected_reply_type": "media",
        "reason": "user_offers_photos_for_style_reference",
        "next_question": "media",
        "open_questions": ["media"],
    }
    assert dialog_state.interaction_state.resume_slot == "media"
    assert dialog_state.meta["current_goal"] == "consult"
    assert dialog_state.semantic_state.materialized_frame.reason == "user_offers_photos_for_style_reference"
    assert dialog_state.meta["semantic_contract"]["capability"] == "consultation"

    loaded = service.load_runtime_payload(updated)
    assert loaded["expected_reply_type"] == "media"
    assert loaded["expected_reply_reason"] == "user_offers_photos_for_style_reference"
    assert loaded["current_goal"] == "consult"
    assert loaded["dialog_state"].pending_question_contract.next_question == "media"

    conversation = SimpleNamespace(context=updated, state="bot_active")
    user_message = SimpleNamespace(message_metadata={})
    turn_result = TurnExecutor().assemble(
        decision=decision,
        dialog_state=dialog_state,
        reply=ResponseRealizer().realize(decision, text=execution.text),
        stages=["ingress", "planner", "boundary", "state", "executor", "realizer"],
    )

    runtime._record_turn_trace(
        conversation=conversation,
        user_message=user_message,
        bot_response=None,
        decision=decision,
        execution=execution,
        turn_result=turn_result,
        delivered=True,
    )

    runtime_entry = next(
        entry
        for entry in conversation.context.get("decision_trace") or []
        if entry.get("stage") == "consultant_runtime"
    )
    runtime_trace_contract = RuntimeTraceContractV1.model_validate(
        runtime_entry["runtime_trace_contract"]
    )
    assert runtime_trace_contract.state_transition.current_goal == "consult"
    assert runtime_trace_contract.state_transition.pending_question_contract == {
        "expected_reply_type": "media",
        "reason": "user_offers_photos_for_style_reference",
        "next_question": "media",
        "open_questions": ["media"],
    }

    decision_meta = (user_message.message_metadata or {}).get("decision_meta") or {}
    assert decision_meta["pending_question_contract"] == {
        "expected_reply_type": "media",
        "reason": "user_offers_photos_for_style_reference",
        "next_question": "media",
        "open_questions": ["media"],
    }
    assert decision_meta["runtime_trace_contract"]["state_transition"]["current_goal"] == "consult"


def test_consultant_runtime_refreshes_core_trace_stages_for_current_media_turn() -> None:
    planner = TurnPlanner()
    service = DialogStateService()
    runtime = ConsultantRuntime()
    now = datetime(2026, 3, 30, 12, 5, tzinfo=timezone.utc)
    semantic_payload = {
        "intent": "consult",
        "action": "collect",
        "tool_action": "consult",
        "goal": "booking",
        "reason": "user_offers_photos_for_style_reference",
        "capability": "consultation",
        "pack_refs": ["style_reference"],
        "slots": {"service": "маникюр"},
        "referents": {
            "service": {
                "value": "маникюр",
                "entity_id": "svc:manicure",
                "entity_type": "service",
                "source_ref": "user_message",
            }
        },
        "subject_kind": "service",
        "temporal_scope": "none",
        "resolution_mode": "direct",
        "expected_reply_type": "media",
        "next_question": "media",
        "open_questions": ["media"],
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
    }
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(semantic_payload)
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )
    decision.meta["policy_core_trace"] = {
        "attempted": True,
        "status": "ok",
        "schema_verdict": "ok",
        "projection_verdict": "ok",
        "input": {
            "message": "Могу прислать фото своих ногтей.",
        },
        "raw_output": json.dumps(semantic_payload, ensure_ascii=False),
    }
    execution = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Могу прислать фото своих ногтей.",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=now,
    )
    updated, dialog_state, _ = service.write_runtime_payload(
        {},
        decision=decision,
        execution_meta=execution.meta,
        now=now,
    )
    conversation = SimpleNamespace(
        context={
            **updated,
            "decision_trace": [
                {
                    "stage": "policy_core",
                    "raw_output": "{\"intent\":\"booking\",\"expected_reply_type\":\"time\"}",
                },
                {
                    "stage": "pending_question_interaction",
                    "expected_reply_type": "time",
                    "pending_question_target": "time",
                },
                {
                    "stage": "question_contract",
                    "expected_reply_type": "time",
                    "reason": "booking_collect_requested_time_for_service",
                },
                {
                    "stage": "policy_validation_boundary",
                    "reason_code": "boundary:test",
                },
                {
                    "stage": "consultant_runtime",
                    "expected_reply_type": "time",
                    "tool_decision": "datetime",
                },
            ],
        },
        state="bot_active",
    )
    user_message = SimpleNamespace(message_metadata={})
    turn_result = TurnExecutor().assemble(
        decision=decision,
        dialog_state=dialog_state,
        reply=ResponseRealizer().realize(decision, text=execution.text),
        stages=["ingress", "planner", "boundary", "state", "executor", "realizer"],
    )

    runtime._record_turn_trace(
        conversation=conversation,
        user_message=user_message,
        bot_response=None,
        decision=decision,
        execution=execution,
        turn_result=turn_result,
        delivered=True,
    )

    trace = conversation.context.get("decision_trace") or []
    assert any(
        entry.get("stage") == "policy_validation_boundary"
        and entry.get("reason_code") == "boundary:test"
        for entry in trace
    )
    assert not any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        and entry.get("reason") == "booking_collect_requested_time_for_service"
        for entry in trace
    )
    assert any(
        entry.get("stage") == "policy_core"
        and entry.get("input", {}).get("message") == "Могу прислать фото своих ногтей."
        and "\"expected_reply_type\": \"media\"" in str(entry.get("raw_output"))
        for entry in trace
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "media"
        and entry.get("pending_question_contract", {}).get("next_question") == "media"
        for entry in trace
    )


def test_consultant_runtime_records_referent_followup_axes_in_trace_and_meta() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "tool_args": {},
            "entity_refs": [
                {
                    "entity_id": "spec:aigerim",
                    "entity_type": "specialist",
                    "value": "Айгерим",
                    "source_ref": "message",
                }
            ],
            "referents": {
                "specialist": {
                    "value": "Айгерим",
                    "entity_id": "spec:aigerim",
                    "entity_type": "specialist",
                    "source_ref": "message",
                }
            },
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "goal": "booking",
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="referent_followup",
        source="llm_policy_core",
    )
    execution_meta = {
        "slot_values": {"service": "Маникюр"},
        "next_slot": "datetime",
    }
    now = datetime.now(timezone.utc)
    _, dialog_state, _ = DialogStateService().write_runtime_payload(
        {},
        decision=decision,
        execution_meta=execution_meta,
        now=now,
    )
    runtime = ConsultantRuntime()
    conversation = SimpleNamespace(context={}, state="bot_active")
    user_message = SimpleNamespace(message_metadata={})
    execution = SimpleNamespace(tool_action="collect", tool_decision="datetime", meta=execution_meta)
    turn_result = SimpleNamespace(dialog_state=dialog_state, reply=SimpleNamespace(reply_kind="collect"))

    runtime._record_turn_trace(
        conversation=conversation,
        user_message=user_message,
        bot_response=None,
        decision=decision,
        execution=execution,
        turn_result=turn_result,
        delivered=True,
    )

    trace = conversation.context.get("decision_trace") or []
    assert any(
        entry.get("stage") == "consultant_runtime"
        and entry.get("pending_question_target") == "specialist"
        and entry.get("active_question_relation") == "referent_followup"
        for entry in trace
    )
    decision_meta = (user_message.message_metadata or {}).get("decision_meta") or {}
    assert decision_meta.get("pending_question_target") == "specialist"
    assert decision_meta.get("active_question_relation") == "referent_followup"
    assert decision_meta["semantic_contract"]["referents"]["specialist"] == {
        "value": "Айгерим",
        "entity_id": "spec:aigerim",
        "entity_type": "specialist",
        "source_ref": "message",
    }
    assert decision_meta.get("pending_question_contract") == {
        "expected_reply_type": "time",
        "reason": "collect:datetime",
        "pending_question_target": "specialist",
        "active_question_relation": "referent_followup",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }


def test_consultant_runtime_records_tool_execution_projection_in_trace_and_meta() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "pricing",
            "action": "fact",
            "tool_action": "info",
            "tool_args": {},
            "entity_refs": [
                {
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "value": "маникюр",
                    "source_ref": "message",
                }
            ],
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "subject_kind": "service",
            "capability": "pricing",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "goal": "info",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="generic_info_interrupt",
        source="llm_policy_core",
    )
    now = datetime.now(timezone.utc)
    _, dialog_state, _ = DialogStateService().write_runtime_payload(
        {},
        decision=decision,
        execution_meta={},
        now=now,
    )
    runtime = ConsultantRuntime()
    conversation = SimpleNamespace(context={}, state="bot_active")
    user_message = SimpleNamespace(message_metadata={})
    execution = SimpleNamespace(
        tool_action="catalog.service_query",
        tool_decision="price_query",
        meta={
            "tool_execution_projection": {
                "projection_source": "semantic_contract",
                "service_query": "маникюр",
            }
        },
    )
    turn_result = SimpleNamespace(dialog_state=dialog_state, reply=SimpleNamespace(reply_kind="fact"))

    runtime._record_turn_trace(
        conversation=conversation,
        user_message=user_message,
        bot_response=None,
        decision=decision,
        execution=execution,
        turn_result=turn_result,
        delivered=True,
    )

    trace = conversation.context.get("decision_trace") or []
    assert any(
        entry.get("stage") == "consultant_runtime"
        and entry.get("tool_execution_projection") == {
            "projection_source": "semantic_contract",
            "service_query": "маникюр",
        }
        and entry.get("semantic_contract", {}).get("referents", {}).get("service") == {
            "value": "маникюр",
            "entity_id": "svc:manicure",
            "entity_type": "service",
            "source_ref": "message",
        }
        for entry in trace
    )
    decision_meta = (user_message.message_metadata or {}).get("decision_meta") or {}
    assert decision_meta.get("tool_execution_projection") == {
        "projection_source": "semantic_contract",
        "service_query": "маникюр",
    }
    assert decision_meta["semantic_contract"]["referents"]["service"] == {
        "value": "маникюр",
        "entity_id": "svc:manicure",
        "entity_type": "service",
        "source_ref": "message",
    }


def test_consultant_runtime_memory_profile_uses_canonical_pending_question_contract_only() -> None:
    runtime = ConsultantRuntime()
    dialog_state = DialogState.model_validate(
        {
            "schema_version": "dialog_state.v1",
            "semantic_state": {
                "schema_version": "canonical_semantic_state.v1",
                "materialized_frame": {
                    "schema_version": "semantic_frame.v2",
                    "user_goal": "booking",
                    "requested_effect": "collect_missing_input",
                    "subject": {"kind": "booking"},
                    "referents": {
                        "service": {
                            "value": "Маникюр",
                            "entity_id": "svc:manicure",
                            "entity_type": "service",
                            "source_ref": "memory",
                        }
                    },
                    "constraints": {},
                    "preferences": {},
                    "continuation": {
                        "expected_reply_type": "name",
                        "reason": "calendar_get_booking_collect_reference",
                        "next_question": "name",
                        "open_questions": ["name"],
                    },
                    "capability_selection": {
                        "capability": "booking_manage",
                    },
                    "needs_human": False,
                    "reason": "calendar_get_booking_collect_reference",
                },
                "event_log": [],
            },
            "current_referents": {
                "service": "Маникюр",
                "specialist": None,
                "branch": None,
                "booking": None,
                "customer": None,
            },
            "pending_question_contract": {
                "expected_reply_type": "name",
                "reason": "calendar_get_booking_collect_reference",
                "next_question": "name",
                "open_questions": ["name"],
            },
            "interaction_state": {
                "interaction_owner": "llm_policy_core",
            },
            "projections": {
                "expected_reply_type": "name",
                "expected_reply_reason": "calendar_get_booking_collect_reference",
            },
            "meta": {
                "semantic_contract": {
                    "contract_version": "semantic_contract.v1",
                    "subject_kind": "service",
                    "capability": "pricing",
                    "resolution_mode": "direct",
                    "referents": {
                        "service": {
                            "value": "Педикюр",
                            "entity_id": "svc:pedicure",
                            "entity_type": "service",
                            "source_ref": "stale_meta",
                        }
                    },
                }
            },
        }
    )
    runtime_state = SimpleNamespace(
        current_goal="booking",
        booking_state={"service": "Маникюр"},
        dialog_state=dialog_state,
        expected_reply_type="time",
        expected_reply_reason="collect:datetime",
    )

    profile = runtime._build_policy_core_memory_profile(runtime_state)

    assert profile["pending_question_contract"] == {
        "expected_reply_type": "name",
        "reason": "calendar_get_booking_collect_reference",
        "next_question": "name",
        "open_questions": ["name"],
    }
    assert profile["semantic_contract"]["subject_kind"] == "booking"
    assert profile["semantic_contract"]["capability"] == "booking_manage"
    assert profile["semantic_contract"]["referents"]["service"] == {
        "value": "Маникюр",
        "entity_id": "svc:manicure",
        "entity_type": "service",
        "source_ref": "memory",
    }
    assert "current_referents" not in profile
    assert "interaction_state" not in profile
    assert "active_slots" not in profile


def test_consultant_runtime_memory_profile_uses_state_written_semantic_decision_contract_from_executor_enrichment() -> None:
    runtime = ConsultantRuntime()
    service = DialogStateService()
    planner = TurnPlanner()
    now = datetime(2026, 3, 27, 12, 30, tzinfo=timezone.utc)
    expected_pending_question_contract = {
        "expected_reply_type": "time",
        "reason": "collect:datetime",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }
    expected_specialist_referent = {
        "value": "Айгерим",
        "entity_id": "spc:aigerim",
        "entity_type": "specialist",
        "source_ref": "execution",
    }
    expected_grounding_provenance = {
        "pack_id": "demo_salon",
        "resolver_id": "catalog",
    }
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "action": "collect",
            "intent": "booking",
            "goal": "booking",
            "capability": "booking_manage",
            "tool_action": "calendar.book_slot",
            "slots": {"service": "Маникюр"},
            "subject_kind": "booking",
            "resolution_mode": "ask_about_requested_slot",
            "expected_reply_type": "time",
            "reason": "collect:datetime",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "memory",
                }
            },
        }
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="calendar.book_slot",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    updated, _, _ = service.write_runtime_payload(
        {
            "consultant_runtime": {
                "schema_version": "consultant_runtime.v1",
                "dialog_state": {
                    "schema_version": "dialog_state.v1",
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "reason": "stale_reason",
                        "next_question": "name",
                        "open_questions": ["name"],
                    },
                    "interaction_state": {
                        "interaction_owner": "stale_owner",
                    },
                    "meta": {
                        "writer": "dialog_state_service",
                        "current_goal": "booking",
                        "semantic_contract": {
                            "contract_version": "semantic_contract.v1",
                            "capability": "pricing",
                            "subject_kind": "service",
                        },
                    },
                },
                "booking": {
                    "active": True,
                    "service": "Маникюр",
                    "last_question": "datetime",
                },
            }
        },
        decision=decision,
        execution_meta={
            "semantic_enrichment": {
                "referents": {
                    "specialist": dict(expected_specialist_referent)
                },
                "grounding_provenance": dict(expected_grounding_provenance),
            },
            "slot_values": {"service": "Маникюр"},
        },
        now=now,
    )
    loaded = service.load_runtime_payload(updated)
    runtime_state = SimpleNamespace(
        current_goal=loaded["current_goal"],
        booking_state=loaded["booking_payload"],
        dialog_state=loaded["dialog_state"],
        expected_reply_type=loaded["expected_reply_type"],
        expected_reply_reason=loaded["expected_reply_reason"],
    )

    profile = runtime._build_policy_core_memory_profile(runtime_state)

    assert profile["pending_question_contract"] == expected_pending_question_contract
    assert profile["semantic_contract"]["capability"] == "booking_manage"
    assert profile["semantic_contract"]["subject_kind"] == "booking"
    assert profile["semantic_contract"]["pending_question_target"] == "time"
    assert profile["semantic_contract"]["active_question_relation"] == "ask_about_requested_slot"
    assert profile["semantic_contract"]["grounding_provenance"] == expected_grounding_provenance
    assert profile["semantic_contract"]["referents"]["specialist"] == expected_specialist_referent

    conversation = SimpleNamespace(context={}, state="bot_active")
    user_message = SimpleNamespace(message_metadata={})
    execution = SimpleNamespace(
        tool_action="calendar.book_slot",
        tool_decision="datetime",
        meta={
            "semantic_enrichment": {
                "referents": {"specialist": dict(expected_specialist_referent)},
                "grounding_provenance": dict(expected_grounding_provenance),
            },
            "tool_execution_projection": {
                "projection_source": "semantic_contract",
                "service_query": "Маникюр",
            },
        },
    )
    turn_result = SimpleNamespace(
        dialog_state=runtime_state.dialog_state,
        reply=SimpleNamespace(reply_kind="collect"),
    )

    runtime._record_turn_trace(
        conversation=conversation,
        user_message=user_message,
        bot_response=None,
        decision=decision,
        execution=execution,
        turn_result=turn_result,
        delivered=True,
    )

    trace = conversation.context.get("decision_trace") or []
    assert any(
        entry.get("stage") == "consultant_runtime"
        and entry.get("semantic_contract", {}).get("referents", {}).get("specialist")
        == expected_specialist_referent
        and entry.get("semantic_contract", {}).get("grounding_provenance")
        == expected_grounding_provenance
        and entry.get("pending_question_contract") == expected_pending_question_contract
        and entry.get("tool_execution_projection") == {
            "projection_source": "semantic_contract",
            "service_query": "Маникюр",
        }
        for entry in trace
    )
    decision_meta = (user_message.message_metadata or {}).get("decision_meta") or {}
    assert decision_meta["semantic_contract"]["referents"]["specialist"] == expected_specialist_referent
    assert decision_meta["semantic_contract"]["grounding_provenance"] == expected_grounding_provenance
    assert decision_meta["pending_question_contract"] == expected_pending_question_contract


def test_consultant_runtime_memory_profile_prefers_materialized_frame_over_stale_legacy_carriers() -> None:
    runtime = ConsultantRuntime()
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "goal": "booking",
            "reason": "collect:datetime",
            "capability": "bookability",
            "subject_kind": "service",
            "slots": {"service": "Маникюр"},
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "expected_reply_type": "time",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="ask_about_requested_slot",
        source="llm_policy_core",
    )
    now = datetime.now(timezone.utc)
    _, dialog_state, _ = DialogStateService().write_runtime_payload(
        {},
        decision=decision,
        execution_meta={"next_slot": "datetime"},
        now=now,
    )
    dialog_state.meta["current_goal"] = "handoff"
    dialog_state.meta["semantic_contract"] = {
        "contract_version": "semantic_contract.v1",
        "capability": "stale_meta",
        "referents": {
            "service": {
                "value": "Педикюр",
                "entity_type": "service",
                "source_ref": "stale_meta",
            }
        },
    }
    dialog_state.current_referents.service = "Педикюр"
    dialog_state.pending_question_contract.expected_reply_type = "name"
    dialog_state.pending_question_contract.reason = "stale_projection"
    dialog_state.pending_question_contract.next_question = "name"
    dialog_state.pending_question_contract.open_questions = ["name"]
    dialog_state.projections.expected_reply_type = "name"
    dialog_state.projections.expected_reply_reason = "stale_projection"

    profile = runtime._build_policy_core_memory_profile(
        SimpleNamespace(
            booking_state={},
            dialog_state=dialog_state,
        )
    )

    assert profile["active_goal"] == "booking"
    assert profile["semantic_contract"]["capability"] == "bookability"
    assert profile["semantic_contract"]["referents"]["service"] == {
        "value": "Маникюр",
        "entity_id": "svc:manicure",
        "entity_type": "service",
        "source_ref": "message",
    }
    assert profile["pending_question_contract"] == {
        "expected_reply_type": "time",
        "reason": "collect:datetime",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }
    assert profile["slot_state"] == {"service": "Маникюр"}


def test_consultant_runtime_contract_action_prefers_materialized_frame_over_stale_legacy_carriers() -> None:
    runtime = ConsultantRuntime()
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "goal": "booking",
            "reason": "collect:datetime",
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="ask_about_requested_slot",
        source="llm_policy_core",
    )
    now = datetime.now(timezone.utc)
    _, dialog_state, _ = DialogStateService().write_runtime_payload(
        {},
        decision=decision,
        execution_meta={"next_slot": "datetime"},
        now=now,
    )
    dialog_state.meta["current_goal"] = "handoff"
    dialog_state.pending_question_contract.expected_reply_type = "name"
    dialog_state.pending_question_contract.reason = "stale_projection"
    dialog_state.pending_question_contract.next_question = "name"
    dialog_state.pending_question_contract.open_questions = ["name"]
    dialog_state.projections.expected_reply_type = "name"
    dialog_state.projections.expected_reply_reason = "stale_projection"

    action = runtime._derive_contract_action(
        decision=decision,
        execution=SimpleNamespace(tool_action="collect", tool_decision="datetime", meta={}),
        turn_result=SimpleNamespace(
            dialog_state=dialog_state,
            reply=SimpleNamespace(reply_kind="collect"),
        ),
    )

    assert action == "booking_prompt"


def test_consultant_runtime_owner_backed_semantic_contract_ignores_stale_state_fields() -> None:
    runtime = ConsultantRuntime()
    planner = TurnPlanner()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "goal": "booking",
            "reason": "collect:datetime",
            "capability": "bookability",
            "subject_kind": "service",
            "resolution_mode": "ask_about_requested_slot",
            "slots": {"service": "Маникюр"},
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "expected_reply_type": "time",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        }
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )
    dialog_state = DialogState.model_validate(
        {
            "schema_version": "dialog_state.v1",
            "pending_question_contract": {
                "expected_reply_type": "name",
                "reason": "stale_projection",
                "next_question": "name",
                "open_questions": ["name"],
            },
            "projections": {
                "expected_reply_type": "name",
                "expected_reply_reason": "stale_projection",
            },
            "meta": {
                "current_goal": "handoff",
                "semantic_contract": {
                    "contract_version": "semantic_contract.v1",
                    "capability": "stale_meta",
                    "subject_kind": "branch",
                    "referents": {
                        "service": {
                            "value": "Педикюр",
                            "entity_id": "svc:pedicure",
                            "entity_type": "service",
                            "source_ref": "stale_meta",
                        }
                    },
                },
            },
        }
    )
    execution = SimpleNamespace(
        meta={
            "semantic_contract": {
                "contract_version": "semantic_contract.v1",
                "capability": "stale_execution",
                "referents": {
                    "specialist": {
                        "value": "Айгерим",
                        "entity_id": "spc:aigerim",
                        "entity_type": "specialist",
                        "source_ref": "execution",
                    }
                },
                "grounding_provenance": {
                    "pack_id": "demo_salon",
                    "resolver_id": "catalog",
                },
            }
        }
    )

    semantic_contract = runtime._project_runtime_semantic_contract(
        dialog_state,
        decision=decision,
        execution=execution,
    )

    assert semantic_contract["capability"] == "bookability"
    assert semantic_contract["subject_kind"] == "service"
    assert semantic_contract["referents"]["service"] == {
        "value": "Маникюр",
        "entity_id": "svc:manicure",
        "entity_type": "service",
        "source_ref": "message",
    }
    assert semantic_contract["referents"]["specialist"] == {
        "value": "Айгерим",
        "entity_id": "spc:aigerim",
        "entity_type": "specialist",
        "source_ref": "execution",
    }
    assert semantic_contract["grounding_provenance"] == {
        "pack_id": "demo_salon",
        "resolver_id": "catalog",
    }


def test_consultant_runtime_owner_backed_pending_question_contract_drops_stale_state() -> None:
    runtime = ConsultantRuntime()
    planner = TurnPlanner()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "hours",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "goal": "info",
            "reason": "hours_lookup",
            "capability": "hours",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
        }
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="catalog.service_query",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )
    dialog_state = DialogState.model_validate(
        {
            "schema_version": "dialog_state.v1",
            "pending_question_contract": {
                "expected_reply_type": "name",
                "reason": "stale_projection",
                "next_question": "name",
                "open_questions": ["name"],
            },
            "projections": {
                "expected_reply_type": "name",
                "expected_reply_reason": "stale_projection",
            },
            "meta": {"current_goal": "booking"},
        }
    )

    pending_question_contract = runtime._project_runtime_pending_question_contract(
        dialog_state,
        decision=decision,
    )

    assert pending_question_contract == {}


def test_consultant_runtime_contract_action_prefers_owner_goal_on_owner_backed_turn() -> None:
    runtime = ConsultantRuntime()
    planner = TurnPlanner()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "goal": "booking",
            "reason": "collect:datetime",
            "capability": "bookability",
            "subject_kind": "service",
            "resolution_mode": "ask_about_requested_slot",
            "expected_reply_type": "time",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        }
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )
    dialog_state = DialogState.model_validate(
        {
            "schema_version": "dialog_state.v1",
            "pending_question_contract": {
                "expected_reply_type": "name",
                "reason": "stale_projection",
                "next_question": "name",
                "open_questions": ["name"],
            },
            "projections": {
                "expected_reply_type": "name",
                "expected_reply_reason": "stale_projection",
            },
            "meta": {"current_goal": "handoff"},
        }
    )

    action = runtime._derive_contract_action(
        decision=decision,
        execution=SimpleNamespace(tool_action="collect", tool_decision="datetime", meta={}),
        turn_result=SimpleNamespace(
            dialog_state=dialog_state,
            reply=SimpleNamespace(reply_kind="collect"),
        ),
    )

    assert action == "booking_prompt"


def test_consultant_runtime_contract_action_prefers_binding_plan_collect_when_outcome_is_stale() -> None:
    runtime = ConsultantRuntime()
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "fact",
            "tool_action": "calendar.list_slots",
        },
        interaction_owner="legacy_booking_flow",
        interaction_relation="ask_about_requested_slot",
        source="legacy_runtime",
    )
    decision.outcome = "FACT"
    decision.binding_plan = BindingPlanV1.model_validate(
        _binding_plan_payload()
        | {
            "decision_id": "binding-non-owner-booking-prompt",
            "binding_outcome_type": "workflow_advance",
            "capability_id": "bookability",
            "selected_tool_or_workflow_ref": "collect",
            "resolved_args": {},
            "idempotency_key": "binding-non-owner-booking-prompt",
        }
    )
    dialog_state = DialogState.model_validate(
        {
            "schema_version": "dialog_state.v1",
            "pending_question_contract": {
                "expected_reply_type": "time",
                "reason": "collect:datetime",
                "next_question": "datetime",
                "open_questions": ["datetime"],
            },
            "projections": {
                "expected_reply_type": "time",
                "expected_reply_reason": "collect:datetime",
            },
            "meta": {"current_goal": "booking"},
        }
    )

    action = runtime._derive_contract_action(
        decision=decision,
        execution=SimpleNamespace(tool_action="collect", tool_decision="datetime", meta={}),
        turn_result=SimpleNamespace(
            dialog_state=dialog_state,
            reply=SimpleNamespace(reply_kind="collect"),
        ),
    )

    assert action == "booking_prompt"


def test_turn_planner_builds_canonical_semantic_frame_v2() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "fact",
            "tool_action": "calendar.book_slot",
            "tool_action_hint": "calendar.book_slot",
            "goal": "booking",
            "reason": "final_name_collected",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "direct",
            "temporal_scope": "specific_time",
            "slots": {
                "service": "Маникюр",
                "datetime": "2026-03-27T15:00:00+05:00",
                "name": "Алина",
            },
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "memory",
                }
            },
            "entity_refs": [
                {
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "value": "Маникюр",
                    "source_ref": "memory",
                }
            ],
            "expected_reply_type": "name",
            "pending_question_act": "fill_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "fill_requested_slot",
            "next_question": "name",
            "open_questions": ["name"],
        },
        interaction_owner="llm_policy_core",
        source="policy_core",
    )

    canonical_frame = TurnPlanner().canonical_semantic_frame(decision)
    canonical_contract = TurnPlanner().canonical_semantic_contract(decision)

    assert decision.semantic_frame.schema_version == "semantic_frame.v2"
    assert decision.semantic_frame.user_goal == "booking"
    assert decision.semantic_frame.requested_effect == "commit_booking"
    assert decision.semantic_frame.subject["kind"] == "service"
    assert decision.semantic_frame.subject["value"] == "Маникюр"
    assert decision.semantic_frame.continuation["next_question"] == "name"
    assert decision.semantic_frame.continuation["slot_values"]["service"] == "Маникюр"
    assert decision.semantic_frame.capability_selection["capability"] == "bookability"
    assert decision.semantic_frame.capability_selection["tool_action_hint"] == "calendar.book_slot"
    assert decision.meta["semantic_contract"]["capability"] == "bookability"
    assert canonical_frame.schema_version == "semantic_frame.v2"
    assert canonical_frame.user_goal == "booking"
    assert canonical_frame.requested_effect == "commit_booking"
    assert canonical_frame.subject["kind"] == "service"
    assert canonical_frame.subject["value"] == "Маникюр"
    assert canonical_frame.continuation["next_question"] == "name"
    assert canonical_frame.continuation["slot_values"]["service"] == "Маникюр"
    assert canonical_frame.capability_selection["capability"] == "bookability"
    assert canonical_frame.capability_selection["tool_action_hint"] == "calendar.book_slot"
    assert canonical_contract["capability"] == "bookability"


def test_dialog_state_service_writes_append_only_semantic_state_log() -> None:
    service = DialogStateService()
    first_decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "tool_action_hint": "collect",
            "goal": "booking",
            "reason": "collect_datetime",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "ask_about_requested_slot",
            "slots": {"service": "Маникюр"},
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "expected_reply_type": "time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="llm_policy_core",
        source="policy_core",
    )

    updated, dialog_state, _ = service.write_runtime_payload(
        {},
        decision=first_decision,
        execution_meta={
            "slot_values": {"service": "Маникюр"},
            "next_slot": "datetime",
        },
        now=datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc),
        conversation_id="conv-1",
        trace_id="trace-1",
    )
    second_updated, second_state, _ = service.write_runtime_payload(
        updated,
        decision=first_decision,
        execution_meta={
            "slot_values": {"service": "Маникюр"},
            "next_slot": "datetime",
        },
        now=datetime(2026, 3, 26, 12, 5, tzinfo=timezone.utc),
        conversation_id="conv-1",
        trace_id="trace-1",
    )

    assert dialog_state.semantic_state.materialized_frame.user_goal == "booking"
    assert dialog_state.semantic_state.materialized_frame.continuation["next_question"] == "datetime"
    assert len(dialog_state.semantic_state.event_log) == 1
    assert len(second_state.semantic_state.event_log) == 2
    runtime_payload = second_updated["consultant_runtime"]["dialog_state"]
    assert runtime_payload["semantic_state"]["materialized_frame"]["capability_selection"]["capability"] == "bookability"
    assert runtime_payload["semantic_state"]["event_log"][0]["action"] == "collect"
    first_journal = TurnJournalV1.model_validate(updated["consultant_runtime"]["turn_journal"])
    second_journal = TurnJournalV1.model_validate(second_updated["consultant_runtime"]["turn_journal"])
    assert len(first_journal.events) == 2
    assert len(second_journal.events) == 4
    assert second_journal.events[-1].event_type == "ExecutionCompleted"
    assert second_journal.last_turn_id == first_decision.binding_plan.decision_id
    projection = ConversationProjectionV1.model_validate(
        second_updated["consultant_runtime"]["conversation_projection"]
    )
    assert projection.current_goal == "booking"
    assert projection.pending_question_contract["expected_reply_type"] == "time"


def test_runtime_turn_journal_and_conversation_projection_schemas_validate_runtime_payload() -> None:
    service = DialogStateService()
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "tool_action_hint": "calendar.list_slots",
            "goal": "booking",
            "reason": "collect_datetime",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "ask_about_requested_slot",
            "slots": {"service": "Маникюр"},
            "expected_reply_type": "time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    updated, _dialog_state, _ = service.write_runtime_payload(
        {},
        decision=decision,
        execution_meta={
            "slot_values": {"service": "Маникюр"},
            "next_slot": "datetime",
        },
        now=datetime(2026, 3, 27, 14, 0, tzinfo=timezone.utc),
        conversation_id="conv-1",
        trace_id="trace-1",
    )

    runtime_payload = updated["consultant_runtime"]
    _load_schema("contracts/runtime/turn_journal.v1.jsonschema").validate(
        runtime_payload["turn_journal"]
    )
    _load_schema("contracts/runtime/conversation_projection.v1.jsonschema").validate(
        runtime_payload["conversation_projection"]
    )


def test_runtime_trace_contract_schema_and_turn_result_schema_validate() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "goal": "booking",
            "reason": "collect_datetime",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "ask_about_requested_slot",
            "slots": {"service": "Маникюр"},
            "expected_reply_type": "time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="llm_policy_core",
        source="policy_core",
    )
    decision.semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "collect",
            "goal": "booking",
            "reason": "collect_datetime",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "ask_about_requested_slot",
            "slots": {"service": "Маникюр"},
            "expected_reply_type": "time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        }
    ).model_copy(update={"conversation_id": "conv-rt"})

    updated, dialog_state, _ = DialogStateService().write_runtime_payload(
        {},
        decision=decision,
        execution_meta={
            "slot_values": {"service": "Маникюр"},
            "next_slot": "datetime",
            "question_contract": True,
        },
        now=datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc),
        conversation_id="conv-rt",
        trace_id="trace-rt",
    )
    runtime_payload = updated["consultant_runtime"]
    runtime_trace_contract = RuntimeTraceContractV1.model_validate(
        {
            "schema_version": "runtime_trace_contract.v1",
            "trace_id": "trace-rt",
            "owner_transition": {
                "decision_id": decision.semantic_decision.decision_id,
                "requested_outcome": "collect",
                "intent": "booking",
                "capability_id": "bookability",
                    "interaction_owner": "llm_policy_core",
                    "source": "policy_core",
                "tool_action_hint": "collect",
                "needs_human": False,
                "goal": "booking",
            },
            "binding_transition": {
                "binding_id": decision.binding_plan.binding_id,
                "decision_id": decision.binding_plan.decision_id,
                "binding_outcome_type": decision.binding_plan.binding_outcome_type,
                "capability_id": decision.binding_plan.capability_id,
                "selected_tool_or_workflow_ref": decision.binding_plan.selected_tool_or_workflow_ref,
                "idempotency_key": decision.binding_plan.idempotency_key,
                "resolved_args": dict(decision.binding_plan.resolved_args),
                "authz_scope": dict(decision.binding_plan.authz_scope),
                "timeout_policy": dict(decision.binding_plan.timeout_policy),
                "retry_policy": dict(decision.binding_plan.retry_policy),
            },
            "action_transition": {
                "contract_action": "booking_prompt",
                "runtime_entrypoint": "consultant_runtime",
                "semantic_runtime_path": "consultant_core_v2",
                "reply_kind": "collect",
                "delivered": True,
                "execution_tool_action": "collect",
                "execution_tool_decision": "slot_constraint",
            },
            "state_transition": {
                "turn_id": decision.semantic_decision.decision_id,
                "conversation_id": "conv-rt",
                "current_semantic_decision_ref": decision.semantic_decision.decision_id,
                "active_capability": "bookability",
                "active_workflow_ref": decision.binding_plan.selected_tool_or_workflow_ref,
                "current_goal": "booking",
                "pending_question_contract": runtime_payload["conversation_projection"][
                    "pending_question_contract"
                ],
                "semantic_contract": runtime_payload["conversation_projection"]["semantic_contract"],
                "semantic_state_before": {},
                "semantic_state_after": runtime_payload["conversation_projection"]["semantic_frame"],
                "journal_last_turn_id": runtime_payload["turn_journal"]["last_turn_id"],
                "journal_event_types": [
                    event["event_type"] for event in runtime_payload["turn_journal"]["events"]
                ],
                "last_reply_ref": None,
            },
        }
    )

    _load_schema("contracts/runtime/runtime_trace_contract.v1.jsonschema").validate(
        runtime_trace_contract.model_dump(mode="json", exclude_none=True)
    )

    turn_result_payload = _turn_result_payload()
    turn_result_payload["trace"]["runtime_trace_contract"] = runtime_trace_contract.model_dump(
        mode="json",
        exclude_none=True,
    )
    _load_schema("contracts/runtime/turn_result.v1.jsonschema").validate(
        turn_result_payload
    )


def test_consultant_runtime_memory_profile_prefers_canonical_semantic_state() -> None:
    runtime = ConsultantRuntime()
    dialog_state = DialogState.model_validate(
        {
            "schema_version": "dialog_state.v1",
            "semantic_state": {
                "schema_version": "canonical_semantic_state.v1",
                "materialized_frame": {
                    "schema_version": "semantic_frame.v2",
                    "user_goal": "booking",
                    "requested_effect": "collect_missing_input",
                    "subject": {"kind": "service", "value": "Маникюр"},
                    "referents": {
                        "service": {
                            "value": "Маникюр",
                            "entity_id": "svc:manicure",
                            "entity_type": "service",
                            "source_ref": "carryover",
                        }
                    },
                    "constraints": {},
                    "preferences": {},
                    "continuation": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "slot_values": {"service": "Маникюр"},
                    },
                    "capability_selection": {"capability": "bookability"},
                    "needs_human": False,
                    "reason": "collect_datetime",
                },
                "event_log": [],
            },
            "current_referents": {
                "service": None,
                "specialist": None,
                "branch": None,
                "booking": None,
                "customer": None,
            },
            "pending_question_contract": {
                "expected_reply_type": None,
                "reason": None,
                "pending_question_act": None,
                "pending_question_target": None,
                "active_question_relation": None,
                "next_question": None,
                "open_questions": [],
            },
            "interaction_state": {"interaction_owner": "llm_policy_core"},
            "projections": {
                "expected_reply_type": None,
                "expected_reply_reason": None,
                "session_memory_interaction_state": {},
            },
            "meta": {},
        }
    )
    runtime_state = SimpleNamespace(
        booking_state={},
        dialog_state=dialog_state,
    )

    profile = runtime._build_policy_core_memory_profile(runtime_state)

    assert profile["active_goal"] == "booking"
    assert profile["pending_question_contract"]["next_question"] == "datetime"
    assert profile["semantic_contract"]["capability"] == "bookability"
    assert profile["slot_state"]["service"] == "Маникюр"


def test_consultant_runtime_memory_profile_drops_legacy_semantics_without_canonical_state() -> None:
    runtime = ConsultantRuntime()
    dialog_state = DialogState.model_validate(
        {
            "schema_version": "dialog_state.v1",
            "pending_question_contract": {
                "expected_reply_type": "name",
                "reason": "stale_projection",
                "next_question": "name",
                "open_questions": ["name"],
            },
            "projections": {
                "expected_reply_type": "name",
                "expected_reply_reason": "stale_projection",
            },
            "meta": {
                "current_goal": "handoff",
                "semantic_contract": {
                    "contract_version": "semantic_contract.v1",
                    "capability": "pricing",
                    "subject_kind": "service",
                },
            },
        }
    )

    profile = runtime._build_policy_core_memory_profile(
        SimpleNamespace(
            booking_state={"service": "Маникюр"},
            dialog_state=dialog_state,
        )
    )

    assert profile == {
        "active_goal": "booking",
        "slot_state": {"service": "Маникюр"},
    }


def test_consultant_runtime_memory_profile_deep_copies_canonical_semantic_payloads() -> None:
    runtime = ConsultantRuntime()
    dialog_state = DialogState.model_validate(_dialog_state_payload())

    profile = runtime._build_policy_core_memory_profile(
        SimpleNamespace(
            booking_state={"service": "manicure"},
            dialog_state=dialog_state,
        )
    )

    profile["semantic_contract"]["referents"]["branch"]["value"] = "astana-center"
    profile["pending_question_contract"]["open_questions"].append("name")

    assert dialog_state.semantic_state.materialized_frame.referents["branch"]["value"] == "almaty-center"
    assert dialog_state.semantic_state.materialized_frame.continuation["open_questions"] == [
        "datetime"
    ]


def test_turn_executor_builds_execution_contract_from_canonical_semantic_frame() -> None:
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "goal": "booking",
            "reason": "collect_datetime",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "ask_about_requested_slot",
            "slots": {"service": "Маникюр"},
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "memory",
                }
            },
            "expected_reply_type": "time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        }
    )
    decision = TurnPlanner().build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    contract = TurnExecutor()._build_execution_semantic_contract(
        decision,
        booking_state={"service": "Педикюр"},
        service_name="Педикюр",
    )
    pending_question = TurnExecutor()._build_execution_pending_question_contract(decision)

    assert contract is not None
    assert contract["capability"] == "bookability"
    assert contract["subject_kind"] == "service"
    assert contract["resolution_mode"] == "ask_about_requested_slot"
    assert contract["referents"]["service"]["value"] == "Маникюр"
    assert contract["referents"]["service"]["source_ref"] == "memory"
    assert "specialist" not in contract.get("referents", {})
    assert pending_question == {
        "expected_reply_type": "time",
        "reason": "collect_datetime",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }


def test_consultant_runtime_closure_proof_preserves_canonical_semantic_and_question_contracts() -> None:
    expected_service_referent = {
        "value": "Маникюр",
        "entity_id": "svc:manicure",
        "entity_type": "service",
        "source_ref": "message",
    }
    expected_specialist_referent = {
        "value": "Айгерим",
        "entity_id": "spec:aigerim",
        "entity_type": "specialist",
        "source_ref": "message",
    }
    expected_pending_question_contract = {
        "expected_reply_type": "time",
        "reason": "collect:datetime",
        "pending_question_target": "specialist",
        "active_question_relation": "referent_followup",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }
    expected_tool_execution_projection = {
        "projection_source": "semantic_contract",
        "service_query": "Маникюр",
        "specialist_name": "Айгерим",
    }

    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "calendar.check_availability",
            "tool_args": {},
            "entity_refs": [
                {
                    "entity_id": expected_service_referent["entity_id"],
                    "entity_type": expected_service_referent["entity_type"],
                    "value": expected_service_referent["value"],
                    "source_ref": expected_service_referent["source_ref"],
                },
                {
                    "entity_id": expected_specialist_referent["entity_id"],
                    "entity_type": expected_specialist_referent["entity_type"],
                    "value": expected_specialist_referent["value"],
                    "source_ref": expected_specialist_referent["source_ref"],
                },
            ],
            "referents": {
                "service": dict(expected_service_referent),
                "specialist": dict(expected_specialist_referent),
            },
            "subject_kind": "specialist",
            "capability": "bookability",
            "resolution_mode": "policy_collect",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "goal": "booking",
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="referent_followup",
        source="llm_policy_core",
    )
    execution_meta = {
        "next_slot": "datetime",
        "tool_execution_projection": dict(expected_tool_execution_projection),
        "semantic_contract": {
            "contract_version": "semantic_contract.v1",
            "referents": {
                "service": dict(expected_service_referent),
                "specialist": dict(expected_specialist_referent),
            },
            "entity_refs": [
                {
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "label": "Маникюр",
                    "value": "Маникюр",
                    "source_ref": "message",
                },
                {
                    "entity_id": "spec:aigerim",
                    "entity_type": "specialist",
                    "label": "Айгерим",
                    "value": "Айгерим",
                    "source_ref": "message",
                },
            ],
            "grounding_provenance": {
                "pack_id": "demo_salon",
                "pack_version": "2026-03-25",
                "resolver_id": "pack_query_engine",
                "resolver_version": "2026-03-25",
            },
        },
    }

    now = datetime.now(timezone.utc)
    updated, dialog_state, _ = DialogStateService().write_runtime_payload(
        {},
        decision=decision,
        execution_meta=execution_meta,
        now=now,
    )
    runtime_payload = updated["consultant_runtime"]
    assert "semantic_contract" not in runtime_payload
    assert dialog_state.meta["semantic_contract"]["referents"]["service"] == expected_service_referent
    assert dialog_state.meta["semantic_contract"]["referents"]["specialist"] == expected_specialist_referent
    assert dialog_state.meta["semantic_contract"]["grounding_provenance"] == {
        "pack_id": "demo_salon",
        "resolver_id": "pack_query_engine",
        "resolver_version": "2026-03-25",
    }
    assert "pending_question_contract" not in runtime_payload
    assert "expected_reply_type" not in runtime_payload
    assert dialog_state.pending_question_contract.model_dump(mode="json", exclude_none=True) == expected_pending_question_contract
    assert "expected_reply_type" not in updated
    loaded = DialogStateService().load_runtime_payload(updated)
    assert loaded["expected_reply_type"] == "time"

    runtime = ConsultantRuntime()
    conversation = SimpleNamespace(context={}, state="bot_active")
    user_message = SimpleNamespace(message_metadata={})
    execution = SimpleNamespace(
        tool_action="calendar.check_availability",
        tool_decision="specialist_followup",
        meta=execution_meta,
    )
    turn_result = SimpleNamespace(dialog_state=dialog_state, reply=SimpleNamespace(reply_kind="collect"))

    runtime._record_turn_trace(
        conversation=conversation,
        user_message=user_message,
        bot_response=None,
        decision=decision,
        execution=execution,
        turn_result=turn_result,
        delivered=True,
    )

    trace = conversation.context.get("decision_trace") or []
    assert any(
        entry.get("stage") == "consultant_runtime"
        and entry.get("semantic_contract", {}).get("referents", {}).get("service")
        == expected_service_referent
        and entry.get("semantic_contract", {}).get("grounding_provenance", {}).get("pack_id")
        == "demo_salon"
        and entry.get("pending_question_contract") == expected_pending_question_contract
        and entry.get("tool_execution_projection") == expected_tool_execution_projection
        and entry.get("expected_reply_type") == "time"
        for entry in trace
    )
    decision_meta = (user_message.message_metadata or {}).get("decision_meta") or {}
    assert decision_meta["semantic_contract"]["referents"]["service"] == expected_service_referent
    assert decision_meta["semantic_contract"]["referents"]["specialist"] == expected_specialist_referent
    assert decision_meta["semantic_contract"]["grounding_provenance"]["pack_id"] == "demo_salon"
    assert decision_meta["pending_question_contract"] == expected_pending_question_contract
    assert decision_meta["tool_execution_projection"] == expected_tool_execution_projection
    assert decision_meta["expected_reply_type"] == "time"


def test_consultant_runtime_records_runtime_trace_contract_on_active_path() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "tool_action_hint": "calendar.list_slots",
            "goal": "booking",
            "reason": "collect_datetime",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "ask_about_requested_slot",
            "slots": {"service": "Маникюр"},
            "expected_reply_type": "time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="ask_about_requested_slot",
        source="llm_policy_core",
    )
    decision.semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action_hint": "calendar.list_slots",
            "goal": "booking",
            "reason": "collect_datetime",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "ask_about_requested_slot",
            "slots": {"service": "Маникюр"},
            "expected_reply_type": "time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        }
    ).model_copy(update={"conversation_id": "conv-runtime-trace"})

    execution_meta = {
        "slot_values": {"service": "Маникюр"},
        "next_slot": "datetime",
        "question_contract": True,
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "tool_execution_projection": {
            "tool_action": "calendar.list_slots",
            "selected_specialist": None,
        },
    }
    now = datetime(2026, 3, 28, 14, 0, tzinfo=timezone.utc)
    updated, dialog_state, _ = DialogStateService().write_runtime_payload(
        {},
        decision=decision,
        execution_meta=execution_meta,
        now=now,
        conversation_id="conv-runtime-trace",
        trace_id="trace-runtime-trace",
    )

    runtime = ConsultantRuntime()
    conversation = SimpleNamespace(context=updated, state="bot_active")
    user_message = SimpleNamespace(message_metadata={})
    execution = SimpleNamespace(
        tool_action="collect",
        tool_decision="slot_constraint",
        meta=execution_meta,
    )
    turn_result = TurnExecutor().assemble(
        decision=decision,
        dialog_state=dialog_state,
        reply=ResponseRealizer().realize(
            decision,
            text="Подскажите, пожалуйста, удобное время записи.",
        ),
        stages=["ingress", "planner", "boundary", "state", "executor", "realizer"],
    )

    runtime._record_turn_trace(
        conversation=conversation,
        user_message=user_message,
        bot_response=None,
        decision=decision,
        execution=execution,
        turn_result=turn_result,
        delivered=True,
    )

    trace = conversation.context.get("decision_trace") or []
    runtime_entry = next(
        entry for entry in trace if entry.get("stage") == "consultant_runtime"
    )
    runtime_trace_contract = RuntimeTraceContractV1.model_validate(
        runtime_entry["runtime_trace_contract"]
    )
    assert runtime_trace_contract.trace_id == "trace-runtime-trace"
    assert runtime_trace_contract.owner_transition.decision_id == decision.semantic_decision.decision_id
    assert runtime_trace_contract.owner_transition.requested_outcome == "collect"
    assert runtime_trace_contract.binding_transition.binding_id == decision.binding_plan.binding_id
    assert (
        runtime_trace_contract.binding_transition.selected_tool_or_workflow_ref
        == decision.binding_plan.selected_tool_or_workflow_ref
    )
    assert runtime_trace_contract.action_transition.contract_action == "booking_prompt"
    assert runtime_trace_contract.action_transition.execution_tool_decision == "slot_constraint"
    assert runtime_trace_contract.state_transition.current_semantic_decision_ref == decision.semantic_decision.decision_id
    assert runtime_trace_contract.state_transition.current_goal == "booking"
    assert runtime_trace_contract.state_transition.pending_question_contract["expected_reply_type"] == "time"
    assert "BindingPlanIssued" in runtime_trace_contract.state_transition.journal_event_types

    decision_meta = (user_message.message_metadata or {}).get("decision_meta") or {}
    meta_runtime_trace_contract = RuntimeTraceContractV1.model_validate(
        decision_meta["runtime_trace_contract"]
    )
    assert meta_runtime_trace_contract == runtime_trace_contract
    assert turn_result.trace.runtime_trace_contract == runtime_trace_contract


def test_turn_executor_commits_booking_only_on_explicit_calendar_book_slot(
    monkeypatch,
) -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "fact",
            "tool_action": "calendar.book_slot",
            "slots": {
                "service": "Маникюр",
                "datetime": "2026-03-27T19:00:00+05:00",
                "name": "Амина",
            },
            "goal": "booking",
            "reason": "explicit_booking_commit",
        },
        interaction_owner="llm_policy_core",
        interaction_relation="fill_requested_slot",
        source="llm_policy_core",
    )
    decision.meta["client_id"] = "client-123"

    class _FakeSchedulingService:
        def __init__(self, db):
            self.db = db

        def create_appointment(self, **kwargs):
            return SimpleNamespace(id="appt-123")

    monkeypatch.setattr(
        "app.services.appointment_service.SchedulingService",
        _FakeSchedulingService,
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Меня зовут Амина.",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone="77000000000",
        now=datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc),
    )

    assert result.tool_action == "calendar.book_slot"
    assert result.tool_decision == "ok"
    assert result.meta["appointment_id"] == "appt-123"


def test_turn_executor_builds_typed_explicit_handoff_owner_cutover_artifact() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "human_request",
            "action": "handoff",
            "tool_action": "handoff",
            "needs_manager": True,
            "reason": "ingress_explicit_human_request",
        },
        interaction_owner="turn_planner.safe_explicit_handoff_owner.v1",
        interaction_relation="turn_planner_safe_explicit_handoff_owner",
    )
    state = DialogState.model_validate(_dialog_state_payload())
    artifact = TurnExecutor().build_owner_cutover_artifact(
        decision=decision,
        dialog_state=state,
        text="Передаю диалог менеджеру.",
        owner_cutover="turn_planner.safe_explicit_handoff_owner.v1",
        transport_status="delivered",
        transport_reason=None,
        downstream_tool_decision="handover_created",
        reason_code="ingress_explicit_human_request",
        stages=["ingress", "turn_planner", "executor", "realizer", "explicit_handoff_owner"],
        action="escalate",
        source="consultant_core_runtime",
    )

    _load_schema("contracts/runtime/turn_result.v1.jsonschema").validate(
        artifact.turn_result.model_dump(mode="json")
    )
    assert artifact.turn_result.contract_status == "ok"
    assert artifact.turn_result.reply.reply_kind == "handoff"
    assert artifact.turn_outcome.action == "escalate"
    assert artifact.turn_outcome.intent == "human_request"
    assert artifact.turn_outcome.tool_action == "handoff"
    assert artifact.turn_outcome.tool_decision == "planner_owner_cutover"
    assert artifact.turn_outcome.meta["owner_cutover"] == "turn_planner.safe_explicit_handoff_owner.v1"
    assert artifact.turn_outcome.meta["downstream_tool_decision"] == "handover_created"
    assert artifact.runtime_meta["owner_cutover"] == "turn_planner.safe_explicit_handoff_owner.v1"
    assert artifact.runtime_meta["downstream_tool_decision"] == "handover_created"


def test_turn_executor_builds_typed_greeting_owner_cutover_artifact() -> None:
    decision = TurnPlanner().coerce(
        {
            "outcome": "FACT",
            "action": "fact",
            "intent": "greeting",
            "source": "policy_core",
            "tool_action": "smalltalk",
            "binding_plan": {
                "schema_version": "binding_plan.v1",
                "binding_id": "binding-greeting-owner",
                "decision_id": "decision-greeting-owner",
                "binding_outcome_type": "tool_call",
                "capability_id": "other",
                "selected_tool_or_workflow_ref": "smalltalk",
                "authz_scope": {},
                "resolved_args": {},
                "timeout_policy": {},
                "retry_policy": {},
                "idempotency_key": "decision-greeting-owner",
                "deny_reason_code": None,
                "degrade_reason_code": None,
                "handoff_reason_code": None,
            },
            "interaction": {
                "owner": "turn_planner.safe_greeting_owner.v1",
                "relation": "turn_planner_safe_greeting_owner",
            },
            "meta": {
                "planner_source": "turn_planner",
                "synthetic_policy_decision": True,
                "reason": "ingress_lexical_greeting",
                "controller_class": "greeting",
            },
        }
    )
    state = DialogState.model_validate(_dialog_state_payload())
    artifact = TurnExecutor().build_owner_cutover_artifact(
        decision=decision,
        dialog_state=state,
        text="Здравствуйте! Могу помочь с услугами, ценами или записью.",
        owner_cutover="turn_planner.safe_greeting_owner.v1",
        transport_status="delivered",
        transport_reason=None,
        downstream_tool_decision="greeting",
        reason_code="ingress_lexical_greeting",
        stages=["ingress", "turn_planner", "executor", "realizer", "greeting_owner"],
        action="smalltalk",
        source="consultant_core_runtime",
    )

    _load_schema("contracts/runtime/turn_result.v1.jsonschema").validate(
        artifact.turn_result.model_dump(mode="json")
    )
    assert artifact.turn_result.contract_status == "ok"
    assert artifact.turn_result.reply.reply_kind == "fact"
    assert artifact.turn_outcome.action == "smalltalk"
    assert artifact.turn_outcome.intent == "greeting"
    assert artifact.turn_outcome.tool_action == "smalltalk"
    assert artifact.turn_outcome.tool_decision == "planner_owner_cutover"
    assert artifact.turn_outcome.meta["owner_cutover"] == "turn_planner.safe_greeting_owner.v1"
    assert artifact.turn_outcome.meta["downstream_tool_decision"] == "greeting"
    assert artifact.runtime_meta["owner_cutover"] == "turn_planner.safe_greeting_owner.v1"
    assert artifact.runtime_meta["downstream_tool_decision"] == "greeting"


def test_boundary_validator_builds_typed_block_turn_outcome() -> None:
    planner = TurnPlanner()
    boundary = BoundaryValidator()
    decision = planner.build_preflight_reject(
        reason_code="missing_remote_jid",
        control_label="missing_remote_jid",
        interaction_owner="reasoning_core_missing_remote_jid",
        interaction_relation="missing_remote_jid",
    )
    override = boundary.build_block_override(
        reason_code="missing_remote_jid",
        trace_message="reasoning_core blocked inbound without metadata.remoteJid",
        replan_hints=["require metadata.remoteJid"],
        meta={"source": "reasoning_core"},
    )
    turn_result = _build_boundary_turn_result(
        decision=decision,
        override=override,
        contract_status="blocked",
        text="",
    )

    outcome = boundary.build_block_turn_outcome(
        turn_result=turn_result,
        tool_action="preflight.missing_remote_jid",
    )

    assert outcome.action == "reject"
    assert outcome.intent == "system_control"
    assert outcome.tool_action == "preflight.missing_remote_jid"
    assert outcome.tool_decision == "blocked"
    assert outcome.contract_status == "invalid"
    assert outcome.observability.transport_status == "skipped"
    assert outcome.observability.transport_reason == "missing_remote_jid"
    assert outcome.meta["preflight_path"] is True
    assert outcome.meta["boundary_decision"] == "block"
    assert outcome.meta["control_label"] == "missing_remote_jid"


def test_boundary_validator_builds_typed_ignored_block_turn_outcome() -> None:
    planner = TurnPlanner()
    boundary = BoundaryValidator()
    decision = planner.build_preflight_reject(
        reason_code="duplicate_message_id",
        control_label="duplicate_message_id",
        interaction_owner="reasoning_core_duplicate_message",
        interaction_relation="duplicate_message_id",
    )
    override = boundary.build_block_override(
        reason_code="duplicate_message_id",
        trace_message="reasoning_core ignored preexisting duplicate message_id",
        replan_hints=["skip duplicate inbound message_id"],
        meta={"source": "reasoning_core"},
    )
    turn_result = _build_boundary_turn_result(
        decision=decision,
        override=override,
        contract_status="blocked",
        text="",
    )

    outcome = boundary.build_block_turn_outcome(
        turn_result=turn_result,
        tool_action="preflight.duplicate_message_id",
        ignored=True,
    )

    assert outcome.action == "ignore"
    assert outcome.intent == "system_control"
    assert outcome.tool_action == "preflight.duplicate_message_id"
    assert outcome.tool_decision == "blocked"
    assert outcome.contract_status == "invalid"
    assert outcome.meta["ignored_path"] is True
    assert "preflight_path" not in outcome.meta
    assert outcome.meta["control_label"] == "duplicate_message_id"


def test_boundary_validator_builds_typed_degrade_turn_outcome() -> None:
    planner = TurnPlanner()
    boundary = BoundaryValidator()
    decision = planner.build_controlled_degrade(
        reason_code="runtime_exception",
        control_label="runtime_error",
        interaction_owner="reasoning_core_exception_degrade",
        interaction_relation="runtime_exception",
    )
    override = boundary.build_degrade_override(
        reason_code="runtime_exception",
        public_message="Fallback response skipped",
        trace_message="reasoning_core exception degraded through new core",
        meta={"source": "reasoning_core"},
    )
    turn_result = _build_boundary_turn_result(
        decision=decision,
        override=override,
        contract_status="degraded",
        text="Fallback response skipped",
    )

    outcome = boundary.build_degrade_turn_outcome(
        turn_result=turn_result,
        transport_status="failed",
        transport_reason="fallback_send_failed",
    )

    assert outcome.action == "handoff"
    assert outcome.intent == "system_control"
    assert outcome.tool_action == "handoff"
    assert outcome.tool_decision == "runtime_exception"
    assert outcome.contract_status == "degraded"
    assert outcome.observability.transport_status == "failed"
    assert outcome.observability.transport_reason == "fallback_send_failed"
    assert outcome.meta["degrade_path"] is True
    assert outcome.meta["boundary_decision"] == "degrade"
    assert outcome.meta["control_label"] == "runtime_error"


def test_boundary_validator_resolve_reason_code_falls_back_to_observability_and_raises_when_missing() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "duration",
            "action": "fact",
            "tool_action": "catalog.service_query",
        },
        interaction_owner="llm_policy_core",
        interaction_relation="generic_info_interrupt",
        source="llm_policy_core",
    )
    turn_result = TurnExecutor().assemble(
        decision=decision,
        dialog_state=DialogState.model_validate(_dialog_state_payload()),
        reply=ResponseRealizer().realize(decision, text="ignored"),
        contract_status="ok",
        reason_code="fallback_reason",
        stages=["planner", "boundary", "executor", "realizer"],
    )

    assert BoundaryValidator()._resolve_reason_code(turn_result) == "fallback_reason"

    missing_reason_result = TurnExecutor().assemble(
        decision=decision,
        dialog_state=DialogState.model_validate(_dialog_state_payload()),
        reply=ResponseRealizer().realize(decision, text="ignored"),
        contract_status="ok",
        reason_code=None,
        stages=["planner", "boundary", "executor", "realizer"],
    )

    with pytest.raises(ValueError, match="boundary_reason_code_missing"):
        BoundaryValidator()._resolve_reason_code(missing_reason_result)


def test_turn_executor_builds_typed_owner_cutover_turn_outcome() -> None:
    planner = TurnPlanner()
    decision = planner.coerce(_policy_payload())
    state = DialogState.model_validate(_dialog_state_payload())
    reply = ResponseRealizer().realize(decision, text="Выберите услугу, пожалуйста.")
    turn_result = TurnExecutor().assemble(
        decision=decision,
        dialog_state=state,
        reply=reply,
        contract_status="ok",
        reason_code="service_clarify",
        stages=["ingress", "turn_planner", "executor", "realizer"],
    )

    outcome = TurnExecutor().build_owner_cutover_turn_outcome(
        turn_result=turn_result,
        transport_status="delivered",
        transport_reason=None,
        owner_cutover="turn_planner.safe_pricing_collect.v1",
        downstream_tool_decision="service_clarify",
        followup_type="service_choice",
        followup_reason="service_clarify",
    )

    assert outcome.action == "reply"
    assert outcome.intent == "booking"
    assert outcome.tool_action == "calendar.list_slots"
    assert outcome.tool_decision == "planner_owner_cutover"
    assert outcome.contract_status == "ok"
    assert outcome.expected_reply_type == "service_choice"
    assert outcome.expected_reply_reason == "service_clarify"
    assert outcome.observability.reply_observed is True
    assert outcome.observability.transport_status == "delivered"
    assert outcome.meta["owner_cutover"] == "turn_planner.safe_pricing_collect.v1"
    assert outcome.meta["downstream_tool_decision"] == "service_clarify"
    assert outcome.meta["owner_replacement_cutover"] is True


def test_response_realizer_honors_degrade_reply_kind_override() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "duration",
            "action": "fact",
            "tool_action": "catalog.service_query",
        },
        interaction_owner="llm_policy_core",
        interaction_relation="generic_info_interrupt",
        source="llm_policy_core",
    )
    override = BoundaryValidator().build_degrade_override(
        reason_code="executor:handoff_requested",
        public_message="Передаю диалог менеджеру.",
        trace_message="execution_requested_handoff",
        meta={"reply_kind": "handoff", "activate_handoff": True},
    )

    reply = ResponseRealizer().realize(decision, override=override, text="ignored")

    assert reply.reply_kind == "handoff"
    assert reply.text == "Передаю диалог менеджеру."


def test_response_realizer_uses_system_block_and_keeps_non_boundary_degrade_reply_kinds_out_of_fact_collect() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
        },
        interaction_owner="llm_policy_core",
        interaction_relation="fill_requested_slot",
        source="llm_policy_core",
    )
    block_override = BoundaryValidator().build_block_override(
        reason_code="missing_remote_jid",
        trace_message="reasoning_core blocked inbound without metadata.remoteJid",
        replan_hints=["require metadata.remoteJid"],
        public_message="Системная блокировка.",
    )
    block_reply = ResponseRealizer().realize(decision, override=block_override, text="ignored")

    assert block_reply.reply_kind == "system"
    assert block_reply.text == "Системная блокировка."

    degrade_override = BoundaryOverride.model_validate(
        {
            "decision": "degrade",
            "reason_code": "runtime_exception",
            "preserve_fields": ["outcome"],
            "public_message": "Передаю диалог менеджеру.",
            "meta": {"reply_kind": "fact"},
        }
    )
    degrade_reply = ResponseRealizer().realize(decision, override=degrade_override, text="ignored")

    assert degrade_reply.reply_kind == "handoff"
    assert degrade_reply.text == "Передаю диалог менеджеру."


def test_consultant_runtime_preserves_owner_decision_when_executor_requests_handoff() -> None:
    runtime = ConsultantRuntime()
    decision = build_test_policy_override_decision(
        {
            "intent": "duration",
            "action": "fact",
            "tool_action": "catalog.service_query",
        },
        interaction_owner="llm_policy_core",
        interaction_relation="generic_info_interrupt",
        source="llm_policy_core",
    )
    execution = TurnExecutor().execute(
        TurnPlanner().build_controlled_degrade(
            reason_code="branch_missing",
            control_label="branch_missing",
            interaction_owner="turn_executor",
        ),
        db=None,
        message_text=None,
        client_slug=None,
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    preserved_decision, override = runtime._apply_execution_boundary_override(
        decision=decision,
        execution=execution,
        boundary_override=None,
    )

    assert preserved_decision == decision
    assert override is not None
    assert override.reason_code == "executor:handoff_requested"
    assert override.meta["reply_kind"] == "handoff"
    assert runtime._should_activate_handoff(
        decision=preserved_decision,
        boundary_override=override,
    ) is True


def test_dialog_state_service_project_context_session_memory_interaction_state_prefers_runtime_projection() -> None:
    service = DialogStateService()
    context = {
        "consultant_runtime": {
            "conversation_projection": {
                "schema_version": "conversation_projection.v1",
                "projection_version": "v1",
                "current_goal": "booking",
                "semantic_frame": {
                    "referents": {
                        "service": {"value": "маникюр"},
                    }
                },
                "pending_question_contract": {
                    "expected_reply_type": "time",
                    "reason": "runtime_projection",
                    "pending_question_target": "time",
                    "active_question_relation": "ask_about_requested_slot",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                },
            }
        },
        "context_manager": {
            "canonical_dialog_state": {
                "interaction_state": {
                    "resume_slot": "name",
                    "interaction_target": "name",
                    "interaction_relation": "stale_canonical",
                    "interaction_owner": "context_manager",
                }
            }
        },
    }

    projected = service.project_context_session_memory_interaction_state(context)

    assert projected == {
        "resume_slot": "datetime",
        "interaction_target": "time",
        "interaction_relation": "ask_about_requested_slot",
        "interaction_owner": "consultant_runtime",
        "grounded_referents": {"service": "маникюр"},
    }


def test_timeout_owner_boundary_resolution_syncs_session_memory_from_projection_state() -> None:
    from app.services.timeout_owner_boundary_service import apply_timeout_owner_boundary_resolution

    captured: dict[str, object] = {}
    context = {
        "consultant_runtime": {
            "conversation_projection": {
                "schema_version": "conversation_projection.v1",
                "projection_version": "v1",
                "current_goal": "booking",
                "pending_question_contract": {
                    "expected_reply_type": "time",
                    "reason": "runtime_projection",
                    "pending_question_target": "time",
                    "active_question_relation": "ask_about_requested_slot",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                },
            }
        },
        "context_manager": {
            "canonical_dialog_state": {
                "interaction_state": {
                    "resume_slot": "name",
                    "interaction_target": "name",
                    "interaction_relation": "stale_canonical",
                    "interaction_owner": "context_manager",
                }
            }
        },
    }

    def _set_booking_context(current_context, booking_state):
        updated = dict(current_context)
        updated["booking"] = dict(booking_state)
        return updated

    def _set_expected_reply_context(*, context, expected_reply_type, reason, **_kwargs):
        updated = dict(context)
        updated["expected_reply_type"] = expected_reply_type
        updated["expected_reply_reason"] = reason
        return updated

    def _set_context_manager(current_context, manager):
        updated = dict(current_context)
        updated["context_manager"] = manager
        return updated

    result = apply_timeout_owner_boundary_resolution(
        conversation=SimpleNamespace(state="bot_active"),
        saved_message=None,
        context=context,
        resolution=SimpleNamespace(
            booking_state={"active": True, "last_question": "datetime"},
            expected_reply_type="time",
            expected_reply_reason="policy_core_timeout_owner_boundary",
            execution_owner="owner_boundary",
            reason_code="timeout_owner_boundary_matched_expected_reply",
            source="matched_expected_reply",
            missing_slot="datetime",
            filled_slots=("datetime",),
            trace_decision="timeout_owner_boundary_match",
            recovery="timeout_owner_boundary_collect",
            prompt="Скажите удобное время.",
        ),
        now=datetime.now(timezone.utc),
        message_count=5,
        branch_id=None,
        consult_context=None,
        policy_core_mode="active",
        policy_core_degrade_reason=None,
        pending_question_contract=None,
        boundary_state_source="runtime_projection",
        hooks=SimpleNamespace(
            set_booking_context=_set_booking_context,
            set_expected_reply_context=_set_expected_reply_context,
            get_booking_context=lambda current_context: current_context.get("booking") or {},
            get_expected_reply_type=lambda current_context: current_context.get("expected_reply_type"),
            get_expected_reply_reason=lambda current_context: current_context.get("expected_reply_reason"),
            get_context_manager=lambda current_context: dict(current_context.get("context_manager") or {}),
            sync_canonical_dialog_state=lambda manager, **_kwargs: dict(manager),
            set_context_manager=_set_context_manager,
            get_canonical_dialog_state=lambda manager: manager.get("canonical_dialog_state") or {},
            sync_session_memory_interaction_state=lambda current_context, interaction_state, now: (
                captured.setdefault("context", current_context),
                captured.setdefault("interaction_state", interaction_state),
            ) and (current_context, {}),
            set_conversation_context=lambda conversation, current_context: captured.setdefault("conversation_context", current_context),
            apply_policy_guard_override=lambda **_kwargs: None,
            sync_policy_plan_audit=lambda **_kwargs: None,
            record_decision_trace=lambda *_args, **_kwargs: None,
            record_message_decision_meta=lambda *_args, **_kwargs: None,
            update_message_decision_metadata=lambda *_args, **_kwargs: None,
            send_and_save=lambda prompt: (prompt, True),
        ),
    )

    assert result.bot_response == "Скажите удобное время."
    assert captured["interaction_state"] == {
        "resume_slot": "datetime",
        "interaction_target": "time",
        "interaction_relation": "ask_about_requested_slot",
        "interaction_owner": "consultant_runtime",
        "grounded_referents": {},
    }


def test_policy_timeout_followup_boundary_syncs_session_memory_from_projection_state() -> None:
    from app.services.policy_timeout_booking_time_followup_boundary_service import (
        PolicyTimeoutBookingTimeFollowupBoundaryRuntimeInput,
        handle_policy_timeout_booking_time_followup_boundary,
    )

    captured: dict[str, object] = {}
    conversation = SimpleNamespace(id=uuid4(), state="bot_active")
    context = {
        "consultant_runtime": {
            "conversation_projection": {
                "schema_version": "conversation_projection.v1",
                "projection_version": "v1",
                "current_goal": "booking",
                "pending_question_contract": {
                    "expected_reply_type": "time",
                    "reason": "runtime_projection",
                    "pending_question_target": "time",
                    "active_question_relation": "ask_about_requested_slot",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                },
            }
        },
        "context_manager": {
            "canonical_dialog_state": {
                "interaction_state": {
                    "resume_slot": "name",
                    "interaction_target": "name",
                    "interaction_relation": "stale_canonical",
                    "interaction_owner": "context_manager",
                }
            }
        },
    }

    def _set_booking_context(current_context, booking_state):
        updated = dict(current_context)
        updated["booking"] = dict(booking_state)
        return updated

    def _set_expected_reply_context(*, context, expected_reply_type, reason, **_kwargs):
        updated = dict(context)
        updated["expected_reply_type"] = expected_reply_type
        updated["expected_reply_reason"] = reason
        return updated

    def _set_context_manager(current_context, manager):
        updated = dict(current_context)
        updated["context_manager"] = manager
        return updated

    response = handle_policy_timeout_booking_time_followup_boundary(
        runtime_input=PolicyTimeoutBookingTimeFollowupBoundaryRuntimeInput(
            conversation=conversation,
            saved_message=None,
            now=datetime.now(timezone.utc),
            message_count=5,
            branch_id=None,
            policy_core_mode="active",
            policy_core_degrade_reason="timeout",
            reason_code="timeout_followup",
            guard_reason="runtime_projection",
            booking_state={"active": True, "last_question": "datetime"},
            collect_slot="datetime",
            current_booking_datetime="2026-02-12 17:45",
            alternate_booking_datetime="2026-02-12 18:00",
            expected_reply_type="time",
            expected_reply_reason="runtime_projection",
        ),
        hooks=SimpleNamespace(
            get_conversation_context=lambda _conversation: context,
            set_booking_context=_set_booking_context,
            set_expected_reply_context=_set_expected_reply_context,
            get_context_manager=lambda current_context: dict(current_context.get("context_manager") or {}),
            sync_canonical_dialog_state=lambda manager, **_kwargs: dict(manager),
            set_context_manager=_set_context_manager,
            get_canonical_dialog_state=lambda manager: manager.get("canonical_dialog_state") or {},
            sync_session_memory_interaction_state=lambda current_context, interaction_state, now: (
                captured.setdefault("interaction_state", interaction_state),
                current_context,
                {"interaction_state": interaction_state},
            )[-2:],
            set_conversation_context=lambda _conversation, current_context: captured.setdefault("conversation_context", current_context),
            record_session_memory_update=lambda *_args, **_kwargs: None,
            apply_policy_guard_override=lambda **_kwargs: None,
            sync_policy_plan_audit=lambda **_kwargs: None,
            record_decision_trace=lambda *_args, **_kwargs: None,
            record_message_decision_meta=lambda *_args, **_kwargs: None,
            update_message_decision_metadata=lambda *_args, **_kwargs: None,
            build_response=lambda **_kwargs: "Уточните время",
            combine_sidecar=lambda sidecar, response_text: f"{sidecar} {response_text}",
            maybe_apply_consult_return=lambda **kwargs: kwargs["bot_response"],
            reset_low_confidence_retry=lambda *_args, **_kwargs: None,
            send_and_save=lambda response_text: (response_text, True),
            commit=lambda: None,
        ),
    )

    assert response.bot_response == "Уточните время"
    assert captured["interaction_state"] == {
        "resume_slot": "datetime",
        "interaction_target": "time",
        "interaction_relation": "ask_about_requested_slot",
        "interaction_owner": "consultant_runtime",
        "grounded_referents": {},
    }
