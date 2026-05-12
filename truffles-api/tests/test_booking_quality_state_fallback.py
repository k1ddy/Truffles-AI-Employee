import ast
from pathlib import Path


def _load_selected_ops_functions():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))

    selected_nodes = []
    wanted_assigns = {"CHAOS_PENDING_ACTIONS"}
    wanted_functions = {
        "_llm_quality_normalize_tool_token",
        "_llm_quality_effective_intent",
        "_llm_quality_is_handoff_effect_meta",
        "_llm_quality_is_timeout_error",
        "_llm_quality_manager_action_error_is_advisory",
        "_llm_quality_expected_manager_state",
        "_llm_quality_should_send_pending_ack",
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
    return namespace


def _load_state_fallback():
    return _load_selected_ops_functions()["_chaos_state_fallback_ok"]


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


def test_state_fallback_allows_handoff_context_pending_state():
    fn = _load_state_fallback()
    assert fn(
        "bot_active",
        "pending",
        {"action": "handoff", "intent": "handoff_context_update", "tool_decision": "handoff"},
        {},
        {"status": "open"},
    )


def test_manager_take_state_is_race_tolerant():
    namespace = _load_selected_ops_functions()
    expected_manager_state = namespace["_llm_quality_expected_manager_state"]
    assert expected_manager_state("take", "pending") == (None, None)
    assert expected_manager_state("resolve", "manager_active") == ("bot_active", "resolved")


def test_manager_take_timeout_is_advisory_when_resolve_follows():
    namespace = _load_selected_ops_functions()
    advisory = namespace["_llm_quality_manager_action_error_is_advisory"]

    assert advisory(
        action="take",
        error="timeout: timed out",
        expected_state=None,
        expected_status=None,
        remaining_actions=["resolve"],
    )
    assert not advisory(
        action="resolve",
        error="timeout: timed out",
        expected_state="bot_active",
        expected_status="resolved",
        remaining_actions=[],
    )


def test_pending_ack_waits_until_no_customer_turn_remains():
    namespace = _load_selected_ops_functions()
    should_ack = namespace["_llm_quality_should_send_pending_ack"]

    assert not should_ack(
        state="pending",
        pending_mode="ack",
        simulate_manager=False,
        has_remaining_customer_turn=True,
    )
    assert should_ack(
        state="pending",
        pending_mode="ack",
        simulate_manager=False,
        has_remaining_customer_turn=False,
    )
