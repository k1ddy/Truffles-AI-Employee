import ast
from pathlib import Path


def _load_reply_type_fallback():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))

    wanted_assigns = {"CHAOS_BOOKING_REPLY_TYPES", "CHAOS_PENDING_ACTIONS"}
    wanted_functions = {
        "_llm_quality_normalize_tool_token",
        "_llm_quality_effective_intent",
        "_chaos_trace_has_stage",
        "_chaos_trace_has_stage_with_reason",
        "_chaos_trace_has_pending",
        "_chaos_trace_has_truth_hours",
        "_chaos_reply_type_fallback_ok",
    }
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if wanted_assigns & names:
                selected_nodes.append(node)
        if isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)

    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace["_chaos_reply_type_fallback_ok"]


def test_reply_type_fallback_allows_calendar_get_booking_tool_ok():
    fn = _load_reply_type_fallback()
    assert fn(
        "time",
        None,
        {"intent": "calendar.get_booking", "tool_decision": "ok"},
        {"state": "bot_active"},
        [],
    )


def test_reply_type_fallback_does_not_allow_unrelated_tool_intent():
    fn = _load_reply_type_fallback()
    assert not fn(
        "time",
        None,
        {"intent": "catalog.service_query", "tool_decision": "ok"},
        {"state": "bot_active"},
        [],
    )


def test_reply_type_fallback_allows_media_portfolio_reply_during_booking():
    fn = _load_reply_type_fallback()
    assert fn(
        "name",
        None,
        {"intent": "catalog.portfolio", "tool_decision": "ok"},
        {"state": "bot_active"},
        [],
    )
