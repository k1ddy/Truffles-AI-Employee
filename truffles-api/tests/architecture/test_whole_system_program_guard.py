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


def test_whole_system_program_guard_aligns_active_docs_to_whole_system_reset() -> None:
    guard = _load_module('whole_system_program_guard', SCRIPTS / 'whole_system_program_guard.py')
    assert guard.collect_errors(ROOT) == []
