import ast
from pathlib import Path


def _load_state_fallback():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))

    selected_nodes = []
    wanted_assigns = {"CHAOS_PENDING_ACTIONS"}
    wanted_functions = {
        "_llm_quality_normalize_tool_token",
        "_llm_quality_effective_intent",
        "_chaos_booking_completion_actions",
        "_chaos_state_fallback_ok",
    }
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
    return namespace["_chaos_state_fallback_ok"]


def test_state_fallback_allows_pending_pass_for_provider_unavailable_reply():
    fn = _load_state_fallback()
    assert fn(
        "bot_active",
        "pending",
        {"action": "reply", "pending_action": "pending_pass", "tool_decision": "provider_unavailable"},
        {},
        {},
    )


def test_state_fallback_does_not_allow_generic_pending_reply_without_pending_pass():
    fn = _load_state_fallback()
    assert not fn(
        "bot_active",
        "pending",
        {"action": "reply", "pending_action": None, "tool_decision": "ok"},
        {},
        {},
    )


def test_state_fallback_allows_pending_when_expected_manager_active_and_escalated():
    fn = _load_state_fallback()
    assert fn(
        "manager_active",
        "pending",
        {"action": "escalate", "pending_action": "pending_pass"},
        {},
        {},
    )


def test_state_fallback_allows_info_reply_while_pending_for_expected_bot_active():
    fn = _load_state_fallback()
    assert fn(
        "bot_active",
        "pending",
        {"action": "reply", "intent": "catalog.location", "tool_decision": "ok"},
        {},
        {"status": "active"},
    )
