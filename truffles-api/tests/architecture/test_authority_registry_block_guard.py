from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / 'scripts'


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_authority_registry_block_guard_keeps_block2_governance_honest() -> None:
    guard = _load_module('authority_registry_block_guard', SCRIPTS / 'authority_registry_block_guard.py')
    assert guard.collect_errors(ROOT) == []
