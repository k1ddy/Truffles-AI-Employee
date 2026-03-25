from app.core.turn_planner import TurnPlanner


def test_plan_returns_policy_core_payload_without_expected_reply_rescue(monkeypatch):
    planner = TurnPlanner()

    monkeypatch.setattr(
        "app.services.consult_pack_service.load_consult_playbook",
        lambda client_slug: ({}, None),
    )
    monkeypatch.setattr(
        "app.services.intent_service.route_llm_policy_core",
        lambda *args, **kwargs: {
            "payload": {
                "action": "fact",
                "intent": "other",
                "tool_action": "calendar.book_slot",
                "slots": {},
            }
        },
    )

    decision = planner.plan(
        message_text="Алина",
        client_slug="demo_salon",
        expected_reply_type="name",
        expected_reply_reason="collect:name",
        current_goal="booking",
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
        expected_reply_type=None,
        expected_reply_reason=None,
        current_goal=None,
        booking_state=None,
    )

    assert decision.action == "handoff"
    assert decision.intent == "planner_degrade"
    assert decision.interaction.owner == "turn_planner_degrade"
    assert decision.meta["reason_code"] == "planner:policy_timeout"



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
            "payload": {
                "action": "collect",
                "intent": "booking",
                "tool_action": "collect",
                "tool_args": {"candidate_datetime": "завтра 15:00"},
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
        }

    monkeypatch.setattr(
        "app.services.intent_service.route_llm_policy_core",
        _route_llm_policy_core,
    )

    decision = planner.plan(
        message_text="Есть ли место завтра в 15:00?",
        client_slug="demo_salon",
        expected_reply_type="time",
        expected_reply_reason="collect:datetime",
        current_goal="booking",
        booking_state={
            "active": True,
            "service": "Маникюр",
            "last_question": "datetime",
        },
    )

    assert policy_calls == ["Есть ли место завтра в 15:00?"]
    assert decision.source == "llm_policy_core"
    assert decision.interaction.owner == "llm_policy_core_booking"
    assert decision.slots == {"datetime": "завтра 15:00"}
