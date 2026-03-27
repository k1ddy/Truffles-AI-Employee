from app.core.turn_planner import TurnPlanner
from tests import build_test_semantic_decision_payload


def test_plan_returns_policy_core_payload_without_expected_reply_rescue(monkeypatch):
    planner = TurnPlanner()

    monkeypatch.setattr(
        "app.services.consult_pack_service.load_consult_playbook",
        lambda client_slug: ({}, None),
    )
    monkeypatch.setattr(
        "app.services.intent_service.route_llm_policy_core",
        lambda *args, **kwargs: {
            "policy_input": {"message": "Алина", "task": "llm_policy_core"},
            "payload": build_test_semantic_decision_payload(
                {
                    "action": "fact",
                    "intent": "other",
                    "tool_action": "calendar.book_slot",
                    "slots": {},
                }
            ),
            "binding": {
                "tool_action": "calendar.book_slot",
                "tool_args": {},
            },
        },
    )

    decision = planner.plan(
        message_text="Алина",
        client_slug="demo_salon",
        booking_state={
            "active": True,
            "service": "маникюр",
            "datetime": "2026-03-25T15:00:00Z",
            "last_question": "name",
        },
    )

    assert decision.action == "fact"
    assert decision.intent == "other"
    assert decision.source == "llm_policy_core"
    assert decision.tool_action == "calendar.book_slot"
    assert decision.slots == {}
    assert decision.meta["policy_core_trace"]["status"] == "ok"
    assert decision.meta["policy_core_trace"]["schema_verdict"] == "ok"
    assert decision.meta["policy_core_trace"]["projection_verdict"] == "ok"
    assert decision.meta["policy_core_trace"]["input"]["message"] == "Алина"


def test_plan_degrades_when_policy_core_success_is_missing_binding(monkeypatch):
    planner = TurnPlanner()

    monkeypatch.setattr(
        "app.services.consult_pack_service.load_consult_playbook",
        lambda client_slug: ({}, None),
    )
    monkeypatch.setattr(
        "app.services.intent_service.route_llm_policy_core",
        lambda *args, **kwargs: {
            "policy_input": {"message": "Алина", "task": "llm_policy_core"},
            "payload": build_test_semantic_decision_payload(
                {
                    "action": "fact",
                    "intent": "other",
                    "tool_action": "calendar.book_slot",
                    "slots": {},
                }
            ),
        },
    )

    decision = planner.plan(
        message_text="Алина",
        client_slug="demo_salon",
        booking_state=None,
    )

    assert decision.action == "handoff"
    assert decision.intent == "planner_degrade"
    assert decision.meta["reason_code"] == "planner:invalid_projection"
    assert decision.meta["earliest_failed_stage"] == "policy_projection"
    assert decision.meta["root_reason_code"] == "policy_projection:binding_tool_action_missing"
    assert decision.meta["policy_core_trace"]["projection_verdict"] == "binding_tool_action_missing"


def test_plan_degrades_when_policy_core_success_uses_legacy_policy_payload(monkeypatch):
    planner = TurnPlanner()

    monkeypatch.setattr(
        "app.services.consult_pack_service.load_consult_playbook",
        lambda client_slug: ({}, None),
    )
    monkeypatch.setattr(
        "app.services.intent_service.route_llm_policy_core",
        lambda *args, **kwargs: {
            "policy_input": {"message": "Алина", "task": "llm_policy_core"},
            "payload": {
                "action": "fact",
                "intent": "other",
                "tool_action": "calendar.book_slot",
                "slots": {},
            },
            "binding": {
                "tool_action": "calendar.book_slot",
                "tool_args": {},
            },
        },
    )

    decision = planner.plan(
        message_text="Алина",
        client_slug="demo_salon",
        booking_state={
            "active": True,
            "service": "маникюр",
            "datetime": "2026-03-25T15:00:00Z",
            "last_question": "name",
        },
    )

    assert decision.action == "handoff"
    assert decision.intent == "planner_degrade"
    assert decision.meta["reason_code"] == "planner:invalid_projection"
    assert decision.meta["earliest_failed_stage"] == "policy_projection"
    assert decision.meta["root_reason_code"] == "policy_projection:semantic_decision_required"
    assert decision.meta["policy_core_trace"]["projection_verdict"] == "semantic_decision_required"



def test_plan_degrades_when_policy_core_is_unavailable_instead_of_routing_fallback(monkeypatch):
    planner = TurnPlanner()

    monkeypatch.setattr(
        "app.services.consult_pack_service.load_consult_playbook",
        lambda client_slug: ({}, None),
    )
    monkeypatch.setattr(
        "app.services.intent_service.route_llm_policy_core",
        lambda *args, **kwargs: {"error": "policy_timeout"},
    )

    decision = planner.plan(
        message_text="Подтвердите, пожалуйста, мою запись на четверг.",
        client_slug="demo_salon",
        booking_state=None,
    )

    assert decision.action == "handoff"
    assert decision.intent == "planner_degrade"
    assert decision.interaction.owner == "turn_planner_degrade"
    assert decision.meta["reason_code"] == "planner:policy_timeout"
    assert decision.meta["earliest_failed_stage"] == "policy_core"
    assert decision.meta["root_reason_code"] == "policy_core:policy_timeout"
    assert decision.meta["policy_core_trace"]["status"] == "error"
    assert decision.meta["policy_core_trace"]["projection_verdict"] == "skipped"


def test_plan_records_policy_core_schema_failure_bundle(monkeypatch):
    planner = TurnPlanner()

    monkeypatch.setattr(
        "app.services.consult_pack_service.load_consult_playbook",
        lambda client_slug: ({}, None),
    )
    monkeypatch.setattr(
        "app.services.intent_service.route_llm_policy_core",
        lambda *args, **kwargs: {
            "error": "invalid_schema",
            "attempted": True,
            "elapsed_ms": 187.5,
            "raw": '{"broken":true}',
            "schema_error": "tool_action_missing",
            "policy_input": {"message": "Когда запись?", "task": "llm_policy_core"},
            "model_name": "gpt-5.4-nano-2026-03-17",
            "attempt_count": 1,
            "structured_output_enabled": True,
            "structured_output_fallback_used": False,
        },
    )

    decision = planner.plan(
        message_text="Когда запись?",
        client_slug="demo_salon",
        booking_state=None,
    )

    assert decision.meta["reason_code"] == "planner:invalid_schema"
    assert decision.meta["earliest_failed_stage"] == "policy_core"
    assert decision.meta["root_reason_code"] == "policy_core:invalid_schema"
    assert decision.meta["policy_core_trace"] == {
        "attempted": True,
        "status": "error",
        "schema_verdict": "invalid_schema",
        "projection_verdict": "skipped",
        "input": {"message": "Когда запись?", "task": "llm_policy_core"},
        "raw_output": '{"broken":true}',
        "error": "invalid_schema",
        "schema_error": "tool_action_missing",
        "elapsed_ms": 187.5,
        "model_name": "gpt-5.4-nano-2026-03-17",
        "attempt_count": 1,
        "structured_output_enabled": True,
        "structured_output_fallback_used": False,
    }


def test_plan_records_policy_projection_failure_bundle(monkeypatch):
    planner = TurnPlanner()

    monkeypatch.setattr(
        "app.services.consult_pack_service.load_consult_playbook",
        lambda client_slug: ({}, None),
    )
    monkeypatch.setattr(
        "app.services.intent_service.route_llm_policy_core",
        lambda *args, **kwargs: {
            "error": "invalid_projection",
            "attempted": True,
            "elapsed_ms": 91.2,
            "raw": '{"intent":"booking"}',
            "policy_input": {"message": "Можно завтра?", "task": "llm_policy_core"},
            "projection_error": "collect_tool_action_hint_conflict",
            "projection_trace": {
                "status": "error",
                "projection_source": "policy_tool_projector",
                "tool_action_hint": "calendar.list_slots",
                "error": "collect_tool_action_hint_conflict",
            },
            "model_name": "gpt-5.4-nano-2026-03-17",
            "attempt_count": 1,
            "structured_output_enabled": True,
            "structured_output_fallback_used": False,
        },
    )

    decision = planner.plan(
        message_text="Можно завтра?",
        client_slug="demo_salon",
        booking_state=None,
    )

    assert decision.meta["reason_code"] == "planner:invalid_projection"
    assert decision.meta["earliest_failed_stage"] == "policy_projection"
    assert (
        decision.meta["root_reason_code"]
        == "policy_projection:collect_tool_action_hint_conflict"
    )
    assert decision.meta["policy_core_trace"]["schema_verdict"] == "ok"
    assert (
        decision.meta["policy_core_trace"]["projection_verdict"]
        == "collect_tool_action_hint_conflict"
    )
    assert decision.meta["policy_core_trace"]["projection"] == {
        "status": "error",
        "projection_source": "policy_tool_projector",
        "tool_action_hint": "calendar.list_slots",
        "error": "collect_tool_action_hint_conflict",
    }


def test_plan_no_longer_short_circuits_question_contract_before_policy_core(monkeypatch):
    planner = TurnPlanner()
    policy_calls: list[str] = []

    monkeypatch.setattr(
        "app.services.consult_pack_service.load_consult_playbook",
        lambda client_slug: ({}, None),
    )

    def _route_llm_policy_core(message_text: str, **kwargs):
        policy_calls.append(message_text)
        return {
            "payload": build_test_semantic_decision_payload(
                {
                    "action": "collect",
                    "intent": "booking",
                    "tool_action": "collect",
                    "slots": {"datetime": "завтра 15:00"},
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                    "goal": "booking",
                    "reason": "llm_policy_core_slot_constraint",
                    "question_contract": True,
                    "pending_question_act": "slot_constraint",
                    "pending_question_target": "time",
                    "active_question_relation": "slot_constraint",
                }
            ),
            "binding": {
                "tool_action": "collect",
                "tool_args": {},
            },
        }

    monkeypatch.setattr(
        "app.services.intent_service.route_llm_policy_core",
        _route_llm_policy_core,
    )

    decision = planner.plan(
        message_text="Есть ли место завтра в 15:00?",
        client_slug="demo_salon",
        booking_state={
            "active": True,
            "service": "Маникюр",
            "last_question": "datetime",
        },
    )

    assert policy_calls == ["Есть ли место завтра в 15:00?"]
    assert decision.source == "llm_policy_core"
    assert decision.interaction.owner == "llm_policy_core"
    assert decision.slots == {"datetime": "завтра 15:00"}


def test_plan_delegates_context_assembly_to_policy_core_route(monkeypatch):
    planner = TurnPlanner()
    captured_kwargs: dict[str, object] = {}

    def _route_llm_policy_core(message_text: str, **kwargs):
        captured_kwargs["message_text"] = message_text
        captured_kwargs.update(kwargs)
        return {
            "payload": build_test_semantic_decision_payload(
                {
                    "action": "collect",
                    "intent": "booking",
                    "tool_action": "collect",
                    "slots": {"service": "Маникюр"},
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                    "goal": "booking",
                    "reason": "llm_policy_core_collect",
                }
            ),
            "binding": {
                "tool_action": "collect",
                "tool_args": {},
            },
        }

    monkeypatch.setattr(
        "app.services.intent_service.route_llm_policy_core",
        _route_llm_policy_core,
    )

    decision = planner.plan(
        message_text="Хочу записаться на маникюр",
        client_slug="demo_salon",
        booking_state={"active": True, "service": "Маникюр"},
        memory_summary="Клиент хочет маникюр",
    )

    assert decision.source == "llm_policy_core"
    assert captured_kwargs["message_text"] == "Хочу записаться на маникюр"
    assert captured_kwargs["client_slug"] == "demo_salon"
    assert captured_kwargs["memory_summary"] == "Клиент хочет маникюр"
    assert "info_refs" not in captured_kwargs
    assert "consult_refs" not in captured_kwargs
