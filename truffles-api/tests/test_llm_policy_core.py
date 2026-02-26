from app.routers.webhook import decision as decision_router
from app.schemas.intent import validate_llm_plan_output, validate_llm_policy_core_output


def test_validate_llm_policy_core_output_valid():
    payload = {
        "intent": "pricing",
        "action": "fact",
        "tool_action": "info",
        "tool_args": {"service_query": "маникюр"},
        "pack_refs": ["pricing"],
        "slots": {"service": "маникюр"},
        "next_question": "service",
        "open_questions": ["service"],
        "needs_manager": False,
        "risk_signals": ["discounts"],
        "language": "ru",
        "confidence": 0.7,
        "reason": "pricing",
        "goal": "info",
        "entity_refs": [{"entity_id": "svc:manicure", "entity_type": "service"}],
        "resolver_id": "llm_policy_core",
        "resolver_version": "v1",
    }

    contract, error = validate_llm_policy_core_output(payload)

    assert error is None
    assert contract is not None
    assert contract.action == "fact"
    assert contract.tool_action == "info"
    assert contract.resolver_id == "llm_policy_core"
    assert contract.resolver_version == "v1"
    assert contract.entity_refs and contract.entity_refs[0].get("entity_id") == "svc:manicure"


def test_validate_llm_policy_core_output_invalid():
    payload = {"action": "", "tool_action": "info", "slots": {}, "confidence": 1.2}

    contract, error = validate_llm_policy_core_output(payload)

    assert contract is None
    assert error is not None


def test_validate_llm_policy_core_output_rejects_unknown_calendar_tool_arg():
    payload = {
        "intent": "booking",
        "action": "fact",
        "tool_action": "calendar.book_slot",
        "tool_args": {"service_query": "маникюр", "start_at": "2026-02-17T13:00:00", "foo": "bar"},
        "pack_refs": [],
        "slots": {"service": "маникюр", "datetime": "2026-02-17 13:00", "name": "Алия"},
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "confidence": 0.9,
    }

    contract, error = validate_llm_policy_core_output(payload)

    assert contract is None
    assert error is not None
    assert "tool_args_unknown_field:foo" in error


def test_validate_llm_policy_core_output_rejects_invalid_catalog_info_refs_type():
    payload = {
        "intent": "location",
        "action": "fact",
        "tool_action": "catalog.location",
        "tool_args": {"info_refs": "parking"},
        "pack_refs": ["location"],
        "slots": {},
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "confidence": 0.9,
    }

    contract, error = validate_llm_policy_core_output(payload)

    assert contract is None
    assert error is not None
    assert "tool_args_type_invalid:info_refs" in error


def test_validate_llm_plan_output_rejects_invalid_tool_args_shape():
    payload = {
        "outcome": "fact",
        "tool_action": "catalog.location",
        "tool_args": {"info_refs": "parking"},
        "confidence": 0.8,
    }

    contract, error = validate_llm_plan_output(payload)

    assert contract is None
    assert error is not None
    assert "tool_args_type_invalid:info_refs" in error


def test_low_confidence_allowlist_includes_reschedule():
    assert "calendar.reschedule" in decision_router.LLM_POLICY_CORE_LOW_CONFIDENCE_TOOL_ALLOWLIST


def test_derive_policy_info_refs_accepts_slot_style_hours_hint():
    refs = decision_router._derive_policy_info_refs(
        policy_intent="hours",
        message_text="а как у вас там",
        client_slug="demo_salon",
    )

    assert "hours" in refs


def test_should_collect_service_for_info_only_when_service_dependent():
    assert decision_router._should_collect_service_for_info({"pricing"}) is True
    assert decision_router._should_collect_service_for_info({"duration"}) is True
    assert decision_router._should_collect_service_for_info({"duration", "hours"}) is False
    assert decision_router._should_collect_service_for_info({"pricing", "location"}) is False
