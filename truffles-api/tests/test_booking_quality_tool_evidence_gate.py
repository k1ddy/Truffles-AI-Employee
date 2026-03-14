import ast
from pathlib import Path


def _load_tool_evidence_helpers():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))

    wanted_assignments = {
        "LLM_QUALITY_BOOKING_CONFIRM_STATUS_HINTS",
        "LLM_QUALITY_CALENDAR_INTENTS",
        "LLM_QUALITY_CALENDAR_SUCCESS_DECISIONS",
        "LLM_QUALITY_CALENDAR_FAILURE_DECISIONS",
    }
    wanted_functions = {
        "_llm_quality_normalize_tool_token",
        "_llm_quality_effective_intent",
        "_llm_quality_tool_outcome_from_decision",
        "_llm_quality_calendar_outcome_from_meta",
        "_llm_quality_extract_tool_signals",
        "_llm_quality_should_send_calendar_hook",
        "_llm_quality_parse_coverage_tokens",
        "_llm_quality_build_tool_evidence_status",
        "_llm_quality_build_infra_status",
    }

    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if names & wanted_assignments:
                selected_nodes.append(node)
        if isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)

    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace


def test_extract_tool_signals_marks_calendar_intent_failure_on_provider_unavailable():
    ns = _load_tool_evidence_helpers()
    extract_tool_signals = ns["_llm_quality_extract_tool_signals"]

    signals = extract_tool_signals(
        {
            "action": "reply",
            "intent": "calendar.list_slots",
            "tool_decision": "provider_unavailable",
        },
        [],
    )

    assert signals["calendar"]["intent"] == "calendar.list_slots"
    assert signals["calendar"]["tool_decision"] == "provider_unavailable"
    assert signals["calendar"]["outcome"] == "failure"


def test_extract_tool_signals_marks_get_booking_not_found_as_successful_tool_call():
    ns = _load_tool_evidence_helpers()
    extract_tool_signals = ns["_llm_quality_extract_tool_signals"]

    signals = extract_tool_signals(
        {
            "action": "reply",
            "intent": "calendar.get_booking",
            "tool_decision": "not_found",
        },
        [],
    )

    assert signals["calendar"]["outcome"] == "success"
    assert signals["confirm"]["required"] is True

def test_calendar_hook_skips_list_slots_success_signal():
    ns = _load_tool_evidence_helpers()
    should_send = ns["_llm_quality_should_send_calendar_hook"]

    signal = {
        "calendar": {
            "intent": "calendar.list_slots",
            "tool_decision": "ok",
            "outcome": "success",
        }
    }
    assert should_send(signal, []) is False


def test_calendar_hook_allows_success_for_non_list_slots():
    ns = _load_tool_evidence_helpers()
    should_send = ns["_llm_quality_should_send_calendar_hook"]

    signal = {
        "calendar": {
            "intent": "calendar.get_booking",
            "tool_decision": "ok",
            "outcome": "success",
        }
    }
    assert should_send(signal, []) is True


def test_calendar_hook_blocks_non_success_outcome():
    ns = _load_tool_evidence_helpers()
    should_send = ns["_llm_quality_should_send_calendar_hook"]

    signal = {
        "calendar": {
            "intent": "calendar.get_booking",
            "tool_decision": "provider_unavailable",
            "outcome": "failure",
        }
    }
    assert should_send(signal, []) is False


def test_calendar_hook_allows_pending_for_non_list_slots():
    ns = _load_tool_evidence_helpers()
    should_send = ns["_llm_quality_should_send_calendar_hook"]

    signal = {
        "calendar": {
            "intent": "calendar.get_booking",
            "tool_decision": None,
            "outcome": "pending",
        }
    }
    assert should_send(signal, []) is True


def test_extract_tool_signals_normalizes_check_booking_intent_to_confirm_signal():
    ns = _load_tool_evidence_helpers()
    extract_tool_signals = ns["_llm_quality_extract_tool_signals"]

    signals = extract_tool_signals(
        {
            "action": "escalate",
            "intent": "check_booking",
            "llm_policy_core": {
                "payload": {
                    "tool_action": "calendar.get_booking",
                }
            },
        },
        [],
    )

    assert signals["confirm"]["required"] is True
    assert signals["calendar"]["intent"] == "check_booking"
    assert signals["calendar"]["outcome"] == "pending"


def test_tool_evidence_strict_policy_blocks_missing_calendar_and_confirm_evidence():
    ns = _load_tool_evidence_helpers()
    build_tool_evidence_status = ns["_llm_quality_build_tool_evidence_status"]
    build_infra_status = ns["_llm_quality_build_infra_status"]

    tool_evidence = build_tool_evidence_status(
        scenario_coverage="booking,info,interrupt",
        tool_hooks_mode="auto",
        tool_evidence_policy="strict",
        coverage_stats={
            "intents": {"calendar.get_booking": 3, "calendar.list_slots": 4},
            "actions": {"reply": 7},
            "trace_stages": {},
            "tools": {"events": {}},
            "tool_hooks": {"by_action": {}, "required_by_action": {"calendar": 1}},
        },
    )
    assert tool_evidence["valid"] is False
    assert "calendar_evidence_missing" in tool_evidence["reasons"]
    assert "confirm_evidence_missing" in tool_evidence["reasons"]
    assert "calendar_hook_missing" in tool_evidence["reasons"]
    assert "confirm_hook_missing" in tool_evidence["reasons"]

    infra = build_infra_status({}, {"valid": True, "reasons": []}, tool_evidence_status=tool_evidence)
    assert infra["valid"] is False
    assert "tool_evidence:calendar_evidence_missing" in infra["reasons"]


def test_tool_evidence_strict_policy_allows_fail_fast_prefix_without_observed_tool_opportunity():
    ns = _load_tool_evidence_helpers()
    build_tool_evidence_status = ns["_llm_quality_build_tool_evidence_status"]
    build_infra_status = ns["_llm_quality_build_infra_status"]

    tool_evidence = build_tool_evidence_status(
        scenario_coverage="booking,info,interrupt",
        tool_hooks_mode="auto",
        tool_evidence_policy="strict",
        coverage_stats={
            "intents": {},
            "actions": {"reply": 9},
            "trace_stages": {},
            "tools": {"events": {}},
            "tool_hooks": {"by_action": {}},
        },
    )

    assert tool_evidence["valid"] is True
    assert tool_evidence["reasons"] == []
    assert tool_evidence["required"]["booking"] is True
    assert tool_evidence["required"]["calendar"] is False
    assert tool_evidence["required"]["confirm"] is False
    assert tool_evidence["counts"]["calendar_opportunity_total"] == 0
    assert tool_evidence["counts"]["confirm_opportunity_total"] == 0

    infra = build_infra_status({}, {"valid": True, "reasons": []}, tool_evidence_status=tool_evidence)
    assert infra["valid"] is True
    assert infra["reasons"] == []


def test_tool_evidence_strict_policy_allows_provider_unavailable_calendar_failure_without_hook_candidate():
    ns = _load_tool_evidence_helpers()
    build_tool_evidence_status = ns["_llm_quality_build_tool_evidence_status"]
    build_infra_status = ns["_llm_quality_build_infra_status"]

    tool_evidence = build_tool_evidence_status(
        scenario_coverage="booking,info,interrupt",
        tool_hooks_mode="auto",
        tool_evidence_policy="strict",
        coverage_stats={
            "intents": {"calendar.book_slot": 1},
            "actions": {"reply": 1},
            "trace_stages": {},
            "tools": {"events": {"calendar": 1}},
            "tool_hooks": {"by_action": {}, "required_by_action": {}},
        },
    )

    assert tool_evidence["valid"] is True
    assert "calendar_hook_missing" not in tool_evidence["reasons"]
    assert tool_evidence["required"]["calendar"] is True
    assert tool_evidence["required"]["calendar_hook"] is False
    assert tool_evidence["counts"]["calendar_hook_candidates"] == 0

    infra = build_infra_status({}, {"valid": True, "reasons": []}, tool_evidence_status=tool_evidence)
    assert infra["valid"] is True
    assert infra["reasons"] == []


def test_tool_evidence_strict_policy_keeps_confirm_requirements_once_alias_opportunity_is_observed():
    ns = _load_tool_evidence_helpers()
    build_tool_evidence_status = ns["_llm_quality_build_tool_evidence_status"]

    tool_evidence = build_tool_evidence_status(
        scenario_coverage="booking,info,interrupt",
        tool_hooks_mode="auto",
        tool_evidence_policy="strict",
        coverage_stats={
            "intents": {"check_booking": 1},
            "actions": {},
            "trace_stages": {},
            "tools": {"events": {}},
            "tool_hooks": {"by_action": {}, "required_by_action": {"calendar": 1}},
        },
    )

    assert tool_evidence["valid"] is False
    assert "calendar_intent_missing" not in tool_evidence["reasons"]
    assert "calendar_evidence_missing" in tool_evidence["reasons"]
    assert "confirm_evidence_missing" in tool_evidence["reasons"]
    assert "calendar_hook_missing" in tool_evidence["reasons"]
    assert "confirm_hook_missing" in tool_evidence["reasons"]
    assert tool_evidence["required"]["calendar"] is True
    assert tool_evidence["required"]["confirm"] is True
    assert tool_evidence["counts"]["calendar_intent_candidates"] == 1
    assert tool_evidence["counts"]["calendar_opportunity_total"] == 1
    assert tool_evidence["counts"]["confirm_opportunity_total"] == 1


def test_tool_evidence_strict_policy_accepts_runs_with_calendar_and_confirm_proof():
    ns = _load_tool_evidence_helpers()
    build_tool_evidence_status = ns["_llm_quality_build_tool_evidence_status"]

    tool_evidence = build_tool_evidence_status(
        scenario_coverage="booking,info,interrupt",
        tool_hooks_mode="auto",
        tool_evidence_policy="strict",
        coverage_stats={
            "intents": {"calendar.get_booking": 2, "calendar.list_slots": 5},
            "actions": {"booking_confirm": 2},
            "trace_stages": {"booking_commit": 1, "booking_confirm": 2},
            "tools": {"events": {"calendar": 5, "confirm": 2, "commit": 1}},
            "tool_hooks": {
                "by_action": {"calendar": 1, "confirm": 1},
                "required_by_action": {"calendar": 1},
            },
        },
    )

    assert tool_evidence["valid"] is True
    assert tool_evidence["reasons"] == []


def test_tool_evidence_strict_policy_accepts_observed_confirm_evidence_without_explicit_candidate():
    ns = _load_tool_evidence_helpers()
    build_tool_evidence_status = ns["_llm_quality_build_tool_evidence_status"]
    build_infra_status = ns["_llm_quality_build_infra_status"]

    tool_evidence = build_tool_evidence_status(
        scenario_coverage="booking,info,interrupt",
        tool_hooks_mode="auto",
        tool_evidence_policy="strict",
        coverage_stats={
            "intents": {"calendar.book_slot": 1},
            "actions": {},
            "trace_stages": {"booking_confirm": 1},
            "tools": {"events": {"calendar": 1, "confirm": 1}},
            "tool_hooks": {"by_action": {"confirm": 1}, "required_by_action": {}},
        },
    )

    assert tool_evidence["valid"] is True
    assert "confirm_candidate_missing" not in tool_evidence["reasons"]
    assert tool_evidence["required"]["confirm"] is True
    assert tool_evidence["counts"]["check_booking_intents"] == 0
    assert tool_evidence["counts"]["booking_confirm_actions"] == 0
    assert tool_evidence["counts"]["confirm_observed"] is True
    assert tool_evidence["counts"]["confirm_evidence_total"] == 3

    infra = build_infra_status({}, {"valid": True, "reasons": []}, tool_evidence_status=tool_evidence)
    assert infra["valid"] is True
    assert infra["reasons"] == []


def test_tool_evidence_strict_policy_counts_check_booking_alias_intents():
    ns = _load_tool_evidence_helpers()
    build_tool_evidence_status = ns["_llm_quality_build_tool_evidence_status"]

    tool_evidence = build_tool_evidence_status(
        scenario_coverage="booking,info,interrupt",
        tool_hooks_mode="auto",
        tool_evidence_policy="strict",
        coverage_stats={
            "intents": {"check_booking": 2, "calendar.list_slots": 4},
            "actions": {},
            "trace_stages": {},
            "tools": {"events": {"calendar": 4, "confirm": 2}},
            "tool_hooks": {
                "by_action": {"calendar": 1, "confirm": 1},
                "required_by_action": {"calendar": 1},
            },
        },
    )

    assert tool_evidence["valid"] is True
    assert tool_evidence["counts"]["check_booking_intents"] == 2


def test_tool_evidence_strict_policy_requires_auto_tool_hooks_mode():
    ns = _load_tool_evidence_helpers()
    build_tool_evidence_status = ns["_llm_quality_build_tool_evidence_status"]

    tool_evidence = build_tool_evidence_status(
        scenario_coverage="booking,info,interrupt",
        tool_hooks_mode="check",
        tool_evidence_policy="strict",
        coverage_stats={
            "intents": {"calendar.get_booking": 2},
            "actions": {"booking_confirm": 1},
            "trace_stages": {"booking_commit": 1, "booking_confirm": 1},
            "tools": {"events": {"calendar": 2, "confirm": 1}},
            "tool_hooks": {"by_action": {"calendar": 1, "confirm": 1}},
        },
    )

    assert tool_evidence["valid"] is False
    assert "tool_hooks_mode_not_auto" in tool_evidence["reasons"]
