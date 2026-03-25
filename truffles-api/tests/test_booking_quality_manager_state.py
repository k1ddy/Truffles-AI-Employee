import ast
from pathlib import Path


def _load_expected_manager_state():
    script_path = Path(__file__).resolve().parents[2] / "ops" / "diagnose.py"
    source = script_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(script_path))

    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_llm_quality_expected_manager_state":
            selected_nodes.append(node)

    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {}
    exec(compile(module, str(script_path), "exec"), namespace, namespace)
    return namespace["_llm_quality_expected_manager_state"]


def test_expected_manager_state_take_skips_status_lock():
    fn = _load_expected_manager_state()
    expected_state, expected_status = fn("take", "pending")
    assert expected_state is None
    assert expected_status is None
