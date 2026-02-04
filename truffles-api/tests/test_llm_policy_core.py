from app.schemas.intent import validate_llm_policy_core_output


def test_validate_llm_policy_core_output_valid():
    payload = {
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
    payload = {"action": "", "confidence": 1.2}

    contract, error = validate_llm_policy_core_output(payload)

    assert contract is None
    assert error is not None
