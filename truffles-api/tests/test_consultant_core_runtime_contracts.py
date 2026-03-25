from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from jsonschema import Draft202012Validator, FormatChecker, RefResolver

from app.core import (
    BlockBoundaryRequest,
    BoundaryOverride,
    BoundaryValidator,
    DegradeBoundaryRequest,
    DialogState,
    DialogStateService,
    PolicyDecision,
    ResponseRealizer,
    TurnExecutor,
    TurnPlanner,
)
from app.core.consultant_runtime import ConsultantRuntime
from app.services.policy_validation_boundary_service import (
    PolicyValidationBoundaryRuntimeHooks,
    PolicyValidationBoundaryRuntimeInput,
    handle_policy_validation_boundary,
)
from app.services import reasoning_core as reasoning_core_service


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


def _dialog_state_payload() -> dict:
    return {
        "schema_version": "dialog_state.v1",
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
        return TurnPlanner().build_from_policy_override(
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
    state.meta["semantic_contract"] = {
        "contract_version": "semantic_contract.v1",
        "subject_kind": "specialist",
        "capability": "bookability",
        "resolution_mode": "referent_followup",
        "pending_question_target": "specialist",
        "active_question_relation": "referent_followup",
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
        "active_slots": ["service"],
        "current_referents": {
            "service": "manicure",
            "specialist": "Айгерим",
            "branch": "almaty-center",
            "customer": "Марина",
        },
        "pending_question_contract": {
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "expected_reply_type": "time",
            "reason": "booking_time_availability_followup",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
        },
        "interaction_state": {
            "resume_slot": "time",
            "interaction_target": "time",
            "interaction_relation": "ask_about_requested_slot",
            "interaction_owner": "booking_time_followup",
            "grounded_referents": {
                "service": "manicure",
                "specialist": "Айгерим",
                "customer": "Марина",
            },
        },
        "semantic_contract": {
            "contract_version": "semantic_contract.v1",
            "subject_kind": "specialist",
            "capability": "bookability",
            "resolution_mode": "referent_followup",
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
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
            },
        },
    }
    assert decision.interaction.owner == "llm_policy_core_booking"
    assert override is None


def test_consultant_runtime_plan_turn_prefills_grounded_service_for_policy_core(
) -> None:
    runtime = ConsultantRuntime()
    captured: dict[str, object] = {}

    def _fake_plan(**kwargs):
        captured.update(kwargs)
        return TurnPlanner().build_from_policy_override(
            {
                "intent": "booking",
                "action": "collect",
                "tool_action": "collect",
                "goal": "booking",
                "slots": {"service": "маникюр"},
                "next_question": "datetime",
                "open_questions": ["datetime"],
            },
            interaction_owner="llm_policy_core_booking",
            interaction_relation="fill_requested_slot",
            source="llm_policy_core",
        )

    runtime.planner.plan = _fake_plan
    runtime._build_memory_summary = lambda *_args, **_kwargs: "user: test"
    state = DialogState.model_validate(_dialog_state_payload())
    state.current_referents.service = None

    with patch(
        "app.core.consultant_runtime.semantic_service_match",
        return_value=None,
    ), patch(
        "app.core.consultant_runtime.get_pack_service_hint",
        return_value="маникюр",
    ):
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

    assert captured["booking_state"] == {"service": "маникюр"}
    assert captured["memory_profile"]["current_referents"]["service"] == "маникюр"
    assert decision.pending_question_contract.next_question == "datetime"
    assert override is None


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
    _load_schema("contracts/runtime/policy_decision.v1.jsonschema").validate(_policy_payload())
    _load_schema("contracts/runtime/dialog_state.v1.jsonschema").validate(_dialog_state_payload())
    _load_schema("contracts/runtime/boundary_override.v1.jsonschema").validate(_boundary_override_payload())
    _load_schema("contracts/runtime/turn_result.v1.jsonschema").validate(_turn_result_payload())


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
    assert result.reply.reply_kind == "collect"


def test_turn_planner_builds_policy_decision_from_policy_override_payload() -> None:
    planner = TurnPlanner()

    decision = planner.build_from_policy_override(
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


def test_turn_planner_builds_tool_reply_owner_decision_for_pending_question_followup() -> None:
    planner = TurnPlanner()

    decision = planner.build_tool_reply_owner_decision(
        payload={
            "reason": "semantic_temporal_scope_missing_slot_guidance",
            "tool_args": {"service_query": "Маникюр"},
        },
        default_intent="booking",
        reply_intent="booking",
        tool_action="calendar.list_slots",
        expected_reply_type="time",
        pending_question_tool_followup=True,
        pending_question_act="ask_about_requested_slot",
    )

    _load_schema("contracts/runtime/policy_decision.v1.jsonschema").validate(
        decision.model_dump(mode="json")
    )
    assert decision.intent == "booking"
    assert decision.action == "collect"
    assert decision.tool_action == "calendar.list_slots"
    assert decision.interaction.owner == "booking_slot_guidance"
    assert decision.interaction.relation == "ask_about_requested_slot"


def test_turn_planner_builds_tool_reply_owner_decision_for_master_override() -> None:
    planner = TurnPlanner()

    decision = planner.build_tool_reply_owner_decision(
        payload={"tool_action": "catalog.service_query"},
        default_intent="master",
        reply_intent="service_duration",
        tool_action="catalog.service_query",
        expected_reply_type=None,
        master_override_applied=True,
    )

    _load_schema("contracts/runtime/policy_decision.v1.jsonschema").validate(
        decision.model_dump(mode="json")
    )
    assert decision.intent == "master"
    assert decision.action == "fact"
    assert decision.tool_action == "catalog.service_query"
    assert decision.interaction.owner == "policy_core_guard"
    assert decision.interaction.relation == "policy_guard"


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


def test_turn_executor_builds_typed_block_boundary_turn_result() -> None:
    planner = TurnPlanner()
    boundary = BoundaryValidator()
    decision = planner.build_preflight_reject(
        reason_code="missing_remote_jid",
        action="preflight_reject",
        intent="missing_remote_jid",
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
        action="handoff",
        intent="runtime_error",
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
        action="preflight_reject",
        intent="missing_remote_jid",
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
        action="handoff",
        intent="runtime_error",
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
            action="preflight_reject",
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
    assert artifact.turn_result.boundary_override is not None
    assert artifact.turn_result.boundary_override.reason_code == "missing_remote_jid"
    assert artifact.turn_result.dialog_state.meta["block_path"] is True
    assert artifact.turn_outcome.tool_action == "preflight.missing_remote_jid"
    assert artifact.turn_outcome.meta["preflight_path"] is True


def test_turn_executor_builds_typed_degrade_boundary_artifact_from_request() -> None:
    artifact = TurnExecutor().build_degrade_boundary_artifact_from_request(
        request=DegradeBoundaryRequest(
            reason_code="runtime_exception",
            action="handoff",
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
    assert artifact.turn_result.boundary_override is not None
    assert artifact.turn_result.boundary_override.reason_code == "runtime_exception"
    assert artifact.turn_result.dialog_state.meta["degrade_path"] is True
    assert artifact.turn_outcome.tool_action == "handoff"
    assert artifact.turn_outcome.meta["degrade_path"] is True
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
    decision = TurnPlanner().build_from_policy_override(
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


def test_turn_executor_builds_tool_reply_owner_cutover_payload_for_pending_question() -> None:
    decision = TurnPlanner().build_tool_reply_owner_decision(
        payload={
            "intent": "booking",
            "action": "collect",
            "tool_action": "calendar.list_slots",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        default_intent="booking",
        reply_intent="booking",
        tool_action="calendar.list_slots",
        expected_reply_type="time",
        pending_question_tool_followup=True,
    )
    dialog_state = DialogStateService().build_tool_reply_owner_state(
        decision=decision,
        expected_reply_type="time",
        expected_reply_reason="booking_slot_guidance",
        owner_cutover="turn_executor.tool_reply_turn_outcome.v1",
    )

    payload = TurnExecutor().build_tool_reply_owner_cutover_payload(
        decision=decision,
        dialog_state=dialog_state,
        text="На какое время вам удобно?",
        owner_cutover="turn_executor.tool_reply_turn_outcome.v1",
        reply_source="tool_registry",
        reply_intent="calendar.list_slots",
        intent="booking",
        tool_action="calendar.list_slots",
        raw_tool_decision="missing_slot",
        normalized_tool_decision="missing_slot",
        followup_type="time",
        followup_reason="booking_slot_guidance",
        followup_prompt=None,
        services_overview_followup=False,
        conversation_state="bot_active",
        pending_question_tool_followup=True,
        pending_question_act="ask_about_requested_slot",
        pending_question_target=None,
        saved_message_present=True,
    )

    assert payload.artifact.turn_outcome.contract_status == "ok"
    assert payload.trace_payload_override["tool_decision"] == "missing_slot"
    assert payload.trace_payload_override["reply_source"] == "tool_registry"
    assert (
        payload.trace_payload_override["turn_outcome"]["meta"]["interaction_owner"]
        == "booking_slot_guidance"
    )
    assert payload.extra_trace_payloads == [
        {
            "stage": "pending_question_interaction",
            "decision": "booking_slot_guidance",
            "state": "bot_active",
            "source": "tool_registry",
            "tool_action": "calendar.list_slots",
            "tool_decision": "missing_slot",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "expected_reply_type": "time",
        }
    ]
    assert payload.extra_meta_updates == [
        {"intent": "calendar.list_slots"},
        {
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "pending_question_interaction": "ask_about_requested_slot",
            "pending_question_owner": "booking_slot_guidance",
        },
    ]


def test_turn_executor_builds_tool_reply_owner_cutover_payload_for_interrupt_and_override() -> None:
    decision = TurnPlanner().build_tool_reply_owner_decision(
        payload={
            "intent": "services_overview",
            "action": "fact",
            "tool_action": "catalog.service_query",
        },
        default_intent="services_overview",
        reply_intent="master",
        tool_action="catalog.service_query",
        expected_reply_type="service_choice",
        collect_service_info_interrupt_active=True,
        master_override_applied=True,
    )
    dialog_state = DialogStateService().build_tool_reply_owner_state(
        decision=decision,
        expected_reply_type="service_choice",
        expected_reply_reason="services_overview",
        owner_cutover="turn_executor.tool_reply_turn_outcome.v1",
    )

    payload = TurnExecutor().build_tool_reply_owner_cutover_payload(
        decision=decision,
        dialog_state=dialog_state,
        text="Могу подсказать услуги.",
        owner_cutover="turn_executor.tool_reply_turn_outcome.v1",
        reply_source="policy_core_guard",
        reply_intent="master",
        intent="master",
        tool_action="catalog.service_query",
        raw_tool_decision="services_overview",
        normalized_tool_decision="verifier_blocked",
        followup_type="service_choice",
        followup_reason="services_overview",
        followup_prompt="Какую услугу хотите?",
        services_overview_followup=True,
        conversation_state="bot_active",
        collect_service_info_interrupt_active=True,
        info_sections=["services_overview"],
        saved_message_present=True,
        master_override_meta={"policy_semantic_override_block_reason": "master_signal_override_blocked"},
    )

    assert payload.artifact.turn_outcome.contract_status == "degraded"
    assert payload.artifact.turn_outcome.source == "policy_core_guard"
    assert payload.trace_payload_override["tool_decision"] == "services_overview"
    assert payload.extra_trace_payloads == [
        {
            "stage": "booking_interrupt",
            "decision": "info_reply",
            "state": "bot_active",
            "booking_interrupt_info": True,
            "info_sections": ["services_overview"],
        }
    ]
    assert payload.extra_meta_updates == [
        {"intent": "master"},
        {
            "booking_info_interrupt": True,
            "booking_interrupt_info": True,
            "booking_info_intents": ["services_overview"],
        },
        {"policy_semantic_override_block_reason": "master_signal_override_blocked"},
    ]


def test_turn_executor_builds_tool_reply_owner_execution() -> None:
    runtime_input = {
        "payload": {
            "intent": "services_overview",
            "action": "fact",
            "tool_action": "catalog.service_query",
        },
        "default_intent": "master",
        "reply_intent": "master",
        "tool_action": "catalog.service_query",
        "expected_reply_type": "service_choice",
        "expected_reply_reason": "services_overview",
        "text": "Могу подсказать услуги.",
        "owner_cutover": "turn_executor.tool_reply_turn_outcome.v1",
        "reply_source": "policy_core_guard",
        "intent": "master",
        "raw_tool_decision": "services_overview",
        "normalized_tool_decision": "verifier_blocked",
        "followup_prompt": "Какую услугу хотите?",
        "services_overview_followup": True,
        "conversation_state": "bot_active",
        "collect_service_info_interrupt_active": True,
        "info_sections": ["services_overview"],
        "saved_message_present": True,
        "master_override_applied": True,
        "master_override_meta": {
            "policy_semantic_override_block_reason": "master_signal_override_blocked"
        },
    }

    expected_decision = TurnPlanner().build_tool_reply_owner_decision(
        payload=runtime_input["payload"],
        default_intent=runtime_input["default_intent"],
        reply_intent=runtime_input["reply_intent"],
        tool_action=runtime_input["tool_action"],
        expected_reply_type=runtime_input["expected_reply_type"],
        collect_service_info_interrupt_active=runtime_input[
            "collect_service_info_interrupt_active"
        ],
        master_override_applied=runtime_input["master_override_applied"],
    )
    expected_state = DialogStateService().build_tool_reply_owner_state(
        decision=expected_decision,
        expected_reply_type=runtime_input["expected_reply_type"],
        expected_reply_reason=runtime_input["expected_reply_reason"],
        owner_cutover=runtime_input["owner_cutover"],
    )
    expected_payload = TurnExecutor().build_tool_reply_owner_cutover_payload(
        decision=expected_decision,
        dialog_state=expected_state,
        text=runtime_input["text"],
        owner_cutover=runtime_input["owner_cutover"],
        reply_source=runtime_input["reply_source"],
        reply_intent=runtime_input["reply_intent"],
        intent=runtime_input["intent"],
        tool_action=runtime_input["tool_action"],
        raw_tool_decision=runtime_input["raw_tool_decision"],
        normalized_tool_decision=runtime_input["normalized_tool_decision"],
        followup_type=runtime_input["expected_reply_type"],
        followup_reason=runtime_input["expected_reply_reason"],
        followup_prompt=runtime_input["followup_prompt"],
        services_overview_followup=runtime_input["services_overview_followup"],
        conversation_state=runtime_input["conversation_state"],
        collect_service_info_interrupt_active=runtime_input[
            "collect_service_info_interrupt_active"
        ],
        info_sections=runtime_input["info_sections"],
        saved_message_present=runtime_input["saved_message_present"],
        master_override_meta=runtime_input["master_override_meta"],
    )

    execution = TurnExecutor().build_tool_reply_owner_execution(**runtime_input)

    assert execution.decision == expected_decision
    assert execution.dialog_state == expected_state
    assert execution.payload == expected_payload


def test_reasoning_core_finalizes_tool_reply_owner_execution(monkeypatch) -> None:
    runtime_input = {
        "payload": {
            "intent": "services_overview",
            "action": "fact",
            "tool_action": "catalog.service_query",
        },
        "default_intent": "master",
        "reply_intent": "master",
        "tool_action": "catalog.service_query",
        "expected_reply_type": "service_choice",
        "expected_reply_reason": "services_overview",
        "text": "Могу подсказать услуги.",
        "owner_cutover": "turn_executor.tool_reply_turn_outcome.v1",
        "reply_source": "policy_core_guard",
        "intent": "master",
        "raw_tool_decision": "services_overview",
        "normalized_tool_decision": "verifier_blocked",
        "followup_prompt": "Какую услугу хотите?",
        "services_overview_followup": True,
        "conversation_state": "bot_active",
        "collect_service_info_interrupt_active": True,
        "info_sections": ["services_overview"],
        "saved_message_present": True,
        "master_override_applied": True,
        "master_override_meta": {
            "policy_semantic_override_block_reason": "master_signal_override_blocked"
        },
    }
    execution = TurnExecutor().build_tool_reply_owner_execution(**runtime_input)
    captured: dict[str, object] = {}
    sentinel_response = object()

    def _fake_guard(**kwargs):
        captured["guard_kwargs"] = kwargs
        return None

    def _fake_finalize(**kwargs):
        captured["finalize_kwargs"] = kwargs
        return sentinel_response

    monkeypatch.setattr(
        reasoning_core_service,
        "_finalize_turn_planner_owner_cutover",
        _fake_finalize,
    )

    result = reasoning_core_service._finalize_tool_reply_owner_execution(
        payload=SimpleNamespace(),
        db=SimpleNamespace(),
        client_id=None,
        conversation=SimpleNamespace(id="conv-1"),
        saved_message=SimpleNamespace(id="msg-1"),
        owner_execution=execution,
        reply_text=runtime_input["text"],
        reply_intent=runtime_input["reply_intent"],
        reply_source=runtime_input["reply_source"],
        owner_cutover=runtime_input["owner_cutover"],
        tool_decision=runtime_input["normalized_tool_decision"],
        expected_reply_type=runtime_input["expected_reply_type"],
        expected_reply_reason=runtime_input["expected_reply_reason"],
        maybe_apply_fact_guard=_fake_guard,
        guard_decision_meta={"fact_source": "truth"},
        allow_handover=True,
        send_and_save=lambda text: (text, True),
        transport_status_token="sent",
        transport_reason_token=None,
    )

    assert result is sentinel_response
    assert captured["guard_kwargs"] == {
        "decision_meta": {"fact_source": "truth"},
        "intent": "master",
        "source": "policy_core_guard",
        "allow_handover": True,
    }
    assert captured["finalize_kwargs"]["decision"] == execution.decision
    assert captured["finalize_kwargs"]["artifact"] == execution.payload.artifact
    assert (
        captured["finalize_kwargs"]["trace_payload_override"]
        == execution.payload.trace_payload_override
    )
    assert (
        captured["finalize_kwargs"]["extra_trace_payloads"]
        == execution.payload.extra_trace_payloads
    )
    assert (
        captured["finalize_kwargs"]["extra_meta_updates"]
        == execution.payload.extra_meta_updates
    )
    assert captured["finalize_kwargs"]["guard_response"] is None


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


def test_dialog_state_service_builds_tool_reply_owner_state_with_followup() -> None:
    decision = TurnPlanner().build_tool_reply_owner_decision(
        payload={
            "intent": "booking",
            "action": "collect",
            "tool_action": "calendar.list_slots",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        default_intent="booking",
        reply_intent="booking",
        tool_action="calendar.list_slots",
        expected_reply_type="time",
        pending_question_tool_followup=True,
    )

    state = DialogStateService().build_tool_reply_owner_state(
        decision=decision,
        expected_reply_type="time",
        expected_reply_reason="booking_slot_guidance",
        owner_cutover="turn_executor.tool_reply_turn_outcome.v1",
    )

    _load_schema("contracts/runtime/dialog_state.v1.jsonschema").validate(
        state.model_dump(mode="json")
    )
    assert state.projections.expected_reply_type == "time"
    assert state.projections.expected_reply_reason == "booking_slot_guidance"
    assert state.interaction_state.interaction_owner == "booking_slot_guidance"
    assert state.meta["owner_cutover"] == "turn_executor.tool_reply_turn_outcome.v1"


def test_turn_executor_builds_typed_booking_prompt_owner_cutover_artifact() -> None:
    decision = TurnPlanner().build_from_policy_override(
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
    decision = TurnPlanner().build_from_policy_override(
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
    decision = TurnPlanner().build_from_policy_override(
        {
            "intent": "check_booking",
            "action": "fact",
            "tool_action": "calendar.get_booking",
            "reason": "booking_verification_text",
            "goal": "booking",
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


def test_turn_executor_routes_master_query_through_master_catalog() -> None:
    decision = TurnPlanner().build_from_policy_override(
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
    decision = TurnPlanner().build_from_policy_override(
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


def test_turn_executor_adds_pricing_info_sections_for_price_reply() -> None:
    decision = TurnPlanner().build_from_policy_override(
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

    decision = TurnPlanner().build_from_policy_override(
        {
            "intent": "info",
            "action": "fact",
            "tool_action": "info",
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
    assert result.text == "Официальные акции: первое посещение 10%."
    assert result.tool_decision == "promotions"
    assert result.tool_action == "catalog.service_query"
    assert result.meta.get("resolved_tool_action") == "catalog.service_query"
    assert result.meta.get("tool_execution_projection") == {
        "projection_source": "semantic_contract",
        "service_query": "маникюр",
    }
    assert result.meta["semantic_contract"]["referents"]["service"] == {
        "value": "маникюр",
        "entity_id": "svc:manicure",
        "entity_type": "service",
        "source_ref": "message",
    }


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

    decision = TurnPlanner().build_from_policy_override(
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
    assert result.meta.get("tool_execution_projection") == {
        "projection_source": "semantic_contract",
        "service_query": "маникюр",
        "specialist_name": "Айгерим",
        "specialist_id": specialist_id,
    }


def test_turn_executor_keeps_original_fact_query_text_without_semantic_rewrite(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def _get_pack_decision(query_text: str, client_slug: str | None = None):
        captured["query_text"] = query_text
        return SimpleNamespace(response="Цена зависит от услуги.", intent="price_query", meta={}, action="reply")

    monkeypatch.setattr("app.services.pack_runtime_service.get_pack_decision", _get_pack_decision)

    decision = TurnPlanner().build_from_policy_override(
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

    decision = TurnPlanner().build_from_policy_override(
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
    assert runtime_payload["semantic_contract"]["referents"]["service"] == expected_service_referent
    assert runtime_payload["semantic_contract"]["grounding_provenance"]["pack_id"] == "demo_salon"

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

    decision = TurnPlanner().build_from_policy_override(
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

    assert result.text == "Есть ли акции?"
    assert result.tool_decision == "passthrough"
    assert result.meta == {"fact_fallback": True}


def test_consultant_runtime_records_question_contract_trace_entries() -> None:
    decision = TurnPlanner().build_from_policy_override(
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
        "reason": "collect:datetime",
        "pending_question_act": "slot_constraint",
        "pending_question_target": "time",
        "active_question_relation": "slot_constraint",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }


def test_consultant_runtime_trace_prefers_canonical_question_contract_over_stale_projection() -> None:
    runtime = ConsultantRuntime()
    decision = TurnPlanner().build_from_policy_override(
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


def test_turn_executor_omits_empty_pending_question_contract_from_execution_meta() -> None:
    decision = TurnPlanner().build_from_policy_override(
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


def test_consultant_runtime_records_referent_followup_axes_in_trace_and_meta() -> None:
    decision = TurnPlanner().build_from_policy_override(
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
    decision = TurnPlanner().build_from_policy_override(
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


def test_consultant_runtime_finalizes_booking_commit_as_terminal_fact() -> None:
    decision = TurnPlanner().build_from_policy_override(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "calendar.book_slot",
            "goal": "booking",
            "reason": "answer_interpreter_fallback",
        },
        interaction_owner="turn_planner_fallback",
        interaction_relation="fill_requested_slot",
        source="answer_interpreter",
    )
    execution = SimpleNamespace(
        tool_action="calendar.book_slot",
        tool_decision="ok",
        meta={"appointment_id": "appt-123"},
    )

    finalized = ConsultantRuntime._finalize_execution_decision(
        decision=decision,
        execution=execution,
    )

    assert finalized.outcome == "FACT"
    assert finalized.action == "collect"


def test_turn_executor_builds_typed_explicit_handoff_owner_cutover_artifact() -> None:
    decision = TurnPlanner().build_from_policy_override(
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
        action="preflight_reject",
        intent="missing_remote_jid",
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
    assert outcome.intent == "missing_remote_jid"
    assert outcome.tool_action == "preflight.missing_remote_jid"
    assert outcome.tool_decision == "blocked"
    assert outcome.contract_status == "invalid"
    assert outcome.observability.transport_status == "skipped"
    assert outcome.observability.transport_reason == "missing_remote_jid"
    assert outcome.meta["preflight_path"] is True
    assert outcome.meta["boundary_decision"] == "block"


def test_boundary_validator_builds_typed_degrade_turn_outcome() -> None:
    planner = TurnPlanner()
    boundary = BoundaryValidator()
    decision = planner.build_controlled_degrade(
        reason_code="runtime_exception",
        action="handoff",
        intent="runtime_error",
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
    assert outcome.intent == "runtime_error"
    assert outcome.tool_action == "handoff"
    assert outcome.tool_decision == "runtime_exception"
    assert outcome.contract_status == "degraded"
    assert outcome.observability.transport_status == "failed"
    assert outcome.observability.transport_reason == "fallback_send_failed"
    assert outcome.meta["degrade_path"] is True
    assert outcome.meta["boundary_decision"] == "degrade"


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
