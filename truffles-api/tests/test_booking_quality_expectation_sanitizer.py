from app.services.llm_quality_contracts import (
    apply_booking_scenario_active_time_specialist_followup_expectations,
    extract_expectations,
)


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


def test_extract_expectations_compiles_canonical_collect_contract_for_service_choice_booking():
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

    assert expect["action"] == "collect"
    assert expect["meta"]["action"] == "collect"
    assert expect["meta"]["source"] == "llm_policy_core"
    assert expect["meta"]["tool_action"] == "collect"
    assert expect["meta"]["expected_reply_type"] == "service_choice"
    assert expect["meta"]["expected_reply_reason"] == "collect:service"
    assert expect["meta_any"]["action"] == ["collect"]
    assert expect["meta_any"]["expected_reply_type"] == ["service_choice"]
    assert expect["trace_contains"] == [
        {
            "stage": "question_contract",
            "expected_reply_type": "service_choice",
            "reason": "collect:service",
        }
    ]


def test_extract_expectations_strips_stale_booking_prompt_for_active_time_specialist_followup():
    expect = extract_expectations(
        {
            "tags": ["booking"],
            "expect": {
                "action": "booking_prompt",
                "reply_type": "time",
                "state": "bot_active",
                "expected_reply": True,
                "meta": {
                    "action": "booking_prompt",
                    "source": "llm_policy_core",
                    "tool_action": "collect",
                    "expected_reply_type": "service_choice",
                    "expected_reply_reason": "collect:service",
                },
                "meta_any": {
                    "action": ["booking_prompt"],
                    "source": ["llm_policy_core"],
                    "tool_action": ["collect"],
                    "expected_reply_type": ["service_choice"],
                    "expected_reply_reason": ["collect:service"],
                    "pending_question_target": ["specialist"],
                    "active_question_relation": ["referent_followup"],
                },
                "trace_contains": [
                    {
                        "stage": "question_contract",
                        "expected_reply_type": "service_choice",
                        "reason": "collect:service",
                    }
                ],
            },
        }
    )

    assert expect["action"] is None
    assert expect["meta"]["source"] == "llm_policy_core"
    assert expect["meta"]["tool_action"] == "collect"
    assert expect["meta"]["expected_reply_type"] == "time"
    assert "action" not in expect["meta"]
    assert "expected_reply_reason" not in expect["meta"]
    assert expect["meta_any"]["tool_action"] == ["collect"]
    assert expect["meta_any"]["expected_reply_type"] == ["time"]
    assert "action" not in expect["meta_any"]
    assert "expected_reply_reason" not in expect["meta_any"]
    assert expect["trace_contains"] == [
        {
            "stage": "question_contract",
            "expected_reply_type": "time",
        }
    ]


def test_active_time_specialist_followup_repair_drops_stale_service_collect_contract():
    expect = apply_booking_scenario_active_time_specialist_followup_expectations(
        {
            "action": "booking_prompt",
            "reply_type": "time",
            "state": "bot_active",
            "expected_reply": True,
            "meta": {
                "action": "booking_prompt",
                "source": "llm_policy_core",
                "tool_action": "collect",
                "expected_reply_type": "service_choice",
                "expected_reply_reason": "collect:service",
            },
            "meta_any": {
                "action": ["booking_prompt"],
                "source": ["llm_policy_core"],
                "tool_action": ["collect"],
                "expected_reply_type": ["service_choice"],
                "expected_reply_reason": ["collect:service"],
            },
            "trace_contains": [
                {
                    "stage": "question_contract",
                    "expected_reply_type": "service_choice",
                    "reason": "collect:service",
                }
            ],
        },
        tags=["booking"],
        text="Я хочу записаться к Динаре.",
        active_reply_type="time",
    )

    assert expect["action"] is None
    assert expect["reply_type"] == "time"
    assert expect["meta"]["tool_action"] == "collect"
    assert expect["meta"]["expected_reply_type"] == "time"
    assert "action" not in expect["meta"]
    assert "expected_reply_reason" not in expect["meta"]
    assert expect["meta_any"]["pending_question_target"] == ["specialist"]
    assert expect["meta_any"]["active_question_relation"] == ["referent_followup"]
    assert expect["meta_any"]["expected_reply_type"] == ["time"]
    assert "action" not in expect["meta_any"]
    assert "expected_reply_reason" not in expect["meta_any"]
    assert expect["trace_contains"] == [
        {
            "stage": "question_contract",
            "expected_reply_type": "time",
        }
    ]
