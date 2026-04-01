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


def test_repo_touched_slice_continuity_guard_snapshot_matches_current_repo() -> None:
    module = load_module("touched_slice_continuity_guard", SCRIPTS / "touched_slice_continuity_guard.py")
    config = yaml.safe_load((ROOT / "docs" / "TOUCHED_SLICE_CONTINUITY_GUARD.yaml").read_text(encoding="utf-8"))

    assert config["family_id"] == "location_hours_parking"
    assert config["expected_class_name"] == "info_bundle"
    assert config["expected_info_sections"] == ["address", "hours"]
    assert config["expected_intents"] == ["location", "hours"]
    assert module.evaluate(ROOT, config) == []
