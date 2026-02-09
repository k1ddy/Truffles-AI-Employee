import ast
from pathlib import Path

from app.services.intent_service import route_llm_plan


DECISION_PATH = Path(__file__).resolve().parents[1] / "app" / "routers" / "webhook" / "decision.py"


def _collect_call_names(tree: ast.AST) -> set[str]:
    calls: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            calls.add(node.func.id)
            continue
        if isinstance(node.func, ast.Attribute):
            calls.add(node.func.attr)
    return calls


def _collect_intent_service_imports(tree: ast.AST) -> set[str]:
    imported: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "app.services.intent_service":
            continue
        imported.update(alias.name for alias in node.names)
    return imported


def test_runtime_planner_wiring_keeps_legacy_plan_retired() -> None:
    tree = ast.parse(DECISION_PATH.read_text(encoding="utf-8"))
    calls = _collect_call_names(tree)
    imports = _collect_intent_service_imports(tree)

    assert "route_dialogue_controller" in calls
    assert "route_llm_policy_core" in calls
    assert "route_llm_plan" not in calls
    assert "route_llm_plan" not in imports


def test_route_llm_plan_returns_legacy_retired_error() -> None:
    result = route_llm_plan("hello")

    assert result["ok"] is False
    assert result["attempted"] is False
    assert result["error"] == "legacy_retired_use_policy_core"
