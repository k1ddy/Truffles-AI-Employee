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


def test_repo_continuity_state_normalization_guard_snapshot_matches_current_repo() -> None:
    module = load_module(
        "continuity_state_normalization_guard",
        SCRIPTS / "continuity_state_normalization_guard.py",
    )
    config = yaml.safe_load(
        (ROOT / "docs" / "CONTINUITY_STATE_NORMALIZATION_GUARD.yaml").read_text(encoding="utf-8")
    )

    assert config["family_id"] == "continuity_state_normalization"
    assert config["expected_current_goal"] == "booking"
    assert config["expected_pending_question_contract"]["expected_reply_type"] == "time"
    assert config["expected_pending_question_contract"]["reason"] == "collect_datetime"
    assert module.evaluate(ROOT, config) == []
