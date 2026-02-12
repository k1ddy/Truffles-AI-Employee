import ast
from pathlib import Path


def _load_extract_expectations():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))

    wanted_assigns = {
        "LLM_QUALITY_EXPECT_ACTION_HANDOFF",
        "LLM_QUALITY_EXPECT_TAGS_ALLOW_PENDING",
        "LLM_QUALITY_EXPECT_TAGS_ALLOW_MANAGER_ACTIVE",
        "LLM_QUALITY_INFO_TAGS",
        "LLM_QUALITY_EXPECT_INFO_TAGS",
    }
    wanted_functions = {
        "_llm_quality_normalize_expect_token",
        "_llm_quality_normalize_expect_value",
        "_llm_quality_collect_turn_tags",
        "_llm_quality_sanitize_expect_action_by_tags",
        "_llm_quality_sanitize_expect_state_by_tags",
        "_llm_quality_sanitize_expect_info_sections_by_tags",
        "_llm_quality_extract_expectations",
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
    return namespace["_llm_quality_extract_expectations"]


def test_extract_expectations_strips_handoff_action_for_booking_turn():
    fn = _load_extract_expectations()
    expect = fn(
        {
            "tags": ["booking"],
            "expect": {"action": ["booking_escalated"], "reply_type": "time"},
        }
    )
    assert expect["action"] is None


def test_extract_expectations_keeps_handoff_action_for_handoff_turn():
    fn = _load_extract_expectations()
    expect = fn(
        {
            "tags": ["handoff"],
            "expect": {"action": ["booking_escalated"], "reply_type": "time"},
        }
    )
    assert expect["action"] == "booking_escalated"


def test_extract_expectations_strips_pending_state_without_handoff_tags():
    fn = _load_extract_expectations()
    expect = fn(
        {
            "tags": ["booking"],
            "expect": {"state": ["pending", "bot_active"], "reply_type": "time"},
        }
    )
    assert expect["state"] == "bot_active"


def test_extract_expectations_drops_info_sections_without_info_tags():
    fn = _load_extract_expectations()
    expect = fn(
        {
            "tags": ["booking"],
            "expect": {"info_sections": ["service_duration"], "reply_type": "time"},
        }
    )
    assert expect["info_sections"] == []
