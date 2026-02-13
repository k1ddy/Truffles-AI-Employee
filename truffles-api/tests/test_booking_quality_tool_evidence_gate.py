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
        "_llm_quality_tool_outcome_from_decision",
        "_llm_quality_calendar_outcome_from_meta",
        "_llm_quality_extract_tool_signals",
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
            "tool_hooks": {"by_action": {}},
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
            "tool_hooks": {"by_action": {"calendar": 1, "confirm": 1}},
        },
    )

    assert tool_evidence["valid"] is True
    assert tool_evidence["reasons"] == []
