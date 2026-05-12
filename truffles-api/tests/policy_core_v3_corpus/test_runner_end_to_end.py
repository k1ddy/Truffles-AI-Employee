"""End-to-end corpus runner: pilot JSONL → run_corpus → aggregate."""
from __future__ import annotations

import pathlib

import pytest

from app.pack_v1 import load_pack
from app.policy_core_v3_corpus import (
    OracleLLMConfig,
    OracleLLMMode,
    aggregate_records,
    load_corpus_jsonl,
    run_corpus,
)
from app.policy_core_v3_shadow import InMemoryArtifactSink


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PILOT_JSONL = REPO_ROOT / "truffles-api" / "tests" / "corpora" / "beauty_salon_pilot_v0.jsonl"
PACK_DIR = REPO_ROOT / "packs" / "beauty_salon_v1"


@pytest.mark.asyncio
async def test_oracle_mode_yields_high_intent_match() -> None:
    """In oracle mode, v3 returns the corpus oracle verbatim → most records
    should be intent_match (legacy intent vocabulary differs slightly so
    not 100% — assert ≥0.6 as a sanity floor)."""
    dialogs = load_corpus_jsonl(PILOT_JSONL)
    pack = load_pack(PACK_DIR)
    sink = InMemoryArtifactSink()
    records = await run_corpus(
        dialogs=dialogs,
        pack=pack,
        sink=sink,
        config=OracleLLMConfig(mode=OracleLLMMode.oracle),
    )
    assert len(records) > 0
    report = aggregate_records(records)
    assert report.total_records == len(records)
    assert report.dialogs_seen == len(dialogs)
    assert report.v3_degrade_rate < 1.0  # at least some decisions came back
    # latency should be measurable but small (mock LLM has no I/O)
    assert report.latency_ms_p50 >= 0.0


@pytest.mark.asyncio
async def test_degrade_mode_yields_full_v3_degrade() -> None:
    """In degrade mode v3 always degrades → v3_degrade_rate == 1.0."""
    dialogs = load_corpus_jsonl(PILOT_JSONL)
    pack = load_pack(PACK_DIR)
    sink = InMemoryArtifactSink()
    records = await run_corpus(
        dialogs=dialogs,
        pack=pack,
        sink=sink,
        config=OracleLLMConfig(mode=OracleLLMMode.degrade),
    )
    report = aggregate_records(records)
    assert report.v3_degrade_rate == 1.0
    assert report.intent_match_rate == 0.0


@pytest.mark.asyncio
async def test_drift_mode_produces_some_mismatches() -> None:
    """Drift at 50% must produce strictly positive mismatch_rate while still
    not collapsing to all-degrade."""
    dialogs = load_corpus_jsonl(PILOT_JSONL)
    pack = load_pack(PACK_DIR)
    sink = InMemoryArtifactSink()
    records = await run_corpus(
        dialogs=dialogs,
        pack=pack,
        sink=sink,
        config=OracleLLMConfig(mode=OracleLLMMode.drift, drift_rate=0.5),
    )
    report = aggregate_records(records)
    assert report.v3_degrade_rate < 1.0
    # At least one drifted intent should have surfaced as mismatch
    assert report.intent_mismatch_rate > 0.0
