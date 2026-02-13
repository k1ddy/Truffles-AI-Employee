from app.schemas.intent import validate_llm_policy_core_output
from app.routers.webhook import decision as decision_router


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
    }

    contract, error = validate_llm_policy_core_output(payload)

    assert error is None
    assert contract is not None
    assert contract.action == "fact"
    assert contract.tool_action == "info"


def test_validate_llm_policy_core_output_invalid():
    payload = {"action": "", "tool_action": "info", "slots": {}, "confidence": 1.2}

    contract, error = validate_llm_policy_core_output(payload)

    assert contract is None
    assert error is not None


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
