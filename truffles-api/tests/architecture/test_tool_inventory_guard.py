from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GUARD_PATH = ROOT / "scripts" / "tool_inventory_guard.py"


def _load_guard():
    spec = importlib.util.spec_from_file_location("tool_inventory_guard", GUARD_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tool_inventory_guard_passes_current_repo() -> None:
    guard = _load_guard()

    assert guard.collect_inventory_errors(ROOT) == []


def test_tool_inventory_guard_requires_registered_scripts(tmp_path: Path) -> None:
    guard = _load_guard()
    repo = tmp_path
    scripts_dir = repo / "scripts"
    tests_dir = repo / "truffles-api" / "tests" / "architecture"
    scripts_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)
    (repo / "TECH.md").write_text(
        "Business capability -> architecture layer -> inventory lookup -> decision record -> implementation -> proof -> impacted docs/inventory update\n"
        "new development tool, script, architecture test, runtime worker, router, provider adapter, or external dependency\n",
        encoding="utf-8",
    )
    (repo / "STRUCTURE.md").write_text("", encoding="utf-8")
    (scripts_dir / "new_probe.py").write_text("print('probe')\n", encoding="utf-8")
    (tests_dir / "test_new_probe.py").write_text("def test_probe(): pass\n", encoding="utf-8")

    errors = guard.collect_inventory_errors(repo)

    assert "missing scripts inventory entry: scripts/new_probe.py" in errors
    assert (
        "missing architecture-test inventory entry: "
        "truffles-api/tests/architecture/test_new_probe.py"
    ) in errors
