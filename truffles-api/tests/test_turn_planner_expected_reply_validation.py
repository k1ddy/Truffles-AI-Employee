from app.core.turn_planner import TurnPlanner


def test_expected_reply_datetime_validation_rejects_info_interrupt():
    planner = TurnPlanner()

    value = planner._validate_expected_reply_slot_value(
        "Есть ли акции?",
        normalized_slot="datetime",
        client_slug="demo_salon",
        interpreted_value="акции",
    )

    assert value is None


def test_expected_reply_datetime_validation_accepts_real_datetime():
    planner = TurnPlanner()

    value = planner._validate_expected_reply_slot_value(
        "Завтра в 15:00",
        normalized_slot="datetime",
        client_slug="demo_salon",
        interpreted_value="завтра в 15:00",
    )

    assert value in {"15:00", "2026-03-25t15:00:00"}


def test_expected_reply_name_validation_rejects_price_question():
    planner = TurnPlanner()

    value = planner._validate_expected_reply_slot_value(
        "Какая цена?",
        normalized_slot="name",
        client_slug="demo_salon",
        interpreted_value="Какая цена",
    )

    assert value is None


def test_expected_reply_name_validation_accepts_real_name():
    planner = TurnPlanner()

    value = planner._validate_expected_reply_slot_value(
        "Алина",
        normalized_slot="name",
        client_slug="demo_salon",
        interpreted_value="Алина",
    )

    assert value == "Алина"


def test_expected_reply_service_validation_rejects_grounded_duration_interrupt():
    planner = TurnPlanner()

    value = planner._validate_expected_reply_slot_value(
        "Как вы оцениваете время на наращивание полигелем?",
        normalized_slot="service",
        client_slug="demo_salon",
        interpreted_value="Наращивание полигелем",
    )

    assert value is None


def test_plan_rescues_valid_name_reply_when_policy_core_misclassifies(monkeypatch):
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
    monkeypatch.setattr(
        "app.services.intent_service.interpret_expected_reply",
        lambda *args, **kwargs: {"payload": {"value": "Алина"}},
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

    assert decision.action == "collect"
    assert decision.intent == "booking"
    assert decision.source == "answer_interpreter"
    assert decision.tool_action == "collect"
    assert decision.slots["name"] == "Алина"
    assert decision.pending_question_contract.next_question is None


def test_plan_routes_booking_confirmation_into_reference_collect(monkeypatch):
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

    assert decision.action == "collect"
    assert decision.intent == "confirm_booking"
    assert decision.source == "turn_planner_intent_routing"
    assert decision.tool_action == "collect"
    assert decision.pending_question_contract.next_question == "datetime"
    assert decision.pending_question_contract.open_questions == ["datetime"]


def test_plan_recovers_check_booking_intent_from_calendar_lookup_fact(monkeypatch):
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
                "intent": "booking",
                "tool_action": "calendar.get_booking",
                "slots": {},
            }
        },
    )

    decision = planner.plan(
        message_text="Проверьте мою запись на четверг.",
        client_slug="demo_salon",
        expected_reply_type=None,
        expected_reply_reason=None,
        current_goal=None,
        booking_state=None,
    )

    assert decision.action == "fact"
    assert decision.intent == "check_booking"
    assert decision.source == "llm_policy_core"
    assert decision.tool_action == "calendar.get_booking"


def test_plan_short_circuits_active_booking_price_interrupt_before_policy_degrade(monkeypatch):
    planner = TurnPlanner()

    monkeypatch.setattr(
        "app.services.consult_pack_service.load_consult_playbook",
        lambda client_slug: ({}, None),
    )
    monkeypatch.setattr(
        "app.services.intent_service.route_llm_policy_core",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("policy core should not run")),
    )

    decision = planner.plan(
        message_text="А сколько это стоит?",
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

    assert decision.action == "fact"
    assert decision.intent == "info"
    assert decision.source == "turn_planner_intent_routing"
    assert decision.tool_action == "catalog.service_query"
    assert decision.tool_args == {"service_query": "Маникюр"}
    assert decision.slots == {"service": "Маникюр"}


def test_plan_preserves_grounded_service_on_service_choice_duration_interrupt(monkeypatch):
    planner = TurnPlanner()

    monkeypatch.setattr(
        "app.services.consult_pack_service.load_consult_playbook",
        lambda client_slug: ({}, None),
    )

    decision = planner.plan(
        message_text="Как вы оцениваете время на наращивание полигелем?",
        client_slug="demo_salon",
        expected_reply_type="service_choice",
        expected_reply_reason="collect:service",
        current_goal="booking",
        booking_state={
            "active": True,
            "name": "Айгерим",
            "datetime": "2026-03-25T19:00:00+00:00",
            "last_question": "service",
        },
    )

    assert decision.action == "fact"
    assert decision.intent == "duration"
    assert decision.source == "turn_planner_intent_routing"
    assert decision.tool_args == {"service_query": "Наращивание полигелем"}
    assert decision.slots == {"service": "Наращивание полигелем"}


def test_plan_recovers_explicit_time_fill_before_duration_interrupt(monkeypatch):
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
                "intent": "duration",
                "tool_action": "catalog.service_query",
                "slots": {},
                "fact_refs": ["duration"],
            }
        },
    )
    monkeypatch.setattr(
        "app.services.intent_service.interpret_expected_reply",
        lambda *args, **kwargs: {"payload": {"value": "в субботу 15:00"}},
    )

    decision = planner.plan(
        message_text="Может быть, в субботу в 3 часа?",
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

    assert decision.action == "collect"
    assert decision.intent == "booking"
    assert decision.source == "answer_interpreter"
    assert isinstance(decision.slots["datetime"], str) and decision.slots["datetime"]
    assert decision.pending_question_contract.next_question == "name"


def test_plan_keeps_slot_constraint_question_contract_for_question_like_time_request(monkeypatch):
    planner = TurnPlanner()

    monkeypatch.setattr(
        "app.services.consult_pack_service.load_consult_playbook",
        lambda client_slug: ({}, None),
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

    assert decision.action == "collect"
    assert decision.intent == "booking"
    assert decision.source == "question_contract"
    assert decision.tool_args.get("candidate_datetime") in {"15:00", "завтра 15:00"}
    assert decision.slots.get("datetime") in {"15:00", "завтра 15:00"}
    assert decision.meta["pending_question_act"] == "slot_constraint"
    assert decision.pending_question_contract.next_question == "datetime"
