"""CorpusTurn / CorpusDialog schema and JSONL loader tests."""
from __future__ import annotations

import json
import pathlib

import pytest

from app.policy_core_v3.schema import (
    CandidateAction,
    Intent,
    PolicyDecisionV3,
)
from app.policy_core_v3_corpus import CorpusDialog, CorpusTurn, load_corpus_jsonl
from app.policy_core_v3_shadow import LegacySummary


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PILOT_JSONL = REPO_ROOT / "truffles-api" / "tests" / "corpora" / "beauty_salon_pilot_v0.jsonl"


def test_pilot_corpus_loads() -> None:
    dialogs = load_corpus_jsonl(PILOT_JSONL)
    assert len(dialogs) >= 25
    for d in dialogs:
        assert d.dialog_id
        assert d.status == "draft"
        assert d.turns


def test_loader_strict_on_invalid_lines(tmp_path) -> None:
    f = tmp_path / "bad.jsonl"
    f.write_text("not-json\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_corpus_jsonl(f)


def test_loader_skips_comments_and_blanks(tmp_path) -> None:
    payload = {
        "dialog_id": "d1",
        "turns": [
            {
                "turn_index": 0,
                "current_message": "hi",
                "legacy_summary": {"intent": "smalltalk", "action": "reply"},
            }
        ],
    }
    f = tmp_path / "ok.jsonl"
    f.write_text(
        f"# comment\n\n{json.dumps(payload)}\n",
        encoding="utf-8",
    )
    dialogs = load_corpus_jsonl(f)
    assert len(dialogs) == 1
    assert dialogs[0].dialog_id == "d1"


def test_corpus_turn_carries_oracle() -> None:
    t = CorpusTurn(
        turn_index=0,
        current_message="x",
        legacy_summary=LegacySummary(intent="x", action="y"),
        oracle_v3=PolicyDecisionV3(
            intent=Intent.smalltalk,
            candidate_action=CandidateAction(tool="none"),
        ),
    )
    assert t.oracle_v3 is not None
    assert t.oracle_v3.intent == Intent.smalltalk


def test_pilot_corpus_covers_required_intents() -> None:
    dialogs = load_corpus_jsonl(PILOT_JSONL)
    legacy_intents = {t.legacy_summary.intent for d in dialogs for t in d.turns}
    expected_subset = {
        "fact_question",
        "booking_request",
        "cancel_request",
        "complaint",
        "medical",
        "refund",
    }
    assert expected_subset <= legacy_intents, f"missing: {expected_subset - legacy_intents}"
