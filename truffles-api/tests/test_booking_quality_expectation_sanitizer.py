from app.services.llm_quality_contracts import extract_expectations


def test_extract_expectations_strips_handoff_action_for_booking_turn():
    expect = extract_expectations(
        {
            "tags": ["booking"],
            "expect": {"action": ["booking_escalated"], "reply_type": "time"},
        }
    )
    assert expect["action"] is None


def test_extract_expectations_keeps_handoff_action_for_handoff_turn():
    expect = extract_expectations(
        {
            "tags": ["handoff"],
            "expect": {"action": ["booking_escalated"], "reply_type": "time"},
        }
    )
    assert expect["action"] == "booking_escalated"


def test_extract_expectations_strips_pending_state_without_handoff_tags():
    expect = extract_expectations(
        {
            "tags": ["booking"],
            "expect": {"state": ["pending", "bot_active"], "reply_type": "time"},
        }
    )
    assert expect["state"] == "bot_active"


def test_extract_expectations_drops_info_sections_without_info_tags():
    expect = extract_expectations(
        {
            "tags": ["booking"],
            "expect": {"info_sections": ["service_duration"], "reply_type": "time"},
        }
    )
    assert expect["info_sections"] == []


def test_extract_expectations_compiles_booking_prompt_contract_for_service_choice_booking():
    expect = extract_expectations(
        {
            "tags": ["booking"],
            "expect": {
                "action": None,
                "reply_type": "service_choice",
                "state": "bot_active",
                "expected_reply": True,
            },
        }
    )

    assert expect["action"] == "booking_prompt"
    assert expect["meta"]["action"] == "booking_prompt"
    assert expect["meta"]["source"] == "llm_policy_core"
    assert expect["meta"]["tool_action"] == "collect"
    assert expect["meta"]["expected_reply_type"] == "service_choice"
    assert expect["meta"]["expected_reply_reason"] == "collect:service"
    assert expect["meta_any"]["action"] == ["booking_prompt"]
    assert expect["meta_any"]["expected_reply_type"] == ["service_choice"]
    assert expect["trace_contains"] == [
        {
            "stage": "question_contract",
            "expected_reply_type": "service_choice",
            "reason": "collect:service",
        }
    ]
