import ast
from pathlib import Path


def _load_progress_gate():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))
    wanted_assignments = {
        "CHAOS_BOOKING_REPLY_TYPES",
        "LLM_QUALITY_PROGRESS_TAGS_BY_REPLY_TYPE",
        "LLM_QUALITY_PROGRESS_SKIP_TAGS",
    }
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            if names & wanted_assignments:
                selected_nodes.append(node)
        if isinstance(node, ast.FunctionDef) and node.name == "_llm_quality_should_expect_booking_progress":
            selected_nodes.append(node)
    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace["_llm_quality_should_expect_booking_progress"]


_should_expect_progress = _load_progress_gate()


def test_progress_gate_ignores_generic_booking_tag_for_service_choice():
    assert _should_expect_progress("service_choice", ["booking"]) is False
    assert _should_expect_progress("service_choice", ["service"]) is True


def test_progress_gate_time_requires_time_or_date_signal():
    assert _should_expect_progress("time", ["booking"]) is False
    assert _should_expect_progress("time", ["date"]) is True


def test_progress_gate_keeps_no_tag_fallback():
    assert _should_expect_progress("time", []) is True
