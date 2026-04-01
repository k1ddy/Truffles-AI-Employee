from __future__ import annotations

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


def test_shadow_lane_elimination_runtime_files_are_removed_locally() -> None:
    module = load_module("shadow_lane_elimination_guard", SCRIPTS / "shadow_lane_elimination_guard.py")

    assert module.evaluate_removed_shadow_lanes(ROOT) == []


def test_shadow_lane_elimination_guard_aligns_active_docs_when_block_is_active() -> None:
    module = load_module("shadow_lane_elimination_guard", SCRIPTS / "shadow_lane_elimination_guard.py")

    assert module.collect_errors(ROOT) == []
