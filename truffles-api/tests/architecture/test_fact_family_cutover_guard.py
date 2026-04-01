from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repo_fact_family_cutover_guard_snapshot_matches_current_repo() -> None:
    module = load_module("fact_family_cutover_guard", SCRIPTS / "fact_family_cutover_guard.py")
    config = yaml.safe_load((ROOT / "docs" / "FACT_FAMILY_CUTOVER_GUARD.yaml").read_text(encoding="utf-8"))

    assert config["family_id"] == "location_hours_parking"
    assert config["target_family_fact_refs"] == ["location", "hours", "parking"]
    assert config["expected_runtime_tool_action"] == "catalog.location"
    assert module.evaluate(ROOT, config) == []
