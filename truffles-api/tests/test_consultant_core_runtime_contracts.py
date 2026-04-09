from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
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
from app.routers.webhook import guards as webhook_guards
from app.services.knowledge_runtime import RuntimeTruth, use_runtime_truth_override
from app.services.policy_validation_boundary_service import (
    PolicyValidationBoundaryRuntimeHooks,
    PolicyValidationBoundaryRuntimeInput,
    handle_policy_validation_boundary,
)
from app.services.state_machine import ConversationState
from app.services.tool_registry_service import ToolExecutionResult
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
        "action": "collect",
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


def test_dialog_state_service_canonicalizes_booking_prompt_reason_to_collect_slot() -> None:
    projections = DialogStateService().project_expected_reply_projections(
        expected_reply_type="time",
        expected_reply_reason="booking_prompt",
    )
    assert projections.expected_reply_type == "time"
    assert projections.expected_reply_reason == "collect:datetime"

    media_projections = DialogStateService().project_expected_reply_projections(
        expected_reply_type="media",
        expected_reply_reason="booking_prompt_media_ack",
    )
    assert media_projections.expected_reply_reason == "collect:media"


def test_dialog_state_service_expected_reply_sync_canonicalizes_booking_prompt_reason() -> None:
    now = datetime(2026, 4, 3, 18, 0, tzinfo=timezone.utc)
    result = DialogStateService().build_expected_reply_context_sync_result(
        {
            "booking": {
                "active": True,
                "service": "Маникюр",
                "last_question": "datetime",
            },
            "context_manager": {
                "message_count": 4,
                "current_goal": "booking",
            },
        },
        expected_reply_type="time",
        reason="booking_prompt",
        now=now,
    )

    assert result.expected_reply_type == "time"
    assert result.expected_reply_reason == "collect:datetime"
    assert result.pending_question_contract == {
        "expected_reply_type": "time",
        "reason": "collect:datetime",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }
    assert result.context["expected_reply_reason"] == "collect:datetime"
    assert (
        result.context.get("context_manager", {})
        .get("canonical_dialog_state", {})
        .get("pending_question_contract", {})
        .get("reason")
        == "collect:datetime"
    )


def test_decision_booking_followup_reason_helper_accepts_canonical_collect_reason() -> None:
    from app.routers.webhook import decision as decision_router

    assert decision_router._is_booking_followup_expected_reply_reason(
        "collect:datetime",
        expected_reply_type="time",
    ) is True
    assert decision_router._is_booking_followup_expected_reply_reason(
        "collect:service",
        expected_reply_type="service_choice",
    ) is True
    assert decision_router._is_booking_followup_expected_reply_reason(
        "booking_prompt",
        expected_reply_type="time",
    ) is True
    assert decision_router._is_booking_followup_expected_reply_reason(
        "info_interrupt",
        expected_reply_type="time",
    ) is False
    assert decision_router._timeout_booking_completion_override("booking_prompt") == (
        "collect",
        "collect",
    )


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


def _runtime_truth_payload(payload: dict, *, slug: str = "demo_salon") -> RuntimeTruth:
    return RuntimeTruth(
        truth=payload,
        client_slug=slug,
        branch_id=uuid4(),
        source="test_consultant_core_runtime_contracts",
        allow_fallback=False,
    )


def _owner_backed_promotions_interrupt_decision() -> PolicyDecision:
    planner = TurnPlanner()
    semantic_payload = build_test_semantic_decision_payload(
        {
            "intent": "pricing",
            "action": "fact",
            "tool_action_hint": "info",
            "pack_refs": ["promotions"],
            "reason": "user_asked_promotions_during_booking_continuity",
            "subject_kind": "service",
            "capability": "promotions",
            "resolution_mode": "policy_fact",
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "from_user",
                }
            },
        }
    )
    binding_payload = _binding_plan_payload() | {
        "decision_id": semantic_payload["decision_id"],
        "selected_tool_or_workflow_ref": "catalog.service_query",
        "capability_id": "promotions",
        "resolved_args": {"service_query": "маникюр"},
        "idempotency_key": semantic_payload["decision_id"],
    }
    return planner._build_policy_core_decision(
        semantic_payload,
        binding_plan_payload=binding_payload,
    )


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
        "pending_question_contract": {
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "expected_reply_type": "time",
            "reason": "booking_time_availability_followup",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
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
    assert "semantic_contract" not in captured["memory_profile"]
    assert TurnPlanner().canonical_pending_question_contract(decision).next_question == "datetime"
    assert override is None


def test_consultant_runtime_plan_turn_preserves_original_decision_when_semantic_owner_guard_fails() -> None:
    runtime = ConsultantRuntime()

    original_decision = build_test_policy_override_decision(
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
    runtime.planner.plan = lambda **_kwargs: SimpleNamespace(
        decision=original_decision,
        boundary_signal=None,
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

    assert decision is original_decision
    assert decision.intent == "booking"
    assert decision.interaction.owner == "llm_policy_core_booking"
    assert decision.source == "llm_policy_core"
    assert "degrade_path" not in decision.meta
    assert "reason_code" not in decision.meta
    assert override is not None
    assert override.reason_code == "planner:missing_semantic_owner"
    assert override.meta["control_label"] == "planner_missing_semantic_owner"
    assert override.meta["handoff_activation_requested"] is True
    assert override.meta["missing_semantic_owner_guard"] == {
        "reason_code": "missing_semantic_owner",
        "source": "llm_policy_core",
        "outcome": "COLLECT",
        "action": "collect",
        "tool_action": "collect",
    }
    assert override.meta["missing_semantic_owner_guard"]["source"] == "llm_policy_core"
    assert override.meta["earliest_failed_stage"] == "planner"
    assert override.meta["root_reason_code"] == "planner:missing_semantic_owner"


def test_consultant_runtime_plan_turn_preserves_owner_backed_decision_without_binding_plan() -> None:
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

    runtime.planner.plan = lambda **_kwargs: SimpleNamespace(
        decision=decision,
        boundary_signal=None,
    )
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

    assert planned is decision
    assert planned.intent == "booking"
    assert planned.source == "llm_policy_core"
    assert "degrade_path" not in planned.meta
    assert "reason_code" not in planned.meta
    assert override is not None
    assert override.reason_code == "planner:missing_binding_plan"
    assert override.meta["control_label"] == "planner_missing_binding_plan"
    assert override.meta["missing_binding_plan_guard"] == {
        "reason_code": "missing_binding_plan",
        "semantic_decision_id": semantic_decision.decision_id,
        "tool_action": "collect",
        "source": "llm_policy_core",
    }
    assert override.meta["earliest_failed_stage"] == "planner"


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

    runtime.planner.plan = lambda **_kwargs: SimpleNamespace(
        decision=decision,
        boundary_signal=None,
    )
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

    assert planned is decision
    assert planned.intent == "booking"
    assert planned.source == "llm_policy_core"
    assert "degrade_path" not in planned.meta
    assert override is not None
    assert override.reason_code == "planner:invalid_outcome"
    assert override.meta["control_label"] == "planner_invalid_outcome"
    assert override.meta["planner_boundary_signal"] is True


def test_consultant_runtime_plan_turn_preserves_explicit_boundary_handoff_on_planner_signal() -> None:
    runtime = ConsultantRuntime()
    signal = TurnPlanner().build_controlled_degrade_signal(
        reason_code="planner:existing_degrade",
        control_label="planner_existing_degrade",
        interaction_owner="turn_planner",
    )

    runtime.planner.plan = lambda **_kwargs: SimpleNamespace(
        decision=None,
        boundary_signal=signal,
    )
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

    assert planned is None
    assert override is not None
    assert override.reason_code == "planner:existing_degrade"
    assert override.meta["degrade_stage"] == "planner"
    assert override.meta["planner_boundary_signal"] is True
    assert override.meta["handoff_activation_requested"] is True


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
def test_consultant_runtime_plan_turn_preserves_owner_decision_on_post_owner_semantic_mutation(
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

    runtime.planner.plan = lambda **_kwargs: SimpleNamespace(
        decision=decision,
        boundary_signal=None,
    )
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

    assert planned is decision
    assert planned.source == "llm_policy_core"
    assert "degrade_path" not in planned.meta
    assert override is not None
    assert override.reason_code == "planner:semantic_decision_post_owner_mutation"
    assert override.meta["control_label"] == "planner_semantic_decision_guard"
    mutation_guard = override.meta["semantic_mutation_guard"]
    assert mutation_guard["reason_code"] == "semantic_decision_post_owner_mutation"
    assert mutation_guard["semantic_decision_id"] == semantic_decision.decision_id
    assert expected_diff_key in mutation_guard["diffs"]
    assert override.meta["semantic_mutation_guard"]["reason_code"] == "semantic_decision_post_owner_mutation"
    assert expected_diff_key in override.meta["semantic_mutation_guard"]["diffs"]


def _build_boundary_turn_result(
    *,
    decision: PolicyDecision | None,
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
    decision: PolicyDecision | None,
    override: BoundaryOverride,
    contract_status: str,
    text: str,
    tool_action: str,
    ignored: bool = False,
    intent: str | None = None,
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
            intent=intent,
        )
    if contract_status == "degraded":
        return executor.build_degrade_boundary_artifact(
            decision=decision,
            dialog_state=state,
            boundary_override=override,
            text=text,
            transport_status="failed",
            transport_reason="fallback_send_failed",
            intent=intent,
        )
    raise ValueError(f"unsupported_contract_status:{contract_status}")


def _build_binding_only_boundary_decision(
    *,
    binding_plan: BindingPlanV1,
    outcome: str,
    action: str,
    intent: str,
    tool_action: str,
    reason_code: str,
) -> PolicyDecision:
    return PolicyDecision(
        outcome=outcome,
        action=action,
        intent=intent,
        source="boundary_test",
        tool_action=tool_action,
        interaction={"owner": "boundary_test_owner"},
        binding_plan=binding_plan,
        meta={"reason_code": reason_code},
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


def test_fact_plan_prefers_explicit_parking_ref_over_coarse_location_family_alias() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "location",
            "action": "fact",
            "tool_action": "catalog.location",
            "pack_refs": ["parking"],
            "reason": "parking_info_interrupt_booking_time_collect",
            "goal": "booking",
            "capability": "bookability",
            "subject_kind": "service",
            "resolution_mode": "direct",
        },
        interaction_owner="llm_policy_core",
        interaction_relation="generic_info_interrupt",
        source="llm_policy_core",
    )

    fact_request = FactRequestV1.build_from_policy_decision(decision)
    fact_plan = FactPlanV1.build_from_request(fact_request, decision=decision)

    assert fact_request.requested_fact_refs == ["parking"]
    assert fact_request.requested_scopes == ["info.parking"]
    assert fact_plan.allowed_emitted_sets == [["parking"]]
    assert fact_plan.allowed_emitted_fact_refs == ["parking"]


def test_fact_plan_prefers_owner_exact_service_query_ref_over_coarse_pricing_alias() -> None:
    decision = _owner_backed_promotions_interrupt_decision()

    fact_request = FactRequestV1.build_from_policy_decision(decision)
    fact_plan = FactPlanV1.build_from_request(fact_request, decision=decision)

    assert fact_request.requested_fact_refs == ["promotions"]
    assert fact_request.requested_scopes == ["info.promotions"]
    assert fact_request.supporting_pack_refs == ["promotions"]
    assert fact_request.supporting_capability_refs == ["promotions"]
    assert fact_request.composition_mode == "companion_allowed"
    assert fact_plan.bundle_policy == "service_query_fact_sections"
    assert fact_plan.allowed_emitted_sets == [["promotions"]]
    assert fact_plan.allowed_emitted_fact_refs == ["promotions"]


def test_fact_plan_prefers_owner_exact_pack_ref_over_booking_capability_alias() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "pricing",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "pack_refs": ["promotions"],
            "reason": "user_asked_promotions_during_booking_continuity",
            "goal": "booking",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "policy_fact",
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
        },
        interaction_owner="llm_policy_core",
        interaction_relation="generic_info_interrupt",
        source="llm_policy_core",
    )

    fact_request = FactRequestV1.build_from_policy_decision(decision)
    fact_plan = FactPlanV1.build_from_request(fact_request, decision=decision)

    assert fact_request.requested_fact_refs == ["promotions"]
    assert fact_request.requested_scopes == ["info.promotions"]
    assert fact_request.supporting_pack_refs == ["promotions"]
    assert fact_plan.allowed_emitted_sets == [["promotions"]]
    assert fact_plan.allowed_emitted_fact_refs == ["promotions"]


def test_fact_plan_prefers_owner_exact_pack_ref_over_master_query_alias() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "master_query",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "pack_refs": ["promotions"],
            "reason": "user_asked_promotions_during_booking_continuity",
            "goal": "booking",
            "subject_kind": "service",
            "capability": "promotions",
            "resolution_mode": "policy_fact",
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                }
            },
        },
        interaction_owner="llm_policy_core",
        interaction_relation="generic_info_interrupt",
        source="llm_policy_core",
    )

    fact_request = FactRequestV1.build_from_policy_decision(decision)
    fact_plan = FactPlanV1.build_from_request(fact_request, decision=decision)

    assert fact_request.requested_fact_refs == ["promotions"]
    assert fact_request.requested_scopes == ["info.promotions"]
    assert fact_request.supporting_pack_refs == ["promotions"]
    assert fact_plan.allowed_emitted_sets == [["promotions"]]
    assert fact_plan.allowed_emitted_fact_refs == ["promotions"]


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


def test_policy_decision_schema_allows_meta_only_control_payload_without_binding_plan() -> None:
    payload = _policy_payload() | {
        "meta": {"reason_code": "missing_remote_jid"},
        "binding_plan": None,
    }

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


def test_policy_decision_model_allows_meta_only_control_payload_without_binding_plan() -> None:
    payload = _policy_payload() | {
        "meta": {"reason_code": "missing_remote_jid"},
        "binding_plan": None,
    }

    decision = PolicyDecision.model_validate(payload)
    assert decision.binding_plan is None


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

    assert override.meta == {}


def test_boundary_validator_strips_business_control_meta_from_override() -> None:
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

    assert override.meta == {}


def test_boundary_validator_validate_normalizes_override_surface() -> None:
    boundary = BoundaryValidator()
    decision = build_test_policy_override_decision(
        {
            "intent": "human_request",
            "action": "handoff",
            "tool_action": "handoff",
            "reason": "runtime_exception",
        },
        interaction_owner="llm_policy_core_handoff",
        interaction_relation="generic_handoff",
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
    assert validated.override.meta == {}


def test_turn_executor_builds_typed_block_boundary_turn_result() -> None:
    boundary = BoundaryValidator()
    override = boundary.build_block_override(
        reason_code="missing_remote_jid",
        trace_message="reasoning_core blocked inbound without metadata.remoteJid",
        replan_hints=["require metadata.remoteJid"],
        meta={"source": "reasoning_core"},
    )
    state = DialogState.model_validate(_dialog_state_payload())
    reply = ResponseRealizer().realize(None, override=override, text="")

    turn_result = TurnExecutor().build_block_boundary_turn_result(
        decision=None,
        dialog_state=state,
        reply=reply,
        boundary_override=override,
    )

    assert turn_result.contract_status == "blocked"
    assert turn_result.policy_decision is None
    assert turn_result.boundary_override is not None
    assert turn_result.boundary_override.reason_code == "missing_remote_jid"
    assert turn_result.observability.reason_code == "missing_remote_jid"
    assert turn_result.trace.stages == ["ingress", "planner", "boundary", "executor", "realizer"]


def test_turn_executor_builds_typed_degrade_boundary_turn_result() -> None:
    boundary = BoundaryValidator()
    override = boundary.build_degrade_override(
        reason_code="runtime_exception",
        public_message="Fallback response skipped",
        trace_message="reasoning_core exception degraded through new core",
        meta={"source": "reasoning_core"},
    )
    state = DialogState.model_validate(_dialog_state_payload())
    reply = ResponseRealizer().realize(None, override=override, text="Fallback response skipped")

    turn_result = TurnExecutor().build_degrade_boundary_turn_result(
        decision=None,
        dialog_state=state,
        reply=reply,
        boundary_override=override,
    )

    assert turn_result.contract_status == "degraded"
    assert turn_result.policy_decision is None
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
    boundary = BoundaryValidator()
    override = boundary.build_block_override(
        reason_code="missing_remote_jid",
        trace_message="reasoning_core blocked inbound without metadata.remoteJid",
        replan_hints=["require metadata.remoteJid"],
        meta={"source": "reasoning_core"},
    )

    artifact = _build_boundary_artifact(
        decision=None,
        override=override,
        contract_status="blocked",
        text="",
        tool_action="preflight.missing_remote_jid",
        intent="missing_remote_jid",
    )

    assert artifact.turn_result.contract_status == "blocked"
    assert artifact.turn_result.policy_decision is None
    assert artifact.turn_result.observability.reason_code == "missing_remote_jid"
    assert artifact.turn_outcome.action == "reject"
    assert artifact.turn_outcome.tool_action == "preflight.missing_remote_jid"
    assert artifact.turn_outcome.meta["preflight_path"] is True


def test_turn_executor_builds_typed_degrade_boundary_artifact() -> None:
    boundary = BoundaryValidator()
    override = boundary.build_degrade_override(
        reason_code="runtime_exception",
        public_message="Fallback response skipped",
        trace_message="reasoning_core exception degraded through new core",
        meta={"source": "reasoning_core"},
    )

    artifact = _build_boundary_artifact(
        decision=None,
        override=override,
        contract_status="degraded",
        text="Fallback response skipped",
        tool_action="handoff",
        intent="runtime_error",
    )

    assert artifact.turn_result.contract_status == "degraded"
    assert artifact.turn_result.policy_decision is None
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
    assert artifact.turn_result.policy_decision is None
    assert artifact.turn_result.boundary_override is not None
    assert artifact.turn_result.boundary_override.reason_code == "missing_remote_jid"
    assert artifact.turn_result.dialog_state.meta["block_path"] is True
    assert artifact.turn_outcome.tool_action == "preflight.missing_remote_jid"
    assert artifact.turn_outcome.intent == "missing_remote_jid"
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
    assert artifact.turn_result.policy_decision is None
    assert artifact.turn_result.boundary_override is not None
    assert artifact.turn_result.boundary_override.reason_code == "runtime_exception"
    assert artifact.turn_result.dialog_state.meta["degrade_path"] is True
    assert artifact.turn_outcome.tool_action == "handoff"
    assert artifact.turn_outcome.intent == "runtime_error"
    assert artifact.turn_outcome.meta["degrade_path"] is True
    assert artifact.turn_outcome.meta["control_label"] == "runtime_error"
    assert artifact.turn_outcome.observability.transport_reason == "fallback_send_failed"


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


def test_clarify_limit_escalation_records_canonical_handoff_action() -> None:
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id="client-123",
        state=ConversationState.BOT_ACTIVE.value,
    )
    saved_message = SimpleNamespace(id="msg-1", message_metadata={})
    user = SimpleNamespace(id="user-123")
    db = Mock()
    db.commit = Mock()
    record_message_meta = Mock()

    with patch(
        "app.routers.webhook.guards._reuse_active_handover",
        return_value=(None, True, True),
    ), patch(
        "app.routers.webhook.guards._reset_low_confidence_retry"
    ), patch(
        "app.routers.webhook.guards._record_decision_trace"
    ), patch(
        "app.routers.webhook.guards._record_message_decision_meta",
        record_message_meta,
    ), patch(
        "app.routers.webhook.guards._update_message_decision_metadata"
    ), patch(
        "app.routers.webhook.guards.save_message"
    ):
        response = webhook_guards._handle_clarify_limit_escalation(
            db=db,
            conversation=conversation,
            user=user,
            message_text="нужен человек",
            saved_message=saved_message,
            source="truth_gate",
            allow_handover=False,
            send_response=lambda *_args, **_kwargs: True,
        )

    assert response.success is True
    record_message_meta.assert_called_once_with(
        saved_message,
        action="handoff",
        intent="clarify_limit",
        source="truth_gate",
        fast_intent=False,
    )


def _capture_boundary_message_meta(captured: dict[str, object]):
    def _record_message_decision_meta(_saved_message, **payload):
        captured["message_meta"] = payload

    return _record_message_decision_meta


def _capture_boundary_override(captured: dict[str, object]):
    def _apply_policy_guard_override(**payload):
        captured["override"] = payload

    return _apply_policy_guard_override


def test_policy_timeout_booking_specialist_boundary_records_canonical_collect_action() -> None:
    from app.services.policy_timeout_booking_specialist_boundary_service import (
        PolicyTimeoutBookingSpecialistBoundaryRuntimeHooks,
        PolicyTimeoutBookingSpecialistBoundaryRuntimeInput,
        handle_policy_timeout_booking_specialist_boundary,
    )

    captured: dict[str, object] = {}

    response = handle_policy_timeout_booking_specialist_boundary(
        runtime_input=PolicyTimeoutBookingSpecialistBoundaryRuntimeInput(
            mode="specialist_followup",
            conversation=SimpleNamespace(id=uuid4(), state="bot_active"),
            saved_message=SimpleNamespace(id="msg-1"),
            now=datetime(2026, 4, 3, 18, 0, tzinfo=timezone.utc),
            policy_core_mode="degraded_fallback",
            policy_core_degrade_reason="timeout",
            reason_code="timeout_degrade",
            guard_reason="policy_core_timeout_pending_specialist",
            booking_state={"active": True, "service": "маникюр"},
            collect_slot="specialist",
            expected_reply_type="specialist",
            expected_reply_reason="booking_specialist_followup",
            active_question_relation="referent_followup",
            specialist_name="Динара",
        ),
        hooks=PolicyTimeoutBookingSpecialistBoundaryRuntimeHooks(
            get_conversation_context=lambda *_args, **_kwargs: {},
            set_booking_context=lambda context, booking_state: {**context, "booking": booking_state},
            set_expected_reply_context=lambda **kwargs: kwargs["context"],
            set_conversation_context=lambda *_args, **_kwargs: None,
            apply_policy_guard_override=_capture_boundary_override(captured),
            sync_policy_plan_audit=lambda **_kwargs: None,
            record_decision_trace=lambda *_args, **_kwargs: None,
            record_message_decision_meta=_capture_boundary_message_meta(captured),
            update_message_decision_metadata=lambda *_args, **_kwargs: None,
            format_specialist_followup_prompt=lambda **_kwargs: "Какого специалиста предпочитаете?",
            send_and_save=lambda text: (text, True),
            commit=lambda: None,
            handle_booking_interrupt=lambda **_kwargs: None,
        ),
    )

    assert response.bot_response == "Какого специалиста предпочитаете?"
    assert captured["override"] == {
        "final_action": "collect",
        "final_tool_action": "collect",
        "reason_code": "timeout_degrade",
        "reason": "policy_core_timeout_pending_specialist",
    }
    assert captured["message_meta"] == {
        "action": "collect",
        "intent": "booking",
        "source": "policy_core_guard",
        "fast_intent": False,
    }


def test_policy_timeout_booking_time_followup_boundary_records_canonical_collect_action() -> None:
    from app.services.policy_timeout_booking_time_followup_boundary_service import (
        PolicyTimeoutBookingTimeFollowupBoundaryRuntimeHooks,
        PolicyTimeoutBookingTimeFollowupBoundaryRuntimeInput,
        handle_policy_timeout_booking_time_followup_boundary,
    )

    captured: dict[str, object] = {}

    response = handle_policy_timeout_booking_time_followup_boundary(
        runtime_input=PolicyTimeoutBookingTimeFollowupBoundaryRuntimeInput(
            conversation=SimpleNamespace(id=uuid4(), state="bot_active"),
            saved_message=SimpleNamespace(id="msg-2"),
            now=datetime(2026, 4, 3, 18, 5, tzinfo=timezone.utc),
            message_count=4,
            branch_id=None,
            policy_core_mode="degraded_fallback",
            policy_core_degrade_reason="timeout",
            reason_code="timeout_degrade",
            guard_reason="booking_time_availability_followup",
            booking_state={"active": True, "service": "маникюр"},
            collect_slot="datetime",
            current_booking_datetime="2026-04-04 17:45",
            alternate_booking_datetime="2026-04-04 18:00",
            expected_reply_type="time",
            expected_reply_reason="booking_time_availability_followup",
        ),
        hooks=PolicyTimeoutBookingTimeFollowupBoundaryRuntimeHooks(
            get_conversation_context=lambda *_args, **_kwargs: {"context_manager": {}},
            set_booking_context=lambda context, booking_state: {**context, "booking": booking_state},
            set_expected_reply_context=lambda **kwargs: kwargs["context"],
            get_context_manager=lambda context: context.get("context_manager", {}),
            sync_canonical_dialog_state=lambda manager, **_kwargs: manager,
            set_context_manager=lambda context, manager: {**context, "context_manager": manager},
            get_canonical_dialog_state=lambda manager: manager.get("canonical_dialog_state", {}),
            sync_session_memory_interaction_state=lambda current_context, interaction_state, now: (
                current_context,
                {"interaction_state": interaction_state},
            ),
            set_conversation_context=lambda *_args, **_kwargs: None,
            record_session_memory_update=lambda *_args, **_kwargs: None,
            apply_policy_guard_override=_capture_boundary_override(captured),
            sync_policy_plan_audit=lambda **_kwargs: None,
            record_decision_trace=lambda *_args, **_kwargs: None,
            record_message_decision_meta=_capture_boundary_message_meta(captured),
            update_message_decision_metadata=lambda *_args, **_kwargs: None,
            build_response=lambda **_kwargs: "Уточните время",
            combine_sidecar=lambda sidecar, response_text: f"{sidecar} {response_text}",
            maybe_apply_consult_return=lambda **kwargs: kwargs["bot_response"],
            reset_low_confidence_retry=lambda *_args, **_kwargs: None,
            send_and_save=lambda text: (text, True),
            commit=lambda: None,
        ),
    )

    assert response.bot_response == "Уточните время"
    assert captured["override"] == {
        "final_action": "collect",
        "final_tool_action": "collect",
        "reason_code": "timeout_degrade",
        "reason": "booking_time_availability_followup",
    }
    assert captured["message_meta"] == {
        "action": "collect",
        "intent": "booking",
        "source": "llm_policy_core",
        "fast_intent": False,
    }


def test_policy_timeout_recovery_boundary_fact_fallback_records_canonical_fact_action() -> None:
    from app.services.policy_timeout_recovery_boundary_service import (
        PolicyTimeoutRecoveryBoundaryRuntimeHooks,
        PolicyTimeoutRecoveryBoundaryRuntimeInput,
        handle_policy_timeout_recovery_boundary,
    )

    captured: dict[str, object] = {}

    response = handle_policy_timeout_recovery_boundary(
        runtime_input=PolicyTimeoutRecoveryBoundaryRuntimeInput(
            mode="fact_fallback",
            conversation=SimpleNamespace(id=uuid4(), state="bot_active"),
            saved_message=SimpleNamespace(id="msg-3"),
            now=datetime(2026, 4, 3, 18, 10, tzinfo=timezone.utc),
            policy_core_mode="degraded_fallback",
            policy_core_degrade_reason="timeout",
            response_text="Маникюр стоит 2500 ₸.",
            fallback_intent="pricing",
            expected_reply_type="time",
            expected_reply_reason="booking_interrupt",
            info_sections=["pricing"],
        ),
        hooks=PolicyTimeoutRecoveryBoundaryRuntimeHooks(
            get_conversation_context=lambda *_args, **_kwargs: {},
            set_style_reference_pending=lambda context, payload: {**context, "style": payload},
            set_conversation_context=lambda *_args, **_kwargs: None,
            set_expected_reply_context=lambda **kwargs: kwargs["context"],
            apply_policy_guard_override=_capture_boundary_override(captured),
            sync_policy_plan_audit=lambda **_kwargs: None,
            record_decision_trace=lambda *_args, **_kwargs: None,
            record_message_decision_meta=_capture_boundary_message_meta(captured),
            update_message_decision_metadata=lambda *_args, **_kwargs: None,
            send_and_save=lambda text: (text, True),
            commit=lambda: None,
        ),
    )

    assert response.bot_response == "Маникюр стоит 2500 ₸."
    assert captured["override"] == {
        "final_action": "fact",
        "final_tool_action": "pack.fact_fallback",
        "reason_code": "timeout_degrade",
        "reason": "policy_core_timeout_fact_fallback",
    }
    assert captured["message_meta"] == {
        "action": "fact",
        "intent": "pricing",
        "source": "llm_policy_core",
        "fast_intent": False,
    }


def test_policy_timeout_degrade_boundary_pending_slot_question_records_canonical_collect_action() -> None:
    from app.services.policy_timeout_degrade_boundary_service import (
        PolicyTimeoutDegradeBoundaryRuntimeHooks,
        PolicyTimeoutDegradeBoundaryRuntimeInput,
        handle_policy_timeout_degrade_boundary,
    )

    captured: dict[str, object] = {}

    result = handle_policy_timeout_degrade_boundary(
        runtime_input=PolicyTimeoutDegradeBoundaryRuntimeInput(
            mode="pending_slot_question",
            db=SimpleNamespace(),
            conversation=SimpleNamespace(id=uuid4(), state="bot_active"),
            user=SimpleNamespace(id="user-4"),
            saved_message=SimpleNamespace(id="msg-4"),
            message_text="Не понял",
            allow_handover=True,
            now=datetime(2026, 4, 3, 18, 15, tzinfo=timezone.utc),
            policy_core_mode="degraded_fallback",
            policy_core_degrade_reason="timeout",
            retry_intent="booking",
            retry_reason="timeout",
            retry_limit=2,
            retry_limit_decision="clarify_limit",
            retry_limit_reason="policy_core_timeout_limit",
            escalation_intent="booking",
            escalation_fallback_message="Помогу продолжить запись.",
            retry_count=1,
            continue_decision="timeout_pending_slot_question",
            continue_missing_slot="datetime",
            continue_response_text="Уточните, пожалуйста, время.",
            continue_expected_reply_type="time",
            continue_expected_reply_reason="booking_slot_guidance",
            continue_pending_question_decision="booking_slot_guidance",
            continue_pending_question_act="ask_about_requested_slot",
            continue_pending_question_target="time",
            continue_recovery="timeout_pending_slot_question",
            continue_guard_reason_code="timeout_degrade",
            continue_guard_reason="policy_core_timeout_pending_question",
        ),
        hooks=PolicyTimeoutDegradeBoundaryRuntimeHooks(
            get_conversation_context=lambda *_args, **_kwargs: {},
            get_context_manager=lambda *_args, **_kwargs: {},
            timeout_degrade_retry_status=lambda *_args, **_kwargs: (0, False),
            set_expected_reply_context=lambda **kwargs: kwargs["context"],
            record_context_manager_decision=lambda *_args, **_kwargs: None,
            apply_policy_guard_override=_capture_boundary_override(captured),
            sync_policy_plan_audit=lambda **_kwargs: None,
            record_decision_trace=lambda *_args, **_kwargs: None,
            update_message_decision_metadata=lambda *_args, **_kwargs: None,
            handle_clarify_limit_escalation=lambda **_kwargs: None,
            register_clarify_attempt=lambda **_kwargs: 1,
            record_message_decision_meta=_capture_boundary_message_meta(captured),
            send_and_save=lambda text: (text, True),
            commit=lambda: None,
        ),
    )

    assert result.response is not None
    assert result.response.bot_response == "Уточните, пожалуйста, время."
    assert captured["override"] == {
        "final_action": "collect",
        "final_tool_action": "collect",
        "reason_code": "timeout_degrade",
        "reason": "policy_core_timeout_pending_question",
    }
    assert captured["message_meta"] == {
        "action": "collect",
        "intent": "booking",
        "source": "booking_slot_guidance",
        "fast_intent": False,
    }


def test_policy_timeout_degrade_boundary_generic_clarify_records_canonical_collect_action() -> None:
    from app.services.policy_timeout_degrade_boundary_service import (
        PolicyTimeoutDegradeBoundaryRuntimeHooks,
        PolicyTimeoutDegradeBoundaryRuntimeInput,
        handle_policy_timeout_degrade_boundary,
    )

    captured: dict[str, object] = {}

    result = handle_policy_timeout_degrade_boundary(
        runtime_input=PolicyTimeoutDegradeBoundaryRuntimeInput(
            mode="generic_clarify",
            db=SimpleNamespace(),
            conversation=SimpleNamespace(id=uuid4(), state="bot_active"),
            user=SimpleNamespace(id="user-5"),
            saved_message=SimpleNamespace(id="msg-5"),
            message_text="Не понял",
            allow_handover=True,
            now=datetime(2026, 4, 3, 18, 20, tzinfo=timezone.utc),
            policy_core_mode="degraded_fallback",
            policy_core_degrade_reason="timeout",
            retry_intent="policy_timeout_degrade",
            retry_reason="timeout",
            retry_limit=2,
            retry_limit_decision="clarify_limit",
            retry_limit_reason="policy_core_timeout_limit",
            escalation_intent="policy_timeout_degrade",
            escalation_fallback_message="Уточните, пожалуйста.",
            continue_response_text="Уточните, пожалуйста.",
        ),
        hooks=PolicyTimeoutDegradeBoundaryRuntimeHooks(
            get_conversation_context=lambda *_args, **_kwargs: {},
            get_context_manager=lambda *_args, **_kwargs: {},
            timeout_degrade_retry_status=lambda *_args, **_kwargs: (0, False),
            set_expected_reply_context=lambda **kwargs: kwargs["context"],
            record_context_manager_decision=lambda *_args, **_kwargs: None,
            apply_policy_guard_override=_capture_boundary_override(captured),
            sync_policy_plan_audit=lambda **_kwargs: None,
            record_decision_trace=lambda *_args, **_kwargs: None,
            update_message_decision_metadata=lambda *_args, **_kwargs: None,
            handle_clarify_limit_escalation=lambda **_kwargs: None,
            register_clarify_attempt=lambda **_kwargs: 1,
            record_message_decision_meta=_capture_boundary_message_meta(captured),
            send_and_save=lambda text: (text, True),
            commit=lambda: None,
        ),
    )

    assert result.response is not None
    assert result.response.bot_response == "Уточните, пожалуйста."
    assert captured["override"] == {
        "final_action": "collect",
        "final_tool_action": "collect",
        "reason_code": "timeout_degrade",
        "reason": "policy_core_timeout_degrade_clarify",
    }
    assert captured["message_meta"] == {
        "action": "collect",
        "intent": "policy_core_guard",
        "source": "llm_policy_core",
        "fast_intent": False,
    }


@pytest.mark.parametrize(
    ("mode", "expected_intent", "expected_source", "expected_response"),
    [
        ("clarify", "policy_core_guard", "llm_policy_core", "Уточните, пожалуйста."),
        ("collect_prompt", "booking", "policy_core_guard", "Когда вам удобно?"),
        ("pending_question_guidance", "booking", "booking_slot_guidance", "Подскажите удобное время."),
        ("service_grounded_booking", "booking", "policy_core_guard", "Когда вам удобно?"),
    ],
)
def test_policy_validation_boundary_records_canonical_collect_action_for_collect_modes(
    mode: str,
    expected_intent: str,
    expected_source: str,
    expected_response: str,
) -> None:
    captured: dict[str, object] = {}

    response = handle_policy_validation_boundary(
        runtime_input=PolicyValidationBoundaryRuntimeInput(
            mode=mode,
            validation_error="invalid_schema",
            guard_reason="invalid_schema",
            trace_decision="invalid_schema_collect_contract",
            conversation=SimpleNamespace(id=uuid4(), state="bot_active"),
            saved_message=SimpleNamespace(id=f"msg-{mode}"),
            now=datetime(2026, 4, 3, 18, 25, tzinfo=timezone.utc),
            llm_policy_core_meta={"validated": True},
            msg_fact_guard_clarify="Уточните, пожалуйста.",
            booking_state={"active": True},
            collect_slot="datetime",
            requested_slot="datetime",
            pending_question_act="ask_about_requested_slot",
            pending_question_target="time",
            msg_booking_pending_question_time_guidance="Подскажите удобное время.",
            service_query="маникюр",
            service_query_source="carryover",
        ),
        hooks=PolicyValidationBoundaryRuntimeHooks(
            classify_policy_core_degrade_reason=lambda *_args, **_kwargs: {"category": "timeout"},
            sync_semantic_arbiter_meta=lambda *_args, **_kwargs: None,
            sync_policy_plan_audit=lambda **_kwargs: None,
            backfill_policy_degraded_referent_evidence=lambda *_args, **_kwargs: None,
            update_message_decision_metadata=lambda *_args, **_kwargs: None,
            apply_policy_guard_override=_capture_boundary_override(captured),
            record_decision_trace=lambda *_args, **_kwargs: None,
            record_message_decision_meta=_capture_boundary_message_meta(captured),
            get_conversation_context=lambda *_args, **_kwargs: {"context_manager": {}},
            get_context_manager=lambda context: context.get("context_manager", {}),
            get_clarify_attempt_state=lambda *_args, **_kwargs: (0, None),
            record_context_manager_decision=lambda *_args, **_kwargs: None,
            handle_clarify_limit_escalation=lambda **_kwargs: None,
            register_clarify_attempt=lambda **_kwargs: 1,
            set_booking_context=lambda context, booking_state: {**context, "booking": booking_state},
            set_service_hint=lambda context, *_args, **_kwargs: context,
            set_expected_reply_context=lambda **kwargs: kwargs["context"],
            set_conversation_context=lambda *_args, **_kwargs: None,
            expected_reply_for_booking_question=lambda *_args, **_kwargs: "time",
            booking_prompt_for_expected_reply_type=lambda *_args, **_kwargs: "Когда вам удобно?",
            reset_low_confidence_retry=lambda *_args, **_kwargs: None,
            combine_sidecar=lambda *parts: "\n".join(part for part in parts if part),
            maybe_apply_consult_return=lambda **kwargs: kwargs["bot_response"],
            send_and_save=lambda text: (text, True),
            commit=lambda: None,
        ),
    )

    assert response.bot_response == expected_response
    assert captured["override"] == {
        "final_action": "collect",
        "final_tool_action": "collect",
        "reason_code": "contract_validation_failure",
        "reason": "invalid_schema",
    }
    assert captured["message_meta"] == {
        "action": "collect",
        "intent": expected_intent,
        "source": expected_source,
        "fast_intent": False,
    }


def test_policy_core_guard_orchestration_handoff_policy_blocked_records_canonical_collect_action() -> None:
    from app.services.policy_core_guard_orchestration_service import (
        PolicyCoreGuardOrchestrationRuntimeHooks,
        PolicyCoreGuardOrchestrationRuntimeInput,
        handle_policy_core_guard_orchestration,
    )

    captured: dict[str, object] = {}

    response = handle_policy_core_guard_orchestration(
        runtime_input=PolicyCoreGuardOrchestrationRuntimeInput(
            mode="handoff_policy_blocked_safe_reply",
            conversation=SimpleNamespace(id=uuid4(), state="bot_active"),
            saved_message=SimpleNamespace(id="msg-6"),
            policy_core_mode="degraded_fallback",
            policy_core_degrade_reason="blocked",
            response_text="Опишите детали записи, и я помогу продолжить.",
            capability_reason="handoff_not_allowed",
        ),
        hooks=PolicyCoreGuardOrchestrationRuntimeHooks(
            apply_policy_guard_override=_capture_boundary_override(captured),
            sync_policy_plan_audit=lambda **_kwargs: None,
            record_decision_trace=lambda *_args, **_kwargs: None,
            record_message_decision_meta=_capture_boundary_message_meta(captured),
            update_message_decision_metadata=lambda *_args, **_kwargs: None,
            send_and_save=lambda text: (text, True),
            reuse_active_handover=lambda **_kwargs: (None, False, False),
            create_pending_escalation_with_notification=lambda **_kwargs: SimpleNamespace(ok=True, telegram_sent=True),
            record_escalation_metric=lambda *_args, **_kwargs: None,
            timeout_booking_completion_override=lambda action: (action or "collect", action or "collect"),
            commit=lambda: None,
        ),
    )

    assert response.bot_response == "Опишите детали записи, и я помогу продолжить."
    assert captured["override"] == {
        "final_action": "collect",
        "final_tool_action": "collect",
        "reason_code": "safety_policy_block",
        "reason": "handoff_policy_blocked",
    }
    assert captured["message_meta"] == {
        "action": "collect",
        "intent": "policy_core_guard",
        "source": "llm_policy_core",
        "fast_intent": False,
    }


def test_policy_core_guard_orchestration_handoff_mode_records_canonical_handoff_action() -> None:
    from app.services.policy_core_guard_orchestration_service import (
        PolicyCoreGuardOrchestrationRuntimeHooks,
        PolicyCoreGuardOrchestrationRuntimeInput,
        handle_policy_core_guard_orchestration,
    )

    captured: dict[str, object] = {}

    response = handle_policy_core_guard_orchestration(
        runtime_input=PolicyCoreGuardOrchestrationRuntimeInput(
            mode="guard_handoff_safe",
            conversation=SimpleNamespace(id=uuid4(), state="bot_active"),
            saved_message=SimpleNamespace(id="msg-7"),
            policy_core_mode="degraded_fallback",
            policy_core_degrade_reason="timeout",
            user=SimpleNamespace(id="user-7"),
            handover_message="Соедините с менеджером.",
            allow_handover=True,
            reason_code="timeout_degrade",
            response_text="Передал менеджеру.",
            error_response_text="Передача не удалась.",
        ),
        hooks=PolicyCoreGuardOrchestrationRuntimeHooks(
            apply_policy_guard_override=_capture_boundary_override(captured),
            sync_policy_plan_audit=lambda **_kwargs: None,
            record_decision_trace=lambda *_args, **_kwargs: None,
            record_message_decision_meta=_capture_boundary_message_meta(captured),
            update_message_decision_metadata=lambda *_args, **_kwargs: None,
            send_and_save=lambda text: (text, True),
            reuse_active_handover=lambda **_kwargs: (None, False, False),
            create_pending_escalation_with_notification=lambda **_kwargs: SimpleNamespace(ok=True, telegram_sent=True),
            record_escalation_metric=lambda *_args, **_kwargs: None,
            timeout_booking_completion_override=lambda action: (action or "collect", action or "collect"),
            commit=lambda: None,
        ),
    )

    assert response.bot_response == "Передал менеджеру."
    assert captured["override"] == {
        "final_action": "handoff",
        "final_tool_action": "handoff",
        "reason_code": "timeout_degrade",
        "reason": "policy_core_guard_handoff_safe",
    }
    assert captured["message_meta"] == {
        "action": "handoff",
        "intent": "policy_core_guard",
        "source": "llm_policy_core",
        "fast_intent": False,
    }


def test_turn_executor_check_booking_fact_routes_through_tool_registry_with_conversation_id() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "check_booking",
            "action": "fact",
            "tool_action": "calendar.get_booking",
            "reason": "calendar_get_booking_existing_booking_context_carries_customer_and_datetime_reference",
            "subject_kind": "booking",
            "capability": "booking_manage",
            "resolution_mode": "direct",
            "slots": {
                "name": "Алина",
                "datetime": "tomorrow 15:00",
            },
        },
        interaction_owner="llm_policy_core",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )
    conversation_id = uuid4()

    with patch("app.services.tool_registry_service.execute_tool_action") as mock_execute:
        mock_execute.return_value = ToolExecutionResult(
            handled=True,
            ok=True,
            response_text="Запись: маникюр, мастер, 03.04 15:00.",
            error_code=None,
            decision_meta={
                "tool_action": "calendar.get_booking",
                "tool_decision": "ok",
                "appointment_id": str(uuid4()),
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": "calendar.get_booking",
            },
        )
        result = TurnExecutor().execute(
            decision,
            db=object(),
            message_text="Проверьте мою запись.",
            client_slug="demo_salon",
            branch_id=uuid4(),
            booking_state=None,
            user_name=None,
            user_phone=None,
            now=datetime.now(timezone.utc),
            conversation_id=conversation_id,
        )

    assert result.text == "Запись: маникюр, мастер, 03.04 15:00."
    assert result.tool_action == "calendar.get_booking"
    assert result.tool_decision == "ok"
    assert mock_execute.call_args.kwargs["conversation_id"] == conversation_id


def test_turn_executor_check_booking_fact_preserves_tool_registry_not_found_reply() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "check_booking",
            "action": "fact",
            "tool_action": "calendar.get_booking",
            "reason": "calendar_get_booking_collect_reference",
            "subject_kind": "booking",
            "capability": "booking_manage",
            "resolution_mode": "direct",
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="llm_policy_core",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    with patch("app.services.tool_registry_service.execute_tool_action") as mock_execute:
        mock_execute.return_value = ToolExecutionResult(
            handled=True,
            ok=False,
            response_text=(
                "Проверил: пока не вижу подтверждённой записи. "
                "Если нужно перенести, подтвердить или отменить запись, "
                "подскажите номер телефона и примерную дату/время, и я помогу найти."
            ),
            error_code="appointment_not_found",
            decision_meta={
                "tool_action": "calendar.get_booking",
                "tool_decision": "not_found",
            },
            trace={
                "stage": "tool_registry",
                "decision": "not_found",
                "tool_action": "calendar.get_booking",
            },
        )
        result = TurnExecutor().execute(
            decision,
            db=object(),
            message_text="Проверьте мою запись.",
            client_slug="demo_salon",
            branch_id=uuid4(),
            booking_state=None,
            user_name=None,
            user_phone=None,
            now=datetime.now(timezone.utc),
            conversation_id=uuid4(),
        )

    assert "подскажите номер телефона" in result.text
    assert result.tool_action == "calendar.get_booking"
    assert result.tool_decision == "not_found"
    assert "booking_verification_prompt" not in result.meta
    _, kwargs = mock_execute.call_args
    assert kwargs["message_text"] == "Проверьте мою запись."
    assert kwargs["expected_reply_type"] == "time"


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


def test_turn_executor_non_owner_master_query_requires_owner_grounded_service_referent() -> None:
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

    assert result.text == "Я уточню это для вас."
    assert result.tool_decision == "fact_unresolved"
    assert result.meta["fact_fallback"] is True
    assert result.meta["fact_fallback_reason"] == "fact_execution_unresolved"


def test_turn_executor_uses_team_summary_for_grounded_master_query_when_runtime_pack_has_no_profiles() -> None:
    truth = {
        "services_catalog": {
            "services": [
                {
                    "name": "Стрижка",
                    "aliases": ["стрижка"],
                    "duration_text": "Обычно 20–60 минут.",
                }
            ],
            "duration_clarify": "По времени зависит от услуги. Какая именно?",
        },
        "price_list": [
            {
                "category": "Парикмахерский зал",
                "items": [{"name": "Укладка феном", "price": 3500}],
            }
        ],
        "team": {
            "hair": "Колористы 5+ лет, делают блонд, балаяж и другие сложные окрашивания."
        },
    }
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "master_query",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "pack_refs": ["master"],
            "reason": "master_question",
            "goal": "booking",
            "referents": {
                "service": {
                    "value": "укладка",
                    "entity_id": "svc:styling",
                    "entity_type": "service",
                    "source_ref": "inline_user",
                }
            },
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "direct",
        }
    )
    decision = TurnPlanner().build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="catalog.service_query",
        binding_tool_args={"service_query": "укладка"},
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    with use_runtime_truth_override(_runtime_truth_payload(truth)):
        result = TurnExecutor().execute(
            decision,
            db=None,
            message_text="Кто делает укладку?",
            client_slug="demo_salon",
            branch_id=None,
            booking_state=None,
            user_name=None,
            user_phone=None,
            now=datetime.now(timezone.utc),
        )

    assert "Укладка феном" in result.text
    assert "администратор" not in result.text.casefold()
    assert result.tool_decision == "master"
    assert result.meta.get("master_query_contract") == "team.v1"
    assert result.meta.get("master_reply_mode") == "team_match"
    assert result.meta.get("master_team_key") == "hair"
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
    assert "автоматически не подтверждаю" in result.text
    assert result.tool_decision == "slot_constraint"
    assert result.meta.get("pending_question_act") == "slot_constraint"
    assert result.meta.get("pending_question_target") == "time"
    assert result.meta.get("question_contract") is True


def test_turn_executor_realizes_slot_constraint_collect_from_canonical_owner_contract() -> None:
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "action": "collect",
            "intent": "booking",
            "goal": "booking",
            "capability": "bookability",
            "tool_action_hint": "collect",
            "slots": {"service": "Маникюр"},
            "subject_kind": "booking",
            "temporal_scope": "weekday",
            "resolution_mode": "slot_constraint",
            "expected_reply_type": "time",
            "reason": "active_booking_temporal_clue_followup",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "alternate_datetime": "пятница утром",
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
    decision = TurnPlanner().build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        binding_tool_args={},
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="А как насчет пятницы на утро?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "Маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert "пятница утром" in result.text
    assert result.tool_decision == "slot_constraint"
    assert result.meta.get("pending_question_act") == "slot_constraint"
    assert result.meta.get("pending_question_target") == "time"
    assert result.meta.get("alternate_datetime") == "пятница утром"
    assert result.meta.get("slot_values") == {
        "service": "Маникюр",
        "datetime": "пятница утром",
    }
    assert result.meta.get("question_contract") is True


def test_turn_executor_slot_constraint_prompt_normalizes_prepositional_alternate_datetime() -> None:
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "action": "collect",
            "intent": "booking",
            "goal": "booking",
            "capability": "bookability",
            "tool_action_hint": "collect",
            "slots": {"service": "Маникюр"},
            "subject_kind": "booking",
            "temporal_scope": "weekday",
            "resolution_mode": "slot_constraint",
            "expected_reply_type": "time",
            "reason": "active_booking_availability_followup",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "alternate_datetime": "в понедельник",
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
    decision = TurnPlanner().build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        binding_tool_args={},
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Какое время доступно?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "Маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert "на в понедельник" not in result.text
    assert "в понедельник" in result.text
    assert "точное время" in result.text.casefold()
    assert "автоматически не подтверждаю" not in result.text
    assert result.tool_decision == "slot_constraint"
    assert result.meta.get("alternate_datetime") == "в понедельник"


def test_turn_executor_slot_constraint_with_day_only_anchor_asks_precise_time() -> None:
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "action": "collect",
            "intent": "booking",
            "goal": "booking",
            "capability": "bookability",
            "tool_action_hint": "collect",
            "slots": {"service": "Маникюр"},
            "subject_kind": "booking",
            "temporal_scope": "today",
            "resolution_mode": "slot_constraint",
            "expected_reply_type": "time",
            "reason": "active_booking_same_day_availability_followup",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "alternate_datetime": "сегодня",
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
    decision = TurnPlanner().build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        binding_tool_args={},
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="У вас есть время на сегодня?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "Маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert "сегодня" in result.text
    assert "точное время" in result.text.casefold()
    assert "автоматически не подтверждаю" not in result.text
    assert result.tool_decision == "slot_constraint"
    assert result.meta.get("pending_question_act") == "slot_constraint"
    assert result.meta.get("pending_question_target") == "time"
    assert result.meta.get("alternate_datetime") == "сегодня"


def test_turn_executor_slot_constraint_preserves_candidate_datetime_in_runtime_profile() -> None:
    planner = TurnPlanner()
    runtime = ConsultantRuntime()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "action": "collect",
            "intent": "booking",
            "goal": "booking",
            "capability": "bookability",
            "tool_action_hint": "collect",
            "slots": {"service": "Маникюр"},
            "subject_kind": "booking",
            "temporal_scope": "day",
            "resolution_mode": "slot_constraint",
            "expected_reply_type": "time",
            "reason": "active_booking_temporal_clue_followup",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "alternate_datetime": "завтра вечером",
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
        binding_tool_action="collect",
        binding_tool_args={},
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    execution = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Давайте на завтра вечером.",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "Маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime(2026, 4, 7, 0, 0, tzinfo=timezone.utc),
    )

    updated, dialog_state, booking_payload = DialogStateService().write_runtime_payload(
        {},
        decision=decision,
        execution_meta=execution.meta,
        now=datetime(2026, 4, 7, 0, 0, tzinfo=timezone.utc),
    )
    runtime_state = LoadedRuntimeState(
        context=updated,
        dialog_state=dialog_state,
        booking_state=booking_payload or {},
    )

    profile = runtime._build_policy_core_memory_profile(runtime_state)

    assert execution.meta.get("slot_values") == {
        "service": "Маникюр",
        "datetime": "завтра вечером",
    }
    assert (booking_payload or {}).get("datetime") == "завтра вечером"
    assert profile["slot_state"]["datetime"] == "завтра вечером"
    assert profile["semantic_contract"]["alternate_datetime"] == "завтра вечером"


def test_turn_executor_slot_constraint_replaces_stale_datetime_with_new_candidate() -> None:
    planner = TurnPlanner()
    runtime = ConsultantRuntime()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "action": "collect",
            "intent": "booking",
            "goal": "booking",
            "capability": "bookability",
            "tool_action_hint": "collect",
            "slots": {"service": "Маникюр"},
            "subject_kind": "booking",
            "temporal_scope": "day",
            "resolution_mode": "slot_constraint",
            "expected_reply_type": "time",
            "reason": "active_booking_temporal_clue_followup",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "alternate_datetime": "завтра вечером",
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
        binding_tool_action="collect",
        binding_tool_args={},
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    execution = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Давайте на завтра вечером.",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "Маникюр", "datetime": "11:30"},
        user_name=None,
        user_phone=None,
        now=datetime(2026, 4, 7, 0, 0, tzinfo=timezone.utc),
    )

    updated, dialog_state, booking_payload = DialogStateService().write_runtime_payload(
        {},
        decision=decision,
        execution_meta=execution.meta,
        now=datetime(2026, 4, 7, 0, 0, tzinfo=timezone.utc),
    )
    runtime_state = LoadedRuntimeState(
        context=updated,
        dialog_state=dialog_state,
        booking_state=booking_payload or {},
    )

    profile = runtime._build_policy_core_memory_profile(runtime_state)

    assert execution.meta.get("slot_values") == {
        "service": "Маникюр",
        "datetime": "завтра вечером",
    }
    assert (booking_payload or {}).get("datetime") == "завтра вечером"
    assert profile["slot_state"]["datetime"] == "завтра вечером"
    assert profile["semantic_contract"]["alternate_datetime"] == "завтра вечером"


def test_turn_executor_requested_slot_availability_with_carried_day_asks_time_only() -> None:
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "action": "collect",
            "intent": "booking",
            "goal": "booking",
            "capability": "bookability",
            "tool_action_hint": "collect",
            "slots": {"service": "Маникюр"},
            "subject_kind": "booking",
            "temporal_scope": "weekday",
            "resolution_mode": "ask_about_requested_slot",
            "expected_reply_type": "time",
            "reason": "active_booking_requested_slot_availability_followup",
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
    decision = TurnPlanner().build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        binding_tool_args={},
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Какое время доступно?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "Маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.text == "На какое время вам удобно?"
    assert result.tool_decision == "datetime"


def test_turn_executor_service_refinement_keeps_time_collect_without_slot_confirmation_fallback() -> None:
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "action": "collect",
            "intent": "booking",
            "goal": "booking",
            "capability": "bookability",
            "tool_action_hint": "collect",
            "slots": {"service": "Маникюр с укреплением ногтей"},
            "subject_kind": "booking",
            "temporal_scope": "day",
            "resolution_mode": "ask_about_requested_slot",
            "expected_reply_type": "time",
            "reason": "service_refinement_keeps_active_time_continuity",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "alternate_datetime": "завтра",
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
    decision = TurnPlanner().build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        binding_tool_args={},
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Мне нужны услуги с укреплением ногтей.",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "Маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert "Маникюр с укреплением ногтей" in result.text
    assert "завтра" in result.text
    assert "автоматически не подтверждаю" not in result.text
    assert result.tool_decision == "slot_constraint"
    assert result.meta.get("pending_question_act") == "slot_constraint"
    assert result.meta.get("pending_question_target") == "time"
    assert result.meta.get("alternate_datetime") == "завтра"
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
    assert "semantic_contract" not in result.meta


def test_turn_executor_specialist_followup_with_carried_day_asks_only_for_time() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "reason": "user_requested_specific_master_keep_time_collect_with_carried_day",
            "goal": "booking",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "specialist": {
                    "value": "Динара",
                    "entity_type": "specialist",
                    "source_ref": "user_message",
                },
            },
            "subject_kind": "specialist",
            "capability": "bookability",
            "resolution_mode": "referent_followup",
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
            "temporal_scope": "weekday",
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="referent_followup",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Я хочу записаться к Динаре.",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "Маникюр", "datetime": "пятницу"},
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert "Динара" in result.text
    assert "мастер" in result.text.casefold()
    assert "время" in result.text.casefold()
    assert "дат" not in result.text.casefold()
    assert result.tool_decision == "datetime"
    assert result.meta["pending_question_contract"]["pending_question_target"] == "specialist"
    assert result.meta["pending_question_contract"]["active_question_relation"] == "referent_followup"


def test_turn_executor_adds_pricing_info_sections_for_price_reply() -> None:
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "pricing",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "fact_refs": ["pricing"],
            "reason": "pricing_question",
            "goal": "booking",
            "subject_kind": "service",
            "capability": "pricing",
            "resolution_mode": "policy_fact",
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
    decision = TurnPlanner().build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="catalog.service_query",
        binding_tool_args={"service_query": "Маникюр"},
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
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
    assert "semantic_contract" not in result.meta


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
        "app.services.pack_runtime_compat.get_pack_decision",
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


def test_turn_executor_renders_owner_greeting_smalltalk_without_info_fallback() -> None:
    planner = TurnPlanner()
    semantic_payload = build_test_semantic_decision_payload(
        {
            "intent": "greeting",
            "action": "fact",
            "tool_action_hint": "info",
            "reason": "user_greeting",
            "subject_kind": "general",
            "resolution_mode": "direct",
            "temporal_scope": "none",
            "goal": "greeting",
        }
    )
    binding_payload = {
        "schema_version": "binding_plan.v1",
        "binding_id": "binding-owner-greeting",
        "decision_id": semantic_payload["decision_id"],
        "binding_outcome_type": "tool_call",
        "selected_tool_or_workflow_ref": "info",
        "authz_scope": {},
        "resolved_args": {},
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
        db=None,
        message_text="Здравствуйте",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.text == "Здравствуйте! Могу помочь с услугами, ценами или записью."
    assert result.tool_action == "catalog.location"
    assert result.tool_decision == "smalltalk_direct"
    assert result.meta["smalltalk_direct"] is True
    assert result.meta["smalltalk_intent"] == "greeting"
    assert result.meta["fact_fallback"] is False
    assert result.meta.get("fact_fallback_reason") is None
    assert result.meta["fact_contract"]["result"]["response_generated"] is True
    assert result.meta["fact_contract"]["result"]["resolution_source"] == "semantic_smalltalk_direct"


def test_turn_executor_renders_owner_thanks_smalltalk_without_info_fallback() -> None:
    planner = TurnPlanner()
    semantic_payload = build_test_semantic_decision_payload(
        {
            "intent": "thanks",
            "action": "fact",
            "tool_action_hint": "info",
            "reason": "user_thanks",
            "subject_kind": "general",
            "resolution_mode": "direct",
            "temporal_scope": "none",
            "goal": "thanks",
        }
    )
    binding_payload = {
        "schema_version": "binding_plan.v1",
        "binding_id": "binding-owner-thanks",
        "decision_id": semantic_payload["decision_id"],
        "binding_outcome_type": "tool_call",
        "selected_tool_or_workflow_ref": "info",
        "authz_scope": {},
        "resolved_args": {},
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
        db=None,
        message_text="Спасибо",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.text == "Рад помочь. Если нужно — подскажу по услугам, ценам или записи."
    assert result.tool_action == "catalog.location"
    assert result.tool_decision == "smalltalk_direct"
    assert result.meta["smalltalk_direct"] is True
    assert result.meta["smalltalk_intent"] == "thanks"
    assert result.meta["fact_fallback"] is False
    assert result.meta.get("fact_fallback_reason") is None
    assert result.meta["fact_contract"]["result"]["response_generated"] is True
    assert result.meta["fact_contract"]["result"]["resolution_source"] == "semantic_smalltalk_direct"


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
        "get_pack_runtime",
        lambda client_slug=None: SimpleNamespace(
            normalize_text=lambda text: text.casefold(),
            detect_promotion_intent=lambda normalized: "promotions",
            has_duration_signal=lambda normalized, message=None: False,
            has_price_signal=lambda normalized, message=None: False,
            format_reply_from_truth=lambda *args, **kwargs: "Есть акция 10%.",
        ),
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


def test_turn_executor_first_fact_family_requires_owner_exact_tool_binding(monkeypatch) -> None:
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

    assert captured == {}
    assert result.tool_action == "catalog.service_query"
    assert result.tool_decision == "fact_unresolved"
    assert result.meta["fact_manifest_id"] == "default_fact_manifest.v1"
    assert result.meta["fact_requested_refs"] == ["hours"]
    assert result.meta["fact_allowed_refs"] == ["hours"]
    assert result.meta["fact_allowed_sets"] == [["hours"]]
    assert result.meta["fact_emitted_refs"] == []
    fact_contract = result.meta["fact_contract"]
    assert fact_contract["plan"]["bundle_policy"] == "location_base_bundle"
    assert fact_contract["plan"]["allowed_emitted_sets"] == [["hours"]]
    assert fact_contract["result"]["emitted_fact_refs"] == []


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
        "app.services.pack_runtime_compat.get_pack_decision",
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
    assert result.tool_decision == "info_ref_unresolved"
    assert result.meta["fact_fallback"] is True
    assert result.meta["fact_fallback_reason"] == "policy_info_unresolved"
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
        "app.services.pack_runtime_compat.get_pack_decision",
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


def test_turn_executor_mixed_first_turn_fact_scope_hours_and_service_presence_falls_back_to_unresolved(monkeypatch) -> None:
    calls = {"tool_registry": 0, "direct_truth": 0, "pack_runtime": 0}

    def _execute_tool_action(db, **kwargs):
        calls["tool_registry"] += 1
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Работаем ежедневно, без выходных, с 9:00 до 21:00.",
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
    monkeypatch.setattr(
        "app.services.pack_runtime_service.format_reply_from_truth",
        lambda *args, **kwargs: calls.__setitem__("direct_truth", calls["direct_truth"] + 1) or "Маникюр есть.",
    )
    monkeypatch.setattr(
        "app.services.pack_runtime_compat.get_pack_decision",
        lambda *args, **kwargs: calls.__setitem__("pack_runtime", calls["pack_runtime"] + 1)
        or SimpleNamespace(
            response="Маникюр есть.",
            intent="services_overview",
            meta={"info_sections": ["services_overview"]},
            action="reply",
        ),
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "hours",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": ["hours", "services_overview"],
            "fact_refs": ["hours", "services_overview"],
            "reason": "user_asks_working_hours_and_service_is_manicure",
            "goal": "info",
            "capability": "hours",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Здравствуйте! Вы сегодня работаете? Вы маникюром занимаетесь?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == {"tool_registry": 1, "direct_truth": 0, "pack_runtime": 0}
    assert result.text == "Я уточню это для вас."
    assert result.tool_action == "catalog.location"
    assert result.tool_decision == "fact_family_unresolved"
    assert result.meta["fact_fallback"] is True
    assert result.meta["fact_fallback_reason"] == "first_fact_family_mixed_scope_unresolved"
    assert result.meta["fact_family_cutover"] == "location_hours_parking"
    assert result.meta["family_overlap_fact_refs"] == ["hours"]
    assert result.meta["fact_requested_refs"] == ["hours", "services_overview"]
    assert result.meta["fact_allowed_refs"] == ["hours", "services_overview"]
    assert result.meta["fact_emitted_refs"] == []


def test_turn_executor_composes_mixed_first_turn_hours_and_pricing(monkeypatch) -> None:
    calls: list[tuple[str, list[str]]] = []

    def _execute_tool_action(db, **kwargs):
        calls.append((kwargs["tool_action"], list(kwargs.get("allowed_fact_refs") or [])))
        if kwargs["tool_action"] == "catalog.location":
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Работаем ежедневно, без выходных, с 9:00 до 21:00.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.location",
                    "tool_decision": "hours",
                    "info_sections": ["hours"],
                },
                trace={"stage": "tool_registry", "decision": "hours"},
            )
        if kwargs["tool_action"] == "catalog.service_query":
            if kwargs["allowed_fact_refs"] == ["pricing"]:
                assert kwargs["service_query"] == "педикюр"
                return SimpleNamespace(
                    handled=True,
                    ok=True,
                    response_text="Педикюр — 4 500 ₸.",
                    error_code=None,
                    decision_meta={
                        "tool_action": "catalog.service_query",
                        "tool_decision": "pricing",
                        "info_sections": ["pricing"],
                    },
                    trace={"stage": "tool_registry", "decision": "pricing"},
                )
            if kwargs["allowed_fact_refs"] == ["services_overview"]:
                return SimpleNamespace(
                    handled=False,
                    ok=False,
                    response_text=None,
                    error_code="fact_scope_not_needed",
                    decision_meta={},
                    trace={"stage": "tool_registry", "decision": "fact_scope_not_needed"},
                )
        raise AssertionError(f"unexpected tool action: {kwargs['tool_action']}")

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "hours",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": ["hours", "pricing", "services_overview"],
            "fact_refs": ["hours", "pricing", "services_overview"],
            "reason": "user_asks_working_hours_and_pricing_for_pedikur",
            "goal": "info",
            "capability": "hours",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
            "referents": {
                "service": {
                    "value": "педикюр",
                    "entity_id": "svc:pedicure",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Здравствуйте! Вы сегодня работаете? Сколько стоит педикюр?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == [
        ("catalog.location", ["hours", "pricing", "services_overview"]),
        ("catalog.service_query", ["pricing"]),
        ("catalog.service_query", ["services_overview"]),
    ]
    assert result.text == "Работаем ежедневно, без выходных, с 9:00 до 21:00.\n\nПедикюр — 4 500 ₸."
    assert result.tool_action == "catalog.location"
    assert result.tool_decision == "multi_truth_composed"
    assert result.meta["info_sections"] == ["hours", "pricing"]
    assert result.meta["fact_requested_refs"] == ["hours", "pricing", "services_overview"]
    assert result.meta["fact_allowed_refs"] == ["hours", "pricing"]
    assert result.meta["fact_emitted_refs"] == ["hours", "pricing"]
    assert result.meta["fact_composition"]["secondary_tool_action"] == "catalog.service_query"
    assert result.meta["fact_composition"]["secondary_info_sections"] == ["pricing"]


def test_turn_executor_composes_mixed_first_turn_hours_and_services_overview(
    monkeypatch,
) -> None:
    calls: list[tuple[str, list[str]]] = []

    def _execute_tool_action(db, **kwargs):
        calls.append((kwargs["tool_action"], list(kwargs.get("allowed_fact_refs") or [])))
        if kwargs["tool_action"] == "catalog.location":
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Работаем ежедневно, без выходных, с 9:00 до 21:00.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.location",
                    "tool_decision": "hours",
                    "info_sections": ["hours"],
                },
                trace={"stage": "tool_registry", "decision": "hours"},
            )
        if kwargs["tool_action"] == "catalog.service_query":
            assert kwargs["service_query"] is None
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Мы салон красоты: парикмахерские услуги, маникюр и педикюр.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "services_overview",
                    "info_sections": ["services_overview"],
                },
                trace={"stage": "tool_registry", "decision": "services_overview"},
            )
        raise AssertionError(f"unexpected tool action: {kwargs['tool_action']}")

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "hours",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": ["hours", "services_overview"],
            "fact_refs": ["hours", "services_overview"],
            "reason": "user_asks_working_hours_and_service_presence_for_manicure",
            "goal": "info",
            "capability": "hours",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Здравствуйте! Вы сегодня работаете? Вы маникюром занимаетесь?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == [
        ("catalog.location", ["hours", "services_overview"]),
        ("catalog.service_query", ["services_overview"]),
    ]
    assert (
        result.text
        == "Работаем ежедневно, без выходных, с 9:00 до 21:00.\n\n"
        "Мы салон красоты: парикмахерские услуги, маникюр и педикюр."
    )
    assert result.tool_action == "catalog.location"
    assert result.tool_decision == "multi_truth_composed"
    assert result.meta["info_sections"] == ["hours", "services_overview"]
    assert result.meta["fact_requested_refs"] == ["hours", "services_overview"]
    assert result.meta["fact_allowed_refs"] == ["hours", "services_overview"]
    assert result.meta["fact_emitted_refs"] == ["hours", "services_overview"]
    assert result.meta["fact_composition"]["secondary_tool_action"] == "catalog.service_query"
    assert result.meta["fact_composition"]["secondary_info_sections"] == ["services_overview"]


def test_turn_executor_composes_mixed_first_turn_hours_promotions_and_contact(monkeypatch) -> None:
    calls: list[tuple[str, list[str]]] = []

    def _execute_tool_action(db, **kwargs):
        calls.append((kwargs["tool_action"], list(kwargs.get("allowed_fact_refs") or [])))
        if kwargs["tool_action"] == "catalog.location":
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Работаем ежедневно, без выходных, с 9:00 до 21:00. Телефон в карточке салона не указан. Instagram: https://instagram.com/mira_beauty_kz.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.location",
                    "tool_decision": "ok",
                    "info_sections": ["hours", "contact"],
                },
                trace={"stage": "tool_registry", "decision": "ok"},
            )
        if kwargs["tool_action"] == "catalog.service_query":
            assert kwargs["service_query"] == "маникюр"
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Официальные акции: Первое посещение: 10% (на услуги).",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "promotions",
                    "info_sections": ["promotions"],
                },
                trace={"stage": "tool_registry", "decision": "promotions"},
            )
        raise AssertionError(f"unexpected tool action: {kwargs['tool_action']}")

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "hours",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": ["hours", "promotions", "contact"],
            "fact_refs": ["hours", "promotions", "contact"],
            "reason": "user_asks_working_hours_promotions_and_contact_for_manicure",
            "goal": "info",
            "capability": "hours",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Вы сегодня работаете, есть акции на маникюр и как с вами связаться?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == [
        ("catalog.location", ["hours", "promotions", "contact"]),
        ("catalog.service_query", ["promotions"]),
    ]
    assert "Работаем ежедневно" in result.text
    assert "Официальные акции" in result.text
    assert "Instagram" in result.text
    assert result.tool_action == "catalog.location"
    assert result.tool_decision == "multi_truth_composed"
    assert result.meta["info_sections"] == ["hours", "promotions", "contact"]
    assert result.meta["fact_requested_refs"] == ["hours", "promotions", "contact"]
    assert result.meta["fact_allowed_refs"] == ["hours", "promotions", "contact"]
    assert result.meta["fact_emitted_refs"] == ["hours", "promotions", "contact"]
    assert result.meta["fact_composition"]["secondary_tool_action"] == "catalog.service_query"
    assert result.meta["fact_composition"]["secondary_info_sections"] == ["promotions"]


def test_turn_executor_composes_mixed_first_turn_hours_location_and_promotions(monkeypatch) -> None:
    calls: list[tuple[str, list[str]]] = []

    def _execute_tool_action(db, **kwargs):
        calls.append((kwargs["tool_action"], list(kwargs.get("allowed_fact_refs") or [])))
        if kwargs["tool_action"] == "catalog.location":
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Работаем ежедневно, без выходных, с 9:00 до 21:00. Мы находимся по адресу: Абая 10.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.location",
                    "tool_decision": "ok",
                    "info_sections": ["hours", "location"],
                },
                trace={"stage": "tool_registry", "decision": "ok"},
            )
        if kwargs["tool_action"] == "catalog.service_query":
            assert kwargs["service_query"] == "маникюр"
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Официальные акции: Первое посещение: 10% (на услуги).",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "promotions",
                    "info_sections": ["promotions"],
                },
                trace={"stage": "tool_registry", "decision": "promotions"},
            )
        raise AssertionError(f"unexpected tool action: {kwargs['tool_action']}")

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "hours",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": ["hours", "location", "promotions"],
            "fact_refs": ["hours", "location", "promotions"],
            "reason": "user_asks_working_hours_location_and_promotions_for_manicure",
            "goal": "info",
            "capability": "hours",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Вы сегодня работаете, есть акции на маникюр и где находитесь?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == [
        ("catalog.location", ["hours", "location", "promotions"]),
        ("catalog.service_query", ["promotions"]),
    ]
    assert "Работаем ежедневно" in result.text
    assert "Абая 10" in result.text
    assert "Официальные акции" in result.text
    assert result.tool_action == "catalog.location"
    assert result.tool_decision == "multi_truth_composed"
    assert result.meta["info_sections"] == ["hours", "location", "promotions"]
    assert result.meta["fact_requested_refs"] == ["hours", "location", "promotions"]
    assert result.meta["fact_allowed_refs"] == ["hours", "location", "promotions"]
    assert result.meta["fact_emitted_refs"] == ["hours", "location", "promotions"]
    assert result.meta["fact_composition"]["secondary_tool_action"] == "catalog.service_query"
    assert result.meta["fact_composition"]["secondary_info_sections"] == ["promotions"]


def test_turn_executor_composes_general_hours_location_and_promotions(monkeypatch) -> None:
    calls: list[tuple[str, list[str]]] = []

    def _execute_tool_action(db, **kwargs):
        calls.append((kwargs["tool_action"], list(kwargs.get("allowed_fact_refs") or [])))
        if kwargs["tool_action"] == "catalog.location":
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Работаем ежедневно, без выходных, с 9:00 до 21:00. Мы находимся по адресу: Абая 10.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.location",
                    "tool_decision": "ok",
                    "info_sections": ["hours", "location"],
                },
                trace={"stage": "tool_registry", "decision": "ok"},
            )
        if kwargs["tool_action"] == "catalog.service_query":
            assert not kwargs.get("service_query")
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Официальные акции: Первое посещение: 10% (на услуги).",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "promotions",
                    "info_sections": ["promotions"],
                },
                trace={"stage": "tool_registry", "decision": "promotions"},
            )
        raise AssertionError(f"unexpected tool action: {kwargs['tool_action']}")

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "hours",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": ["hours", "location", "promotions"],
            "fact_refs": ["hours", "location", "promotions"],
            "reason": "user_asks_working_hours_location_and_promotions_without_grounded_service",
            "goal": "info",
            "capability": "hours",
            "subject_kind": "general",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="general_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Вы сегодня работаете, есть акции и где находитесь?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == [
        ("catalog.location", ["hours", "location", "promotions"]),
        ("catalog.service_query", ["promotions"]),
    ]
    assert "Работаем ежедневно" in result.text
    assert "Абая 10" in result.text
    assert "Официальные акции" in result.text
    assert result.tool_action == "catalog.location"
    assert result.tool_decision == "multi_truth_composed"
    assert result.meta["info_sections"] == ["hours", "location", "promotions"]
    assert result.meta["fact_requested_refs"] == ["hours", "location", "promotions"]
    assert result.meta["fact_allowed_refs"] == ["hours", "location", "promotions"]
    assert result.meta["fact_emitted_refs"] == ["hours", "location", "promotions"]
    assert result.meta["fact_composition"]["secondary_tool_action"] == "catalog.service_query"
    assert result.meta["fact_composition"]["secondary_info_sections"] == ["promotions"]


def test_turn_executor_composes_general_hours_location_promotions_and_contact(monkeypatch) -> None:
    calls: list[tuple[str, list[str]]] = []

    def _execute_tool_action(db, **kwargs):
        calls.append((kwargs["tool_action"], list(kwargs.get("allowed_fact_refs") or [])))
        if kwargs["tool_action"] == "catalog.location":
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Работаем ежедневно, без выходных, с 9:00 до 21:00. Адрес: Абая 10. Instagram: https://instagram.com/mira_beauty_kz.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.location",
                    "tool_decision": "ok",
                    "info_sections": ["hours", "location", "contact"],
                },
                trace={"stage": "tool_registry", "decision": "ok"},
            )
        if kwargs["tool_action"] == "catalog.service_query":
            assert not kwargs.get("service_query")
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Официальные акции: Первое посещение: 10% (на услуги).",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "promotions",
                    "info_sections": ["promotions"],
                },
                trace={"stage": "tool_registry", "decision": "promotions"},
            )
        raise AssertionError(f"unexpected tool action: {kwargs['tool_action']}")

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "location",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": ["hours", "location", "promotions", "contact"],
            "fact_refs": ["hours", "location", "promotions", "contact"],
            "reason": "user_requests combined hours+promotions+location+contact facts",
            "goal": "info",
            "capability": "location",
            "subject_kind": "general",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="general_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Вы сегодня работаете, есть акции, где находитесь и как с вами связаться?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == [
        ("catalog.location", ["hours", "location", "promotions", "contact"]),
        ("catalog.service_query", ["promotions"]),
    ]
    assert "Работаем ежедневно" in result.text
    assert "Instagram" in result.text
    assert "Официальные акции" in result.text
    assert result.tool_action == "catalog.location"
    assert result.tool_decision == "multi_truth_composed"
    assert result.meta["info_sections"] == ["hours", "location", "promotions", "contact"]
    assert result.meta["fact_requested_refs"] == ["hours", "location", "promotions", "contact"]
    assert result.meta["fact_allowed_refs"] == ["hours", "location", "promotions", "contact"]
    assert result.meta["fact_emitted_refs"] == ["hours", "location", "promotions", "contact"]
    assert result.meta["fact_composition"]["secondary_tool_action"] == "catalog.service_query"
    assert result.meta["fact_composition"]["secondary_info_sections"] == ["promotions"]


def test_turn_executor_composes_mixed_first_turn_location_and_services_overview(monkeypatch) -> None:
    calls: list[tuple[str, list[str]]] = []

    def _execute_tool_action(db, **kwargs):
        calls.append((kwargs["tool_action"], list(kwargs.get("allowed_fact_refs") or [])))
        if kwargs["tool_action"] == "catalog.location":
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Мы находимся по адресу: Абая 10.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.location",
                    "tool_decision": "location",
                    "info_sections": ["location"],
                },
                trace={"stage": "tool_registry", "decision": "location"},
            )
        if kwargs["tool_action"] == "catalog.service_query":
            assert kwargs["service_query"] is None
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Доступны маникюр, педикюр и стрижки.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "services_overview",
                    "info_sections": ["services_overview"],
                },
                trace={"stage": "tool_registry", "decision": "services_overview"},
            )
        raise AssertionError(f"unexpected tool action: {kwargs['tool_action']}")

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "location",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": ["location", "services_overview"],
            "fact_refs": ["location", "services_overview"],
            "reason": "user_asks_services_and_address",
            "goal": "info",
            "capability": "location",
            "subject_kind": "general",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Какие услуги у вас есть и адрес, пожалуйста.",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == [
        ("catalog.location", ["location", "services_overview"]),
        ("catalog.service_query", ["services_overview"]),
    ]
    assert result.text == "Мы находимся по адресу: Абая 10.\n\nДоступны маникюр, педикюр и стрижки."
    assert result.tool_decision == "multi_truth_composed"
    assert result.meta["info_sections"] == ["location", "services_overview"]
    assert result.meta["fact_allowed_refs"] == ["location", "services_overview"]
    assert result.meta["fact_emitted_refs"] == ["location", "services_overview"]


def test_turn_executor_composes_mixed_first_turn_location_pricing_and_duration(monkeypatch) -> None:
    calls: list[tuple[str, list[str]]] = []

    def _execute_tool_action(db, **kwargs):
        calls.append((kwargs["tool_action"], list(kwargs.get("allowed_fact_refs") or [])))
        if kwargs["tool_action"] == "catalog.location":
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Адрес: Абая 150.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.location",
                    "tool_decision": "location",
                    "info_sections": ["location"],
                },
                trace={"stage": "tool_registry", "decision": "location"},
            )
        if kwargs["tool_action"] == "catalog.service_query" and kwargs.get("allowed_fact_refs") == ["pricing"]:
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Маникюр классический — 2 500 ₸.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "pricing",
                    "info_sections": ["pricing"],
                },
                trace={"stage": "tool_registry", "decision": "pricing"},
            )
        if kwargs["tool_action"] == "catalog.service_query" and kwargs.get("allowed_fact_refs") == ["duration"]:
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Маникюр обычно длится 40–60 минут.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "duration",
                    "info_sections": ["duration"],
                },
                trace={"stage": "tool_registry", "decision": "duration"},
            )
        raise AssertionError(f"unexpected tool action: {kwargs['tool_action']} / {kwargs.get('allowed_fact_refs')}")

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "location",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": ["location", "pricing", "duration"],
            "fact_refs": ["location", "pricing", "duration"],
            "reason": "user_asks_location_price_and_duration_for_manicure",
            "goal": "info",
            "capability": "location",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Сколько стоит маникюр, сколько длится и где находитесь?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == [
        ("catalog.location", ["location", "pricing", "duration"]),
        ("catalog.service_query", ["pricing"]),
        ("catalog.service_query", ["duration"]),
    ]
    assert result.text == (
        "Адрес: Абая 150.\n\nМаникюр классический — 2 500 ₸.\n\nМаникюр обычно длится 40–60 минут."
    )
    assert result.tool_decision == "multi_truth_composed"
    assert result.meta["info_sections"] == ["location", "pricing", "duration"]
    assert result.meta["fact_allowed_refs"] == ["location", "pricing", "duration"]
    assert result.meta["fact_emitted_refs"] == ["location", "pricing", "duration"]
    assert result.meta["fact_composition"]["secondary_tool_action"] == "catalog.service_query"
    assert result.meta["fact_composition"]["secondary_info_sections"] == ["pricing", "duration"]
    assert result.meta["fact_composition"]["secondary_tool_decision"] == "multi_step"


def test_turn_executor_composes_mixed_first_turn_location_pricing_and_parking(monkeypatch) -> None:
    calls: list[tuple[str, list[str]]] = []

    def _execute_tool_action(db, **kwargs):
        calls.append((kwargs["tool_action"], list(kwargs.get("allowed_fact_refs") or [])))
        if kwargs["tool_action"] == "catalog.location":
            assert kwargs.get("allowed_fact_refs") == ["location", "pricing", "parking"]
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Адрес: Абая 150.\n\nБесплатная парковка во дворе.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.location",
                    "tool_decision": "ok",
                    "info_sections": ["location", "parking"],
                },
                trace={"stage": "tool_registry", "decision": "ok"},
            )
        if kwargs["tool_action"] == "catalog.service_query" and kwargs.get("allowed_fact_refs") == ["pricing"]:
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Маникюр классический — 2 500 ₸.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "pricing",
                    "info_sections": ["pricing"],
                },
                trace={"stage": "tool_registry", "decision": "pricing"},
            )
        raise AssertionError(f"unexpected tool action: {kwargs['tool_action']} / {kwargs.get('allowed_fact_refs')}")

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "location",
            "action": "fact",
            "tool_action": "catalog.location",
            "pack_refs": ["location", "pricing", "parking"],
            "fact_refs": ["location", "pricing", "parking"],
            "reason": "user_asked_location_price_parking_for_grounded_service",
            "goal": "info",
            "capability": "location",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Где вы находитесь, сколько стоит маникюр и есть парковка?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == [
        ("catalog.location", ["location", "pricing", "parking"]),
        ("catalog.service_query", ["pricing"]),
    ]
    assert result.text == (
        "Адрес: Абая 150.\n\nБесплатная парковка во дворе.\n\nМаникюр классический — 2 500 ₸."
    )
    assert result.tool_decision == "multi_truth_composed"
    assert result.meta["info_sections"] == ["location", "pricing", "parking"]
    assert result.meta["fact_requested_refs"] == ["location", "pricing", "parking"]
    assert result.meta["fact_allowed_refs"] == ["location", "pricing", "parking"]
    assert result.meta["fact_emitted_refs"] == ["location", "pricing", "parking"]
    assert result.meta["fact_composition"]["secondary_tool_action"] == "catalog.service_query"
    assert result.meta["fact_composition"]["secondary_info_sections"] == ["pricing"]


def test_turn_executor_composes_mixed_first_turn_location_pricing_and_contact(monkeypatch) -> None:
    calls: list[tuple[str, list[str]]] = []

    def _execute_tool_action(db, **kwargs):
        calls.append((kwargs["tool_action"], list(kwargs.get("allowed_fact_refs") or [])))
        if kwargs["tool_action"] == "catalog.location":
            assert kwargs.get("allowed_fact_refs") == ["location", "pricing", "contact"]
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Адрес: Абая 150.\n\nWhatsApp: +7 700 000 00 00.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.location",
                    "tool_decision": "ok",
                    "info_sections": ["location", "contact"],
                },
                trace={"stage": "tool_registry", "decision": "ok"},
            )
        if kwargs["tool_action"] == "catalog.service_query" and kwargs.get("allowed_fact_refs") == ["pricing"]:
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Маникюр классический — 2 500 ₸.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "pricing",
                    "info_sections": ["pricing"],
                },
                trace={"stage": "tool_registry", "decision": "pricing"},
            )
        raise AssertionError(f"unexpected tool action: {kwargs['tool_action']} / {kwargs.get('allowed_fact_refs')}")

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "location",
            "action": "fact",
            "tool_action": "catalog.location",
            "pack_refs": ["location", "pricing", "contact"],
            "fact_refs": ["location", "pricing", "contact"],
            "reason": "user_asked_location_price_contact_for_grounded_service",
            "goal": "info",
            "capability": "location",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Где вы находитесь, сколько стоит маникюр и как с вами связаться?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == [
        ("catalog.location", ["location", "pricing", "contact"]),
        ("catalog.service_query", ["pricing"]),
    ]
    assert result.text == (
        "Адрес: Абая 150.\n\nWhatsApp: +7 700 000 00 00.\n\nМаникюр классический — 2 500 ₸."
    )
    assert result.tool_decision == "multi_truth_composed"
    assert result.meta["info_sections"] == ["location", "pricing", "contact"]
    assert result.meta["fact_requested_refs"] == ["location", "pricing", "contact"]
    assert result.meta["fact_allowed_refs"] == ["location", "pricing", "contact"]
    assert result.meta["fact_emitted_refs"] == ["location", "pricing", "contact"]
    assert result.meta["fact_composition"]["secondary_tool_action"] == "catalog.service_query"
    assert result.meta["fact_composition"]["secondary_info_sections"] == ["pricing"]


def test_turn_executor_composes_mixed_first_turn_location_pricing_master_and_contact(monkeypatch) -> None:
    calls: list[tuple[str, list[str]]] = []
    truth = {
        "services_catalog": {
            "services": [
                {
                    "name": "Маникюр",
                    "aliases": ["маникюр"],
                    "price_items": ["Маникюр классический"],
                    "duration_text": "Обычно 45–90 минут.",
                }
            ],
            "duration_clarify": "По времени зависит от услуги. Какая именно?",
        },
        "price_list": [
            {
                "category": "Маникюр",
                "items": [{"name": "Маникюр классический", "price": 2500}],
            }
        ],
        "team": {
            "nails": "Нейл-мастера 5+ лет, работают с классическим и аппаратным маникюром."
        },
        "masters_catalog": {
            "specialists": [
                {
                    "name": "Алия",
                    "services": ["Маникюр"],
                    "experience": "5+ лет",
                    "highlight": "классический маникюр",
                }
            ]
        },
    }

    def _execute_tool_action(db, **kwargs):
        calls.append((kwargs["tool_action"], list(kwargs.get("allowed_fact_refs") or [])))
        if kwargs["tool_action"] == "catalog.location":
            assert kwargs.get("allowed_fact_refs") == ["location", "pricing", "master", "contact"]
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Адрес: Абая 150.\n\nWhatsApp: +7 700 000 00 00.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.location",
                    "tool_decision": "ok",
                    "info_sections": ["location", "contact"],
                },
                trace={"stage": "tool_registry", "decision": "ok"},
            )
        if kwargs["tool_action"] == "catalog.service_query" and kwargs.get("allowed_fact_refs") == ["pricing"]:
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Маникюр классический — 2 500 ₸.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "pricing",
                    "info_sections": ["pricing"],
                },
                trace={"stage": "tool_registry", "decision": "pricing"},
            )
        raise AssertionError(f"unexpected tool action: {kwargs['tool_action']} / {kwargs.get('allowed_fact_refs')}")

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "location",
            "action": "fact",
            "tool_action": "catalog.location",
            "pack_refs": ["location", "pricing", "master", "contact"],
            "fact_refs": ["location", "pricing", "master", "contact"],
            "reason": "user_asked_location_price_master_contact_for_grounded_service",
            "goal": "info",
            "capability": "location",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    with use_runtime_truth_override(_runtime_truth_payload(truth)):
        result = TurnExecutor().execute(
            decision,
            db=object(),
            message_text="Где вы находитесь, сколько стоит маникюр, кто делает маникюр и как с вами связаться?",
            client_slug="demo_salon",
            branch_id=uuid4(),
            booking_state=None,
            user_name=None,
            user_phone=None,
            now=datetime.now(timezone.utc),
        )

    assert calls == [
        ("catalog.location", ["location", "pricing", "master", "contact"]),
        ("catalog.service_query", ["pricing"]),
    ]
    assert "Адрес: Абая 150." in result.text
    assert "WhatsApp: +7 700 000 00 00." in result.text
    assert "Маникюр классический — 2 500 ₸." in result.text
    assert "Алия" in result.text
    assert result.tool_decision == "multi_truth_composed"
    assert result.meta["info_sections"] == ["location", "pricing", "master", "contact"]
    assert result.meta["fact_requested_refs"] == ["location", "pricing", "master", "contact"]
    assert result.meta["fact_allowed_refs"] == ["location", "pricing", "master", "contact"]
    assert result.meta["fact_emitted_refs"] == ["location", "pricing", "master", "contact"]
    assert result.meta["fact_composition"]["secondary_tool_action"] == "catalog.service_query"
    assert result.meta["fact_composition"]["secondary_info_sections"] == ["pricing", "master"]


def test_turn_executor_composes_promotions_master_and_contact(monkeypatch) -> None:
    calls: list[tuple[str, list[str]]] = []
    truth = {
        "services_catalog": {
            "services": [
                {
                    "name": "Маникюр",
                    "aliases": ["маникюр"],
                    "price_items": ["Маникюр классический"],
                    "duration_text": "Обычно 45–90 минут.",
                }
            ],
        },
        "promotions": {
            "items": [
                {
                    "title": "Скидка 10% на маникюр по будням",
                    "description": "Действует по будням до 16:00.",
                }
            ]
        },
        "team": {
            "nails": "Нейл-мастера 5+ лет, работают с классическим и аппаратным маникюром."
        },
        "masters_catalog": {
            "specialists": [
                {
                    "name": "Алия",
                    "services": ["Маникюр"],
                    "experience": "5+ лет",
                    "highlight": "классический маникюр",
                }
            ]
        },
    }

    def _execute_tool_action(db, **kwargs):
        calls.append((kwargs["tool_action"], list(kwargs.get("allowed_fact_refs") or [])))
        if kwargs["tool_action"] == "catalog.service_query" and kwargs.get("allowed_fact_refs") == ["promotions"]:
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Скидка 10% на маникюр по будням до 16:00.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "promotions",
                    "info_sections": ["promotions"],
                },
                trace={"stage": "tool_registry", "decision": "promotions"},
            )
        if kwargs["tool_action"] == "catalog.location" and kwargs.get("allowed_fact_refs") == ["contact"]:
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Телефон в карточке салона не указан. Instagram: https://instagram.com/mira_beauty_kz.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.location",
                    "tool_decision": "ok",
                    "info_sections": ["contact"],
                },
                trace={"stage": "tool_registry", "decision": "ok"},
            )
        raise AssertionError(
            f"unexpected tool action: {kwargs['tool_action']} / {kwargs.get('allowed_fact_refs')}"
        )

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "promotions",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "pack_refs": ["promotions", "master", "contact"],
            "fact_refs": ["promotions", "master", "contact"],
            "reason": "user_asked_promotions_master_contact_for_grounded_service",
            "goal": "info",
            "capability": "promotions",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    with use_runtime_truth_override(_runtime_truth_payload(truth)):
        result = TurnExecutor().execute(
            decision,
            db=object(),
            message_text="Есть акции на маникюр, кто делает маникюр и как с вами связаться?",
            client_slug="demo_salon",
            branch_id=uuid4(),
            booking_state=None,
            user_name=None,
            user_phone=None,
            now=datetime.now(timezone.utc),
        )

    assert calls == [
        ("catalog.service_query", ["promotions"]),
        ("catalog.location", ["contact"]),
    ]
    assert "Скидка 10% на маникюр по будням до 16:00." in result.text
    assert "Алия" in result.text
    assert "Instagram" in result.text
    assert result.tool_decision == "multi_truth_composed"
    assert result.meta["info_sections"] == ["promotions", "master", "contact"]
    assert result.meta["fact_requested_refs"] == ["promotions", "master", "contact"]
    assert result.meta["fact_allowed_refs"] == ["promotions", "master", "contact"]
    assert result.meta["fact_emitted_refs"] == ["promotions", "master", "contact"]
    assert result.meta["fact_composition"]["primary_tool_action"] == "catalog.service_query"
    assert result.meta["fact_composition"]["secondary_tool_action"] == "multi_tool"
    assert result.meta["fact_composition"]["secondary_info_sections"] == ["master", "contact"]


def test_turn_executor_composes_mixed_first_turn_location_pricing_and_services_overview(monkeypatch) -> None:
    calls: list[tuple[str, list[str], str | None]] = []

    def _execute_tool_action(db, **kwargs):
        calls.append(
            (
                kwargs["tool_action"],
                list(kwargs.get("allowed_fact_refs") or []),
                kwargs.get("service_query"),
            )
        )
        if kwargs["tool_action"] == "catalog.location":
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Адрес: Абая 150.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.location",
                    "tool_decision": "location",
                    "info_sections": ["location"],
                },
                trace={"stage": "tool_registry", "decision": "location"},
            )
        if kwargs["tool_action"] == "catalog.service_query" and kwargs.get("allowed_fact_refs") == ["pricing"]:
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Маникюр классический — 2 500 ₸.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "pricing",
                    "info_sections": ["pricing"],
                },
                trace={"stage": "tool_registry", "decision": "pricing"},
            )
        if kwargs["tool_action"] == "catalog.service_query" and kwargs.get("allowed_fact_refs") == ["services_overview"]:
            assert kwargs["service_query"] is None
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Мы салон красоты: маникюр, педикюр и стрижки.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "services_overview",
                    "info_sections": ["services_overview"],
                },
                trace={"stage": "tool_registry", "decision": "services_overview"},
            )
        raise AssertionError(f"unexpected tool action: {kwargs['tool_action']} / {kwargs.get('allowed_fact_refs')}")

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "location",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": ["location", "pricing", "services_overview"],
            "fact_refs": ["location", "pricing", "services_overview"],
            "reason": "user_asks_services_pricing_and_location_for_manicure",
            "goal": "info",
            "capability": "location",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Какие услуги у вас есть и сколько стоит маникюр и где находитесь?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == [
        ("catalog.location", ["location", "pricing", "services_overview"], "маникюр"),
        ("catalog.service_query", ["pricing"], "маникюр"),
        ("catalog.service_query", ["services_overview"], None),
    ]
    assert result.text == (
        "Адрес: Абая 150.\n\nМаникюр классический — 2 500 ₸.\n\nМы салон красоты: маникюр, педикюр и стрижки."
    )
    assert result.tool_decision == "multi_truth_composed"
    assert result.meta["info_sections"] == ["location", "pricing", "services_overview"]
    assert result.meta["fact_allowed_refs"] == ["location", "pricing", "services_overview"]
    assert result.meta["fact_emitted_refs"] == ["location", "pricing", "services_overview"]
    assert result.meta["fact_composition"]["secondary_info_sections"] == ["pricing", "services_overview"]
    assert result.meta["fact_composition"]["secondary_tool_decision"] == "multi_step"


def test_turn_executor_composes_service_query_multifact_pricing_and_duration(monkeypatch) -> None:
    calls: list[tuple[str, list[str]]] = []

    def _execute_tool_action(db, **kwargs):
        calls.append((kwargs["tool_action"], list(kwargs.get("allowed_fact_refs") or [])))
        if kwargs["tool_action"] != "catalog.service_query":
            raise AssertionError(f"unexpected tool action: {kwargs['tool_action']}")
        if kwargs.get("allowed_fact_refs") == ["pricing"]:
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Маникюр классический — 2 500 ₸.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "pricing",
                    "info_sections": ["pricing"],
                },
                trace={"stage": "tool_registry", "decision": "pricing"},
            )
        if kwargs.get("allowed_fact_refs") == ["duration"]:
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Маникюр обычно длится 40–60 минут.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "duration",
                    "info_sections": ["duration"],
                },
                trace={"stage": "tool_registry", "decision": "duration"},
            )
        raise AssertionError(f"unexpected allowed refs: {kwargs.get('allowed_fact_refs')}")

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "pricing",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "pack_refs": ["pricing", "duration"],
            "fact_refs": ["pricing", "duration"],
            "reason": "user asks pricing and duration for grounded service маникюр",
            "goal": "info",
            "capability": "pricing",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Сколько стоит маникюр и сколько длится маникюр?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == [
        ("catalog.service_query", ["pricing"]),
        ("catalog.service_query", ["duration"]),
    ]
    assert result.text == (
        "Маникюр классический — 2 500 ₸.\n\nМаникюр обычно длится 40–60 минут."
    )
    assert result.tool_action == "catalog.service_query"
    assert result.tool_decision == "multi_truth_composed"
    assert result.meta["info_sections"] == ["pricing", "duration"]
    assert result.meta["fact_allowed_refs"] == ["pricing", "duration"]
    assert result.meta["fact_emitted_refs"] == ["pricing", "duration"]
    assert result.meta["fact_composition"]["composition_scope"] == "service_query_multi_fact"
    assert result.meta["fact_composition"]["secondary_info_sections"] == ["duration"]


def test_turn_executor_composes_service_query_multifact_pricing_and_services_overview(monkeypatch) -> None:
    calls: list[tuple[str, list[str], str | None]] = []

    def _execute_tool_action(db, **kwargs):
        calls.append(
            (
                kwargs["tool_action"],
                list(kwargs.get("allowed_fact_refs") or []),
                kwargs.get("service_query"),
            )
        )
        if kwargs["tool_action"] != "catalog.service_query":
            raise AssertionError(f"unexpected tool action: {kwargs['tool_action']}")
        if kwargs.get("allowed_fact_refs") == ["pricing"]:
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Маникюр классический — 2 500 ₸.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "pricing",
                    "info_sections": ["pricing"],
                },
                trace={"stage": "tool_registry", "decision": "pricing"},
            )
        if kwargs.get("allowed_fact_refs") == ["services_overview"]:
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Мы салон красоты: маникюр, педикюр, стрижки и брови.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "services_overview",
                    "info_sections": ["services_overview"],
                },
                trace={"stage": "tool_registry", "decision": "services_overview"},
            )
        raise AssertionError(f"unexpected allowed refs: {kwargs.get('allowed_fact_refs')}")

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "pricing",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "pack_refs": ["pricing", "services_overview"],
            "fact_refs": ["pricing", "services_overview"],
            "reason": "user asks what services are available and the price of manicure",
            "goal": "info",
            "capability": "pricing",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Какие услуги у вас есть и сколько стоит маникюр?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == [
        ("catalog.service_query", ["pricing"], "маникюр"),
        ("catalog.service_query", ["services_overview"], None),
    ]
    assert result.text == (
        "Маникюр классический — 2 500 ₸.\n\nМы салон красоты: маникюр, педикюр, стрижки и брови."
    )
    assert result.tool_action == "catalog.service_query"
    assert result.tool_decision == "multi_truth_composed"
    assert result.meta["info_sections"] == ["pricing", "services_overview"]
    assert result.meta["fact_allowed_refs"] == ["pricing", "services_overview"]
    assert result.meta["fact_emitted_refs"] == ["pricing", "services_overview"]
    assert result.meta["fact_composition"]["composition_scope"] == "service_query_multi_fact"
    assert result.meta["fact_composition"]["secondary_info_sections"] == ["services_overview"]


def test_turn_executor_composes_service_query_head_pricing_and_contact(monkeypatch) -> None:
    calls: list[tuple[str, list[str], str | None]] = []

    def _execute_tool_action(db, **kwargs):
        calls.append(
            (
                kwargs["tool_action"],
                list(kwargs.get("allowed_fact_refs") or []),
                kwargs.get("service_query"),
            )
        )
        if kwargs["tool_action"] == "catalog.service_query" and kwargs.get("allowed_fact_refs") == ["pricing"]:
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Маникюр классический — 2 500 ₸.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "pricing",
                    "info_sections": ["pricing"],
                },
                trace={"stage": "tool_registry", "decision": "pricing"},
            )
        if kwargs["tool_action"] == "catalog.location" and kwargs.get("allowed_fact_refs") == ["contact"]:
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Телефон не указан. Instagram: https://instagram.com/mira_beauty_kz.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.location",
                    "tool_decision": "ok",
                    "info_sections": ["contact"],
                },
                trace={"stage": "tool_registry", "decision": "ok"},
            )
        raise AssertionError(f"unexpected tool call: {kwargs['tool_action']} / {kwargs.get('allowed_fact_refs')}")

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
    )

    decision = build_test_policy_override_decision(
        {
            "intent": "pricing",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "pack_refs": ["pricing", "contact"],
            "fact_refs": ["pricing", "contact"],
            "reason": "user asks pricing for grounded service and contact details",
            "goal": "info",
            "capability": "pricing",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Сколько стоит маникюр и как с вами связаться?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == [
        ("catalog.service_query", ["pricing"], "маникюр"),
        ("catalog.location", ["contact"], None),
    ]
    assert result.text == (
        "Маникюр классический — 2 500 ₸.\n\n"
        "Телефон не указан. Instagram: https://instagram.com/mira_beauty_kz."
    )
    assert result.tool_action == "catalog.service_query"
    assert result.tool_decision == "multi_truth_composed"
    assert result.meta["info_sections"] == ["pricing", "contact"]
    assert result.meta["fact_allowed_refs"] == ["pricing", "contact"]
    assert result.meta["fact_emitted_refs"] == ["pricing", "contact"]
    assert result.meta["fact_composition"]["composition_scope"] == "service_query_cross_tool_fact"
    assert result.meta["fact_composition"]["secondary_tool_action"] == "catalog.location"
    assert result.meta["fact_composition"]["secondary_info_sections"] == ["contact"]


def test_turn_executor_mixed_first_turn_promotions_still_do_not_compose(monkeypatch) -> None:
    calls: list[str] = []

    def _execute_tool_action(db, **kwargs):
        calls.append(kwargs["tool_action"])
        if kwargs["tool_action"] == "catalog.location":
            return SimpleNamespace(
                handled=True,
                ok=True,
                response_text="Парковка есть.",
                error_code=None,
                decision_meta={
                    "tool_action": "catalog.location",
                    "tool_decision": "parking",
                    "info_sections": ["parking"],
                },
                trace={"stage": "tool_registry", "decision": "parking"},
            )
        if kwargs["tool_action"] == "catalog.service_query":
            return SimpleNamespace(
                handled=True,
                ok=False,
                response_text=None,
                error_code="not_found",
                decision_meta={
                    "tool_action": "catalog.service_query",
                    "tool_decision": "not_found",
                    "info_sections": [],
                },
                trace={"stage": "tool_registry", "decision": "not_found"},
            )
        raise AssertionError(f"unexpected tool action: {kwargs['tool_action']}")

    monkeypatch.setattr(
        "app.services.tool_registry_service.execute_tool_action",
        _execute_tool_action,
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
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert calls == ["catalog.location", "catalog.service_query"]
    assert result.text == "Я уточню это для вас."
    assert result.tool_decision == "fact_family_unresolved"
    assert result.meta["fact_fallback_reason"] == "first_fact_family_mixed_scope_unresolved"


def test_turn_executor_appends_service_followup_for_promotions_booking_fact(monkeypatch) -> None:
    def _execute_tool_action(db, **kwargs):
        assert kwargs["tool_action"] == "catalog.service_query"
        assert kwargs["expected_reply_type"] == "service_choice"
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Официальные акции: Первое посещение: 10%.",
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
            "intent": "promotions",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "pack_refs": ["promotions"],
            "fact_refs": ["promotions"],
            "reason": "standalone_promotions_head_with_missing_service_booking_request",
            "goal": "booking",
            "capability": "promotions",
            "subject_kind": "general",
            "resolution_mode": "policy_fact",
            "expected_reply_type": "service_choice",
            "next_question": "service",
            "open_questions": ["service"],
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Есть скидки, хочу записаться.",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.text == (
        "Официальные акции: Первое посещение: 10%.\n\n"
        "На какую услугу хотите записаться?"
    )
    assert result.tool_action == "catalog.service_query"
    assert result.tool_decision == "promotions"
    assert result.meta["info_sections"] == ["promotions"]


def test_turn_executor_appends_datetime_followup_for_promotions_grounded_service_booking_fact(
    monkeypatch,
) -> None:
    def _execute_tool_action(db, **kwargs):
        assert kwargs["tool_action"] == "catalog.service_query"
        assert kwargs["expected_reply_type"] == "time"
        assert kwargs["service_query"] == "маникюр"
        return SimpleNamespace(
            handled=True,
            ok=True,
            response_text="Официальные акции: Первое посещение: 10%.",
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
            "intent": "promotions",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "pack_refs": ["promotions"],
            "fact_refs": ["promotions"],
            "slots": {"service": "маникюр"},
            "referents": {
                "service": {
                    "value": "маникюр",
                    "entity_type": "service",
                    "source_ref": "user_text",
                }
            },
            "reason": "standalone_promotions_head_with_grounded_service_booking_request",
            "goal": "booking",
            "capability": "promotions",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
            "expected_reply_type": "time",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Есть акции на маникюр, хочу записаться.",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.text == (
        "Официальные акции: Первое посещение: 10%.\n\n"
        "На какую дату и время вам удобно?"
    )
    assert result.tool_action == "catalog.service_query"
    assert result.tool_decision == "promotions"
    assert result.meta["info_sections"] == ["promotions"]


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


def test_tool_registry_catalog_location_preserves_allowed_fact_ref_order(monkeypatch) -> None:
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
        info_sections_hint=["hours", "location"],
        message_text="Вы сегодня работаете и где находитесь?",
        expected_reply_type=None,
        now=datetime.now(timezone.utc),
        allowed_fact_refs=["hours", "location"],
    )

    assert result.handled is True
    assert result.ok is True
    assert result.decision_meta.get("info_sections") == ["hours", "location"]
    assert result.response_text.startswith("Работаем ")


def test_tool_registry_catalog_location_renders_contact_location_exact_scope(monkeypatch) -> None:
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
        info_sections_hint=["contact", "location"],
        message_text="Какой у вас телефон и адрес?",
        expected_reply_type=None,
        now=datetime.now(timezone.utc),
        allowed_fact_refs=["contact", "location"],
    )

    assert result.handled is True
    assert result.ok is True
    assert result.decision_meta.get("info_sections") == ["contact", "location"]
    assert "Instagram:" in result.response_text
    assert "Адрес:" in result.response_text


def test_turn_executor_contact_only_catalog_location_uses_exact_pack_ref() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "location",
            "action": "fact",
            "tool_action": "catalog.location",
            "pack_refs": ["contact"],
            "reason": "user_requests_contact_details",
            "goal": "info",
            "capability": "location",
            "subject_kind": "general",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Как с вами связаться?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state=None,
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.tool_action == "catalog.location"
    assert result.tool_decision == "ok"
    assert result.meta["fact_requested_refs"] == ["contact"]
    assert result.meta["fact_allowed_refs"] == ["contact"]
    assert result.meta["fact_emitted_refs"] == ["contact"]
    assert result.meta["info_sections"] == ["contact"]
    assert "Instagram:" in result.text
    assert "Адрес:" not in result.text


def test_turn_executor_prefers_explicit_parking_ref_over_coarse_location_family_alias() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "location",
            "action": "fact",
            "tool_action": "catalog.location",
            "pack_refs": ["parking"],
            "reason": "parking_info_interrupt_booking_time_collect",
            "goal": "booking",
            "capability": "bookability",
            "subject_kind": "service",
            "resolution_mode": "direct",
        },
        interaction_owner="llm_policy_core",
        interaction_relation="generic_info_interrupt",
        source="llm_policy_core",
    )

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Есть ли парковка рядом?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.tool_action == "catalog.location"
    assert result.tool_decision == "ok"
    assert result.meta["fact_requested_refs"] == ["parking"]
    assert result.meta["fact_allowed_refs"] == ["parking"]
    assert result.meta["fact_allowed_sets"] == [["parking"]]
    assert result.meta["fact_emitted_refs"] == ["parking"]
    assert result.meta["info_sections"] == ["parking"]
    assert "Адрес:" not in result.text


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
        lambda self, decision, *, booking_state, prior_booking_state=None: SimpleNamespace(
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
    decision = _build_binding_only_boundary_decision(
        binding_plan=BindingPlanV1.build_degrade(
            decision_id="boundary-degrade-stale-outcome",
            degrade_reason_code="planner_timeout",
        ),
        outcome="FACT",
        action="fact",
        intent="planner_timeout",
        tool_action="handoff",
        reason_code="planner_timeout",
    )

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
        "app.services.pack_runtime_compat.get_pack_decision",
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
        "app.services.pack_runtime_compat.get_pack_decision",
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


def test_turn_executor_routes_owner_backed_promotions_interrupt_through_catalog_tool_registry(
    monkeypatch,
) -> None:
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
        "app.services.pack_runtime_compat.get_pack_decision",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("raw pack fallback should not run")),
    )

    decision = _owner_backed_promotions_interrupt_decision()

    result = TurnExecutor().execute(
        decision,
        db=object(),
        message_text="Какие у вас акции на маникюр?",
        client_slug="demo_salon",
        branch_id=uuid4(),
        booking_state={"service": "маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert captured["tool_action"] == "catalog.service_query"
    assert captured["service_query"] == "маникюр"
    assert captured["info_sections_hint"] == ["promotions"]
    assert captured["allowed_fact_refs"] == ["promotions"]
    assert result.tool_action == "catalog.service_query"
    assert result.tool_decision == "promotions"
    assert "10%" in result.text
    assert result.meta["fact_requested_refs"] == ["promotions"]
    assert result.meta["fact_allowed_refs"] == ["promotions"]
    assert result.meta["fact_allowed_sets"] == [["promotions"]]
    assert result.meta["fact_emitted_refs"] == ["promotions"]
    assert result.meta["fact_contract"]["request"]["intent"] == "pricing"


def test_turn_executor_accepts_owner_backed_promotions_direct_truth_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.pack_runtime_compat.get_pack_decision",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("raw pack fallback should not run")),
    )

    decision = _owner_backed_promotions_interrupt_decision()

    result = TurnExecutor().execute(
        decision,
        db=None,
        message_text="Какие у вас акции на маникюр?",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.tool_action == "catalog.service_query"
    assert result.tool_decision == "promotions"
    assert "10%" in result.text
    assert result.meta.get("info_sections") == ["promotions"]
    assert result.meta.get("info_ref_execution") is True
    assert result.meta.get("info_ref_source") == "policy_core"
    assert result.meta["fact_requested_refs"] == ["promotions"]
    assert result.meta["fact_allowed_refs"] == ["promotions"]
    assert result.meta["fact_allowed_sets"] == [["promotions"]]
    assert result.meta["fact_emitted_refs"] == ["promotions"]
    assert result.meta.get("fact_fallback") is None
    assert result.meta["fact_contract"]["request"]["intent"] == "pricing"


def test_turn_executor_no_longer_fans_out_logical_info_tool_candidates(monkeypatch) -> None:
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
        "app.services.pack_runtime_compat.get_pack_decision",
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

    assert captured == []
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


def test_tool_registry_catalog_service_query_keeps_grounded_price_item_duration_exactness(monkeypatch) -> None:
    from app.services import tool_registry_service

    truth = {
        "services_catalog": {
            "services": [
                {
                    "name": "Стрижка",
                    "aliases": ["стрижка"],
                    "duration_text": "Обычно 20–60 минут.",
                }
            ],
            "duration_clarify": "По времени зависит от услуги. Какая именно?",
        },
        "price_list": [
            {
                "category": "Парикмахерский зал",
                "items": [{"name": "Укладка феном", "price": 3500}],
            }
        ],
        "team": {
            "hair": "Колористы 5+ лет, делают блонд, балаяж и другие сложные окрашивания."
        },
    }
    branch = SimpleNamespace(id=uuid4(), booking_settings={})
    monkeypatch.setattr(tool_registry_service, "_resolve_branch", lambda db, branch_id: branch)

    with use_runtime_truth_override(_runtime_truth_payload(truth)):
        result = tool_registry_service.execute_tool_action(
            db=None,
            tool_action="catalog.service_query",
            tool_args={"service_query": "укладка"},
            conversation_id=None,
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query="укладка",
            info_sections_hint=["duration"],
            allowed_fact_refs=["duration"],
            message_text="Сколько времени занимает укладка?",
            expected_reply_type=None,
            now=datetime.now(timezone.utc),
        )

    assert result.handled is True
    assert result.ok is True
    assert result.response_text == "Укладка феном — точная длительность зависит от объема и сложности."
    assert result.decision_meta.get("tool_decision") == "duration"
    assert result.trace.get("decision") == "duration"


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

    def _build_runtime_service_truth_reply(
        service: dict[str, object] | str | None,
        *,
        client_slug: str | None = None,
        truth: dict | None = None,
    ) -> str | None:
        captured["service"] = str(service)
        assert client_slug == "demo_salon"
        return "Маникюр стоит 10000 тг."

    monkeypatch.setattr(
        "app.services.pack_runtime_compat.get_pack_decision",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("raw pack decision fallback should stay disabled")
        ),
    )
    monkeypatch.setattr(
        "app.services.pack_runtime_service.build_runtime_service_truth_reply",
        _build_runtime_service_truth_reply,
    )

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

    assert captured == {}
    assert result.tool_decision == "fact_unresolved"
    assert result.meta["fact_fallback"] is True
    assert result.meta["fact_fallback_reason"] == "fact_execution_unresolved"


def test_turn_executor_pricing_fact_uses_public_pack_runtime_seam_without_adapter_runtime_fallback(
    monkeypatch,
) -> None:
    def _runtime_pack_decision(*_args, **_kwargs):
        raise AssertionError("default adapter fallback should stay unused on the active pricing seam")

    monkeypatch.setattr(
        "app.services.pack_runtime_compat.get_pack_decision",
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

    assert result.tool_decision == "fact_unresolved"
    assert result.meta["fact_fallback"] is True
    assert result.meta["fact_fallback_reason"] == "fact_execution_unresolved"
    assert result.meta["fact_allowed_refs"] == ["pricing"]
    assert result.meta["fact_emitted_refs"] == []


def test_pack_grounding_flows_into_runtime_state_trace_and_meta(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.pack_runtime_compat.get_pack_decision",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("raw pack decision fallback should stay disabled")
        ),
    )
    monkeypatch.setattr(
        "app.services.pack_runtime_service.build_runtime_service_truth_reply",
        lambda *args, **kwargs: "Маникюр стоит 10000 тг.",
    )

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
        booking_state={"service": "Маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime.now(timezone.utc),
    )

    assert result.tool_decision == "info_ref_unresolved"
    assert result.meta["fact_fallback"] is True
    assert result.meta["fact_fallback_reason"] == "policy_info_unresolved"
    assert "semantic_contract" not in result.meta

    now = datetime.now(timezone.utc)
    updated, dialog_state, _ = DialogStateService().write_runtime_payload(
        {},
        decision=decision,
        execution_meta=result.meta,
        now=now,
    )
    runtime_payload = updated["consultant_runtime"]
    assert dialog_state.current_referents.service is None
    assert "semantic_contract" not in runtime_payload
    assert dialog_state.meta["semantic_contract"] == {
        "contract_version": "semantic_contract.v1",
        "subject_kind": "service",
        "capability": "pricing",
        "temporal_scope": "none",
        "resolution_mode": "policy_fact",
    }

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
        and entry.get("semantic_contract", {}).get("capability") == "pricing"
        and entry.get("tool_decision") == "info_ref_unresolved"
        for entry in trace
    )
    decision_meta = (user_message.message_metadata or {}).get("decision_meta") or {}
    assert decision_meta["semantic_contract"] == {
        "contract_version": "semantic_contract.v1",
        "subject_kind": "service",
        "capability": "pricing",
        "temporal_scope": "none",
        "resolution_mode": "policy_fact",
    }


def test_turn_executor_does_not_copy_non_owner_semantic_contract_into_execution_meta() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "reason": "question_contract_slot_constraint",
            "goal": "booking",
            "subject_kind": "service",
            "capability": "bookability",
            "temporal_scope": "weekday",
            "resolution_mode": "slot_constraint",
            "expected_reply_type": "time",
            "pending_question_target": "time",
            "active_question_relation": "slot_constraint",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="question_contract",
        interaction_relation="slot_constraint",
        source="question_contract",
    )

    meta = TurnExecutor._attach_semantic_contract_meta(
        decision,
        {"slot_values": {"service": "Маникюр"}},
        semantic_contract=TurnPlanner().canonical_semantic_contract(decision),
        pending_question_contract=TurnExecutor._build_execution_pending_question_contract(decision),
    )

    assert meta["slot_values"] == {"service": "Маникюр"}
    assert "semantic_contract" not in meta
    assert meta["pending_question_contract"] == {
        "expected_reply_type": "time",
        "reason": "question_contract_slot_constraint",
        "pending_question_target": "time",
        "active_question_relation": "slot_constraint",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }


def test_turn_executor_does_not_use_truth_semantic_fallback_when_pack_misses(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.pack_runtime_compat.get_pack_decision",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("raw pack decision fallback should stay disabled")
        ),
    )

    monkeypatch.setattr(
        "app.services.pack_runtime_service.format_reply_from_truth",
        lambda *args, **kwargs: None,
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


def test_consultant_runtime_trace_emits_question_contract_for_fact_interrupt_with_preserved_resume() -> None:
    runtime = ConsultantRuntime()
    decision = build_test_policy_override_decision(
        {
            "intent": "master_query",
            "action": "fact",
            "tool_action": "info",
            "pack_refs": ["master"],
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "goal": "booking",
            "reason": "info_interrupt_preserve_resume_pending_question_contract",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
        },
        interaction_owner="llm_policy_core",
        interaction_relation="generic_info_interrupt",
        source="llm_policy_core",
    )
    dialog_state = DialogState.model_validate(
        {
            "pending_question_contract": {
                "expected_reply_type": "time",
                "reason": "info_interrupt_preserve_resume_pending_question_contract",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "generic_info_interrupt",
                "next_question": "datetime",
                "open_questions": ["datetime"],
            },
            "projections": {
                "expected_reply_type": "time",
                "expected_reply_reason": "info_interrupt_preserve_resume_pending_question_contract",
            },
            "meta": {"current_goal": "booking"},
        }
    )
    conversation = SimpleNamespace(context={}, state="bot_active")
    user_message = SimpleNamespace(message_metadata={})
    execution = SimpleNamespace(tool_action="info", tool_decision="master", meta={})
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
        entry.get("stage") == "pending_question_interaction"
        and entry.get("expected_reply_type") == "time"
        and entry.get("active_question_relation") == "generic_info_interrupt"
        for entry in trace
    )
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("expected_reply_type") == "time"
        and entry.get("active_question_relation") == "generic_info_interrupt"
        and entry.get("pending_question_contract", {}).get("next_question") == "datetime"
        for entry in trace
    )


def test_consultant_runtime_trace_emits_reason_code_for_controlled_degrade() -> None:
    runtime = ConsultantRuntime()
    artifact = TurnExecutor().build_degrade_boundary_artifact_from_request(
        request=DegradeBoundaryRequest(
            reason_code="planner:invalid_schema",
            intent="planner_degrade",
            interaction_owner="turn_planner_degrade",
            public_message="Передаю диалог менеджеру, чтобы не потерять ваш запрос.",
            trace_message="planner_invalid_schema",
            transport_status="skipped",
            transport_reason="planner:invalid_schema",
            override_meta={"control_label": "planner_degrade"},
        )
    )
    conversation = SimpleNamespace(context={}, state="pending")
    user_message = SimpleNamespace(message_metadata={})
    execution = runtime._build_boundary_execution_result(
        boundary_override=artifact.turn_result.boundary_override,
        reply=artifact.turn_result.reply,
    )

    runtime._record_turn_trace(
        conversation=conversation,
        user_message=user_message,
        bot_response=None,
        decision=None,
        execution=execution,
        turn_result=artifact.turn_result,
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
    assert decision_meta.get("intent") == "planner_degrade"
    assert decision_meta.get("control_label") == "planner_degrade"
    assert "semantic_contract" not in decision_meta
    assert "pending_question_contract" not in decision_meta


def test_consultant_runtime_trace_records_policy_core_causal_bundle() -> None:
    runtime = ConsultantRuntime()
    policy_core_trace = {
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
    artifact = TurnExecutor().build_degrade_boundary_artifact_from_request(
        request=DegradeBoundaryRequest(
            reason_code="planner:invalid_schema",
            intent="planner_degrade",
            interaction_owner="turn_planner_degrade",
            public_message="Передаю диалог менеджеру, чтобы не потерять ваш запрос.",
            trace_message="planner_invalid_schema",
            transport_status="skipped",
            transport_reason="planner:invalid_schema",
            override_meta={
                "control_label": "planner_degrade",
                "earliest_failed_stage": "policy_core",
                "root_reason_code": "policy_core:invalid_schema",
                "policy_core_trace": policy_core_trace,
            },
        )
    )
    conversation = SimpleNamespace(context={}, state="pending")
    user_message = SimpleNamespace(message_metadata={})
    execution = runtime._build_boundary_execution_result(
        boundary_override=artifact.turn_result.boundary_override,
        reply=artifact.turn_result.reply,
    )

    runtime._record_turn_trace(
        conversation=conversation,
        user_message=user_message,
        bot_response=None,
        decision=None,
        execution=execution,
        turn_result=artifact.turn_result,
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
        "reason": "collect:datetime",
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


class _MessageQueryStub:
    def __init__(self, messages: list[SimpleNamespace]) -> None:
        self._messages = messages

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def all(self) -> list[SimpleNamespace]:
        return list(self._messages)


class _MessageDbStub:
    def __init__(self, messages: list[SimpleNamespace]) -> None:
        self._messages = messages

    def query(self, _model):
        return _MessageQueryStub(self._messages)


def test_consultant_runtime_build_memory_summary_ignores_messages_before_reset_boundary() -> None:
    runtime = ConsultantRuntime()
    conversation = SimpleNamespace(id=uuid4())
    messages = [
        SimpleNamespace(
            role="user",
            content="Я хочу записаться на маникюр на завтра.",
            message_metadata={},
            created_at=datetime(2026, 4, 1, 12, 3, tzinfo=timezone.utc),
        ),
        SimpleNamespace(
            role="assistant",
            content="Ок, давайте новую тему. Чем могу помочь?",
            message_metadata={"decision_meta": {"control_action": "session_reset"}},
            created_at=datetime(2026, 4, 1, 12, 2, tzinfo=timezone.utc),
        ),
        SimpleNamespace(
            role="user",
            content="начнем сначала",
            message_metadata={"decision_meta": {"session_memory_reset": "explicit_reset"}},
            created_at=datetime(2026, 4, 1, 12, 1, tzinfo=timezone.utc),
        ),
        SimpleNamespace(
            role="assistant",
            content="Как вас зовут?",
            message_metadata={},
            created_at=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
        ),
        SimpleNamespace(
            role="user",
            content="Завтра в 15:00.",
            message_metadata={},
            created_at=datetime(2026, 4, 1, 11, 59, tzinfo=timezone.utc),
        ),
    ]

    summary = runtime._build_memory_summary(_MessageDbStub(messages), conversation)

    assert summary == "user: Я хочу записаться на маникюр на завтра."


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
        "reason": "collect:datetime",
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
    }


def test_dialog_state_service_projects_booking_resume_contract_for_active_media_followup_with_noncanonical_goal_text() -> None:
    resume_contract = DialogStateService().project_interrupt_resume_pending_question_contract(
        {
            "expected_reply_type": "media",
            "next_question": "media",
            "open_questions": ["media"],
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
        },
        current_goal="Уточнить скидки и продолжить сбор времени по маникюру.",
        booking_payload={"service": "Маникюр"},
    )

    assert resume_contract == {
        "expected_reply_type": "time",
        "reason": "collect:datetime",
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
    }


def test_dialog_state_service_projects_booking_resume_contract_for_active_media_followup_with_specialist_carry() -> None:
    resume_contract = DialogStateService().project_interrupt_resume_pending_question_contract(
        {
            "expected_reply_type": "media",
            "next_question": "media",
            "open_questions": ["media"],
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
        },
        current_goal="booking",
        booking_payload={"service": "Маникюр"},
    )

    assert resume_contract == {
        "expected_reply_type": "time",
        "reason": "collect:datetime",
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
        "reason": "collect:media",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
        "next_question": "media",
        "open_questions": ["media"],
    }
    assert profile["resume_pending_question_contract"] == {
        "expected_reply_type": "time",
        "reason": "collect:datetime",
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
    }


def test_consultant_runtime_exposes_resume_contract_for_active_media_followup_with_specialist() -> None:
    planner = TurnPlanner()
    runtime = ConsultantRuntime()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "consult",
            "action": "collect",
            "tool_action": "consult",
            "goal": "booking",
            "reason": "user_offers_photo_reference_before_time_selection",
            "capability": "consultation",
            "pack_refs": ["style_reference"],
            "expected_reply_type": "media",
            "next_question": "media",
            "open_questions": ["media"],
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "carryover",
                },
                "specialist": {
                    "value": "Айгерим",
                    "entity_id": "sp:aygerim",
                    "entity_type": "specialist",
                    "source_ref": "user_message",
                },
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
        message_text="Могу прислать фото ногтей для примера.",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "Маникюр"},
        user_name=None,
        user_phone=None,
        now=datetime(2026, 4, 6, 0, 0, tzinfo=timezone.utc),
    )

    updated, dialog_state, booking_payload = DialogStateService().write_runtime_payload(
        {"booking": {"service": "Маникюр"}},
        decision=decision,
        execution_meta=execution.meta,
        now=datetime(2026, 4, 6, 0, 0, tzinfo=timezone.utc),
    )
    runtime_state = LoadedRuntimeState(
        context=updated,
        dialog_state=dialog_state,
        booking_state=booking_payload or {},
    )

    profile = runtime._build_policy_core_memory_profile(runtime_state)

    assert profile["pending_question_contract"] == {
        "expected_reply_type": "media",
        "reason": "collect:media",
        "pending_question_target": "specialist",
        "active_question_relation": "referent_followup",
        "next_question": "media",
        "open_questions": ["media"],
    }
    assert profile["resume_pending_question_contract"] == {
        "expected_reply_type": "time",
        "reason": "collect:datetime",
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
    }


def test_consultant_runtime_recovers_booking_resume_contract_from_active_media_followup_with_noncanonical_goal_text() -> None:
    planner = TurnPlanner()
    service = DialogStateService()
    runtime = ConsultantRuntime()
    now = datetime(2026, 4, 3, 0, 0, tzinfo=timezone.utc)
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "consult",
            "action": "collect",
            "tool_action": "consult",
            "goal": "Уточнить скидку и затем продолжить сбор времени по маникюру.",
            "reason": "user_offers_photo_reference_inside_booking_after_info_interrupt",
            "capability": "consultation",
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
        message_text="Могу прислать фото своих ногтей.",
        client_slug="demo_salon",
        branch_id=None,
        booking_state={"service": "Маникюр"},
        user_name=None,
        user_phone=None,
        now=now,
    )

    updated, dialog_state, booking_payload = service.write_runtime_payload(
        {"booking": {"service": "Маникюр"}},
        decision=decision,
        execution_meta=execution.meta,
        now=now,
    )
    assert dialog_state.meta["current_goal"] == "booking"
    assert dialog_state.semantic_state.materialized_frame.user_goal == "booking"
    dialog_state.meta["current_goal"] = "Ответить про скидки на маникюр и потом вернуться к времени."
    runtime_state = LoadedRuntimeState(
        context=updated,
        dialog_state=dialog_state,
        booking_state=booking_payload or {},
    )

    profile = runtime._build_policy_core_memory_profile(runtime_state)

    assert profile["active_goal"] == "booking"
    assert profile["resume_pending_question_contract"] == {
        "expected_reply_type": "time",
        "reason": "collect:datetime",
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
        "reason": "collect:media",
        "next_question": "media",
        "open_questions": ["media"],
    }
    assert dialog_state.interaction_state.resume_slot == "media"
    assert dialog_state.meta["current_goal"] == "consult"
    assert dialog_state.semantic_state.materialized_frame.reason == "user_offers_photos_for_style_reference"
    assert dialog_state.meta["semantic_contract"]["capability"] == "consultation"

    loaded = service.load_runtime_payload(updated)
    assert loaded["expected_reply_type"] == "media"
    assert loaded["expected_reply_reason"] == "collect:media"
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
    assert profile["semantic_contract"] == dialog_state.meta["semantic_contract"]
    assert "current_referents" not in profile
    assert "interaction_state" not in profile
    assert "active_slots" not in profile


def test_consultant_runtime_memory_profile_preserves_booking_capability_after_fact_interrupt() -> None:
    service = DialogStateService()
    runtime = ConsultantRuntime()
    planner = TurnPlanner()
    now = datetime(2026, 4, 3, 12, 0, tzinfo=timezone.utc)
    context = {
        "consultant_runtime": {
            "dialog_state": {
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
                        "constraints": {"temporal_scope": "specific_time"},
                        "preferences": {},
                        "continuation": {
                            "expected_reply_type": "time",
                            "reason": "collect:datetime",
                            "pending_question_act": "ask_about_requested_slot",
                            "pending_question_target": "time",
                            "active_question_relation": "ask_about_requested_slot",
                            "next_question": "datetime",
                            "open_questions": ["datetime"],
                            "slot_values": {"service": "Маникюр"},
                        },
                        "capability_selection": {
                            "capability": "bookability",
                            "resolution_mode": "ask_about_requested_slot",
                        },
                        "needs_human": False,
                        "reason": "collect:datetime",
                    },
                    "event_log": [],
                },
                "pending_question_contract": {
                    "expected_reply_type": "time",
                    "reason": "collect:datetime",
                    "pending_question_act": "ask_about_requested_slot",
                    "pending_question_target": "time",
                    "active_question_relation": "ask_about_requested_slot",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                },
                "current_referents": {
                    "service": "Маникюр",
                    "specialist": None,
                    "branch": None,
                    "booking": None,
                    "customer": None,
                },
                "interaction_state": {
                    "interaction_owner": "llm_policy_core",
                    "interaction_target": "time",
                    "interaction_relation": "ask_about_requested_slot",
                },
                "projections": {
                    "expected_reply_type": "time",
                    "expected_reply_reason": "collect:datetime",
                },
                "meta": {
                    "current_goal": "booking",
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "subject_kind": "service",
                        "capability": "bookability",
                        "temporal_scope": "specific_time",
                        "resolution_mode": "ask_about_requested_slot",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                    },
                },
            },
            "booking": {
                "active": True,
                "service": "Маникюр",
                "last_question": "datetime",
            },
        }
    }
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "pricing",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "tool_action_hint": "catalog.service_query",
            "goal": "booking",
            "reason": "user_asked_price_during_booking_continuity",
            "subject_kind": "service",
            "capability": "pricing",
            "resolution_mode": "policy_fact",
            "expected_reply_type": "time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "next_question": "datetime",
            "open_questions": ["datetime"],
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
        binding_tool_action="catalog.service_query",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    updated, dialog_state, booking_payload = service.write_runtime_payload(
        context,
        decision=decision,
        execution_meta={
            "tool_decision": "pricing",
            "slot_values": {"service": "Маникюр"},
        },
        now=now,
        conversation_id="conv-1",
        trace_id="trace-1",
    )
    runtime_state = LoadedRuntimeState(
        context=updated,
        dialog_state=dialog_state,
        booking_state=booking_payload or {},
    )

    profile = runtime._build_policy_core_memory_profile(runtime_state)

    assert profile["active_goal"] == "booking"
    assert profile["pending_question_contract"]["expected_reply_type"] == "time"
    assert profile["pending_question_contract"]["active_question_relation"] == "generic_info_interrupt"
    assert profile["semantic_contract"]["capability"] == "bookability"
    assert profile["semantic_contract"]["resolution_mode"] == "ask_about_requested_slot"
    assert profile["semantic_contract"]["pending_question_target"] == "time"
    assert profile["semantic_contract"]["active_question_relation"] == "generic_info_interrupt"


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


def test_consultant_runtime_memory_profile_no_longer_rebuilds_from_materialized_frame() -> None:
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

    assert profile["active_goal"] == "handoff"
    assert profile["semantic_contract"] == {
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
    assert profile["pending_question_contract"] == {
        "expected_reply_type": "name",
        "reason": "stale_projection",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
        "next_question": "name",
        "open_questions": ["name"],
    }
    assert profile["slot_state"] == {"service": "Маникюр"}


def test_consultant_runtime_contract_action_no_longer_uses_stale_legacy_carriers_for_booking_prompt() -> None:
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

    assert action == "collect"


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


def test_consultant_runtime_contract_action_preserves_owner_action_on_owner_backed_turn() -> None:
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

    assert action == "collect"


def test_consultant_runtime_owner_backed_trace_ignores_execution_meta_canonical_fields() -> None:
    runtime = ConsultantRuntime()
    planner = TurnPlanner()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "booking",
            "action": "collect",
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
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        interaction_owner="llm_policy_core_booking",
        source="llm_policy_core",
    )

    updated, dialog_state, _ = DialogStateService().write_runtime_payload(
        {},
        decision=decision,
        execution_meta={"next_slot": "datetime"},
        now=datetime(2026, 4, 3, 11, 0, tzinfo=timezone.utc),
        conversation_id="conv-owner-meta-filter",
        trace_id="trace-owner-meta-filter",
    )

    execution_meta = {
        "action": "handoff",
        "outcome": "HANDOFF",
        "expected_reply_type": "name",
        "expected_reply_reason": "stale_projection",
        "pending_question_act": "stale_pending_question",
        "pending_question_target": "name",
        "question_contract": True,
        "active_question_relation": "stale_relation",
        "pending_question_contract": {
            "expected_reply_type": "name",
            "reason": "stale_projection",
            "pending_question_act": "stale_pending_question",
            "pending_question_target": "name",
            "active_question_relation": "stale_relation",
        },
        "semantic_contract": {
            "contract_version": "semantic_contract.v1",
            "capability": "stale_capability",
            "pending_question_target": "name",
            "active_question_relation": "stale_relation",
        },
        "semantic_frame": {
            "schema_version": "semantic_frame.v2",
            "user_goal": "handoff",
        },
        "decision_trace": {"stage": "stale_runtime"},
        "tool_execution_projection": {"selected_specialist": None},
    }
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
    runtime_entry = next(entry for entry in trace if entry.get("stage") == "consultant_runtime")
    assert runtime_entry["decision"] == "collect"
    assert runtime_entry["outcome"] == "COLLECT"
    assert runtime_entry["expected_reply_type"] == "time"
    assert runtime_entry["expected_reply_reason"] == "collect_datetime"
    assert runtime_entry["pending_question_target"] == "time"
    assert runtime_entry["active_question_relation"] == "ask_about_requested_slot"
    assert runtime_entry["semantic_contract"]["capability"] == "bookability"
    assert runtime_entry["semantic_frame"]["user_goal"] == "booking"
    assert runtime_entry["tool_execution_projection"] == {"selected_specialist": None}

    decision_meta = (user_message.message_metadata or {}).get("decision_meta") or {}
    assert decision_meta["action"] == "collect"
    assert decision_meta["outcome"] == "COLLECT"
    assert decision_meta["expected_reply_type"] == "time"
    assert decision_meta["expected_reply_reason"] == "collect_datetime"
    assert decision_meta["pending_question_target"] == "time"
    assert decision_meta["active_question_relation"] == "ask_about_requested_slot"
    assert decision_meta["semantic_contract"]["capability"] == "bookability"
    assert decision_meta["semantic_frame"]["user_goal"] == "booking"
    assert decision_meta["decision_trace"]["stage"] == "consultant_runtime"
    assert decision_meta["decision_trace"]["pending_question_target"] == "time"
    assert decision_meta["tool_execution_projection"] == {"selected_specialist": None}


def test_consultant_runtime_contract_action_does_not_promote_non_owner_binding_plan_collect() -> None:
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

    assert action == "fact"


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
                "contract_action": "collect",
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


def test_consultant_runtime_memory_profile_ignores_canonical_semantic_state_without_explicit_meta() -> None:
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

    assert "active_goal" not in profile
    assert "slot_state" not in profile
    assert "pending_question_contract" not in profile
    assert "semantic_contract" not in profile


def test_consultant_runtime_memory_profile_keeps_only_explicit_meta_without_canonical_state() -> None:
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
        "active_goal": "handoff",
        "semantic_contract": {
            "contract_version": "semantic_contract.v1",
            "capability": "pricing",
            "subject_kind": "service",
        },
        "pending_question_contract": {
            "expected_reply_type": "name",
            "reason": "stale_projection",
            "next_question": "name",
            "open_questions": ["name"],
        },
    }


def test_consultant_runtime_memory_profile_deep_copies_canonical_semantic_payloads() -> None:
    runtime = ConsultantRuntime()
    dialog_state = DialogState.model_validate(_dialog_state_payload())
    dialog_state.meta["semantic_contract"] = {
        "contract_version": "semantic_contract.v1",
        "referents": {
            "branch": {
                "value": "almaty-center",
                "entity_type": "branch",
                "source_ref": "carryover",
            }
        },
    }

    profile = runtime._build_policy_core_memory_profile(
        SimpleNamespace(
            booking_state={"service": "manicure"},
            dialog_state=dialog_state,
        )
    )

    profile["semantic_contract"]["referents"]["branch"]["value"] = "astana-center"
    profile["pending_question_contract"]["open_questions"].append("name")

    assert dialog_state.semantic_state.materialized_frame.referents["branch"]["value"] == "almaty-center"
    assert dialog_state.meta["semantic_contract"]["referents"]["branch"]["value"] == "almaty-center"
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
        "pending_question_act": "ask_about_requested_slot",
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

    planner = TurnPlanner()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "booking",
            "action": "collect",
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
            "reason": "collect:datetime",
            "expected_reply_type": "time",
            "pending_question_act": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "goal": "booking",
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
        }
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="calendar.check_availability",
        interaction_owner="llm_policy_core_booking",
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
    assert runtime_trace_contract.action_transition.contract_action == "collect"
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


def test_boundary_validator_builds_typed_block_turn_outcome() -> None:
    boundary = BoundaryValidator()
    override = boundary.build_block_override(
        reason_code="missing_remote_jid",
        trace_message="reasoning_core blocked inbound without metadata.remoteJid",
        replan_hints=["require metadata.remoteJid"],
        meta={"source": "reasoning_core"},
    )
    turn_result = _build_boundary_turn_result(
        decision=None,
        override=override,
        contract_status="blocked",
        text="",
    )

    outcome = boundary.build_block_turn_outcome(
        turn_result=turn_result,
        tool_action="preflight.missing_remote_jid",
        intent="missing_remote_jid",
        meta={"control_label": "missing_remote_jid"},
    )

    assert outcome.action == "reject"
    assert outcome.intent == "missing_remote_jid"
    assert outcome.tool_action == "preflight.missing_remote_jid"
    assert outcome.tool_decision == "blocked"
    assert outcome.contract_status == "invalid"
    assert outcome.observability.transport_status == "skipped"
    assert outcome.observability.transport_reason == "missing_remote_jid"
    assert outcome.meta["preflight_path"] is True
    assert outcome.meta["boundary_decision"] == "block"
    assert outcome.meta["control_label"] == "missing_remote_jid"


def test_boundary_validator_builds_typed_ignored_block_turn_outcome() -> None:
    boundary = BoundaryValidator()
    override = boundary.build_block_override(
        reason_code="duplicate_message_id",
        trace_message="reasoning_core ignored preexisting duplicate message_id",
        replan_hints=["skip duplicate inbound message_id"],
        meta={"source": "reasoning_core"},
    )
    turn_result = _build_boundary_turn_result(
        decision=None,
        override=override,
        contract_status="blocked",
        text="",
    )

    outcome = boundary.build_block_turn_outcome(
        turn_result=turn_result,
        tool_action="preflight.duplicate_message_id",
        ignored=True,
        intent="duplicate_message_id",
        meta={"control_label": "duplicate_message_id"},
    )

    assert outcome.action == "ignore"
    assert outcome.intent == "duplicate_message_id"
    assert outcome.tool_action == "preflight.duplicate_message_id"
    assert outcome.tool_decision == "blocked"
    assert outcome.contract_status == "invalid"
    assert outcome.meta["ignored_path"] is True
    assert "preflight_path" not in outcome.meta
    assert outcome.meta["control_label"] == "duplicate_message_id"


def test_boundary_validator_builds_typed_degrade_turn_outcome() -> None:
    boundary = BoundaryValidator()
    override = boundary.build_degrade_override(
        reason_code="runtime_exception",
        public_message="Fallback response skipped",
        trace_message="reasoning_core exception degraded through new core",
        meta={"source": "reasoning_core"},
    )
    turn_result = _build_boundary_turn_result(
        decision=None,
        override=override,
        contract_status="degraded",
        text="Fallback response skipped",
    )

    outcome = boundary.build_degrade_turn_outcome(
        turn_result=turn_result,
        transport_status="failed",
        transport_reason="fallback_send_failed",
        intent="runtime_error",
        meta={"control_label": "runtime_error"},
    )

    assert outcome.action == "handoff"
    assert outcome.intent == "runtime_error"
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


def test_response_realizer_maps_degrade_to_handoff_without_override_business_control() -> None:
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
        meta={"executor_requested_handoff": True},
    )

    reply = ResponseRealizer().realize(decision, override=override, text="ignored")

    assert reply.reply_kind == "handoff"
    assert reply.text == "Передаю диалог менеджеру."
    assert reply.meta == {"boundary_decision": "degrade"}


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
    assert block_reply.meta == {"boundary_decision": "block"}

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
    assert degrade_reply.meta == {"boundary_decision": "degrade"}


def test_response_realizer_does_not_mint_outcome_meta_without_boundary_override() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "hours",
            "action": "fact",
            "tool_action": "catalog.service_query",
        },
        interaction_owner="llm_policy_core",
        interaction_relation="generic_info_interrupt",
        source="llm_policy_core",
    )

    reply = ResponseRealizer().realize(decision, text="Мы работаем до 20:00.")

    assert reply.reply_kind == "fact"
    assert reply.text == "Мы работаем до 20:00."
    assert reply.meta == {}


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
        _build_binding_only_boundary_decision(
            binding_plan=BindingPlanV1.build_degrade(
                decision_id="executor-degrade-handoff",
                degrade_reason_code="branch_missing",
            ),
            outcome="HANDOFF",
            action="handoff",
            intent="branch_missing",
            tool_action="handoff",
            reason_code="branch_missing",
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

    assert preserved_decision is decision
    assert preserved_decision.outcome == "FACT"
    assert preserved_decision.action == "fact"
    assert preserved_decision.tool_action == "catalog.service_query"
    assert preserved_decision.interaction.owner == "llm_policy_core"
    assert override is None
    assert runtime._should_activate_handoff(
        decision=preserved_decision,
        boundary_override=override,
        execution=execution,
    ) is True


def test_consultant_runtime_builds_planner_boundary_artifact_without_owner_replacement() -> None:
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
    override = runtime.boundary.build_degrade_override(
        reason_code="planner:missing_semantic_owner",
        public_message="Передаю диалог менеджеру, чтобы не потерять ваш запрос.",
        trace_message="missing_semantic_owner_guard_failed",
        meta={
            "degrade_stage": "planner",
            "planner_boundary_signal": True,
            "control_label": "planner_missing_semantic_owner",
            "handoff_activation_requested": True,
            "earliest_failed_stage": "planner",
            "root_reason_code": "planner:missing_semantic_owner",
            "missing_semantic_owner_guard": {
                "reason_code": "missing_semantic_owner",
            }
        },
    )

    artifact = runtime._build_planner_boundary_artifact(
        decision=decision,
        boundary_override=override,
    )
    execution = runtime._build_boundary_execution_result(
        boundary_override=override,
        reply=artifact.turn_result.reply,
    )

    assert artifact is not None
    assert artifact.turn_result.policy_decision.intent == decision.intent
    assert artifact.turn_result.policy_decision.action == decision.action
    assert artifact.turn_result.policy_decision.tool_action == decision.tool_action
    assert artifact.turn_result.contract_status == "degraded"
    assert artifact.turn_result.reply.reply_kind == "handoff"
    assert artifact.turn_result.observability.reason_code == "planner:missing_semantic_owner"
    assert artifact.turn_outcome.tool_decision == "planner_boundary_override"
    assert artifact.turn_outcome.meta["control_label"] == "planner_missing_semantic_owner"
    assert execution.tool_action == "handoff"
    assert execution.tool_decision == "planner_boundary_override"
    assert execution.request_handoff is True


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


def test_timeout_owner_boundary_resolution_is_disabled() -> None:
    from app.services.timeout_owner_boundary_service import apply_timeout_owner_boundary_resolution

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
    with pytest.raises(RuntimeError, match="timeout_owner_boundary_semantic_recovery_disabled"):
        apply_timeout_owner_boundary_resolution(
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
                set_booking_context=lambda *_args, **_kwargs: context,
                set_expected_reply_context=lambda **kwargs: kwargs["context"],
                get_booking_context=lambda current_context: current_context.get("booking") or {},
                get_expected_reply_type=lambda current_context: current_context.get("expected_reply_type"),
                get_expected_reply_reason=lambda current_context: current_context.get("expected_reply_reason"),
                get_context_manager=lambda current_context: dict(current_context.get("context_manager") or {}),
                sync_canonical_dialog_state=lambda manager, **_kwargs: dict(manager),
                set_context_manager=lambda current_context, manager: current_context,
                get_canonical_dialog_state=lambda manager: manager.get("canonical_dialog_state") or {},
                sync_session_memory_interaction_state=lambda current_context, interaction_state, now: (current_context, {}),
                set_conversation_context=lambda *_args, **_kwargs: None,
                apply_policy_guard_override=lambda **_kwargs: None,
                sync_policy_plan_audit=lambda **_kwargs: None,
                record_decision_trace=lambda *_args, **_kwargs: None,
                record_message_decision_meta=lambda *_args, **_kwargs: None,
                update_message_decision_metadata=lambda *_args, **_kwargs: None,
                send_and_save=lambda prompt: (prompt, True),
            ),
        )


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
