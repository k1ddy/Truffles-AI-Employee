import ast
from pathlib import Path


def _load_chaos_action_fallback_ok():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))

    wanted_assigns = {"CHAOS_PENDING_ACTIONS", "CHAOS_BOOKING_REPLY_TYPES"}
    wanted_functions = {
        "_chaos_extract_expected_reply",
        "_chaos_booking_reply_active",
        "_chaos_trace_has_pending",
        "_chaos_booking_completion_actions",
        "_chaos_action_fallback_ok",
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
    return namespace["_chaos_action_fallback_ok"]


def test_chaos_action_fallback_allows_provider_unavailable_reply_for_booking_escalated():
    fallback = _load_chaos_action_fallback_ok()

    expected = {"action_any": ["booking_escalated"], "expected_reply_type": "time"}
    meta = {
        "action": "reply",
        "intent": "calendar.list_slots",
        "tool_decision": "provider_unavailable",
    }
    conv_meta = {"state": "bot_active", "context": {"booking": {"active": True}}}

    assert fallback(expected, meta, conv_meta, trace_entries=[], info_sections_ok=False) is True


def test_chaos_action_fallback_does_not_allow_generic_reply_without_provider_unavailable():
    fallback = _load_chaos_action_fallback_ok()

    expected = {"action_any": ["booking_escalated"], "expected_reply_type": "time"}
    meta = {
        "action": "reply",
        "intent": "calendar.list_slots",
        "tool_decision": "ok",
    }
    conv_meta = {"state": "bot_active", "context": {"booking": {"active": True}}}

    assert fallback(expected, meta, conv_meta, trace_entries=[], info_sections_ok=False) is False
