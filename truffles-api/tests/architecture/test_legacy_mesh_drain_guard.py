from __future__ import annotations

import ast
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_legacy_mesh_drain_topology_is_green() -> None:
    module = load_module("legacy_mesh_drain_guard", SCRIPTS / "legacy_mesh_drain_guard.py")
    assert module.collect_topology_errors(ROOT) == []


def test_webhook_package_init_routes_info_interrupt_helper_through_runtime_module() -> None:
    init_path = ROOT / "truffles-api" / "app" / "routers" / "webhook" / "__init__.py"
    text = init_path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(init_path))

    assert "app.routers.webhook.expected_reply_interrupt_runtime" in text
    assert "app.routers.webhook.decision" not in text

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "app.routers.webhook.decision"
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "") != "app.routers.webhook.decision"


def test_app_runtime_decision_importers_shrink_to_legacy_only() -> None:
    module = load_module("legacy_mesh_drain_guard", SCRIPTS / "legacy_mesh_drain_guard.py")
    app_root = ROOT / "truffles-api" / "app"
    direct = module._collect_importers(
        search_root=app_root,
        target_module="app.routers.webhook.decision",
    )
    via_package = module._collect_importers(
        search_root=app_root,
        target_module="app.routers.webhook",
        target_member="decision",
    )
    assert sorted(set(direct + via_package)) == ["truffles-api/app/routers/webhook/_legacy.py"]
