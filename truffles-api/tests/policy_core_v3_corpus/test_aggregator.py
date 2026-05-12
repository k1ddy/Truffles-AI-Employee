"""Aggregator tests — pure logic on synthetic ComparisonRecord lists."""
from __future__ import annotations

import json

from app.policy_core_v3_corpus import (
    aggregate_jsonl_file,
    aggregate_records,
    format_report_text,
)
from app.policy_core_v3_shadow import (
    ComparisonRecord,
    Divergence,
    LegacySummary,
)


def _make_record(
    dialog_id: str,
    *,
    flags: list[str],
    latency: float = 1.0,
    v3_outcome: str = "decision",
) -> ComparisonRecord:
    div = Divergence(
        intent_match="intent_match" in flags,
        legacy_intent="x",
        v3_intent="x" if "intent_match" in flags else None,
        v3_degraded="v3_degrade" in flags,
        legacy_rescue="legacy_rescue" in flags,
        legacy_degrade="legacy_degrade" in flags,
        legacy_tool_action=None,
        v3_tool=None,
        flags=flags,
    )
    return ComparisonRecord(
        tenant_id="t",
        conversation_id=dialog_id,
        turn_index=0,
        current_message="m",
        legacy_summary=LegacySummary(intent="x", action="y"),
        v3_outcome_kind=v3_outcome,
        v3_decision=None if v3_outcome == "degrade" else {"intent": "x"},
        v3_degrade=None if v3_outcome != "degrade" else {"degrade_reason": "empty_response"},
        v3_latency_ms=latency,
        v3_attempts=1,
        divergence=div,
        policy_version="v",
        pack_id="p",
        pack_version=1,
    )


def test_aggregate_empty() -> None:
    r = aggregate_records([])
    assert r.total_records == 0
    assert r.intent_match_rate == 0.0
    assert r.flag_counts == {}


def test_aggregate_basic_match_rate() -> None:
    records = [
        _make_record("d1", flags=["intent_match"]),
        _make_record("d1", flags=["intent_match"]),
        _make_record("d2", flags=["intent_mismatch"]),
        _make_record("d2", flags=["v3_degrade", "legacy_decision_while_v3_degrade"], v3_outcome="degrade"),
    ]
    r = aggregate_records(records)
    assert r.total_records == 4
    assert r.dialogs_seen == 2
    assert r.intent_match_rate == 0.5
    assert r.intent_mismatch_rate == 0.25
    assert r.v3_degrade_rate == 0.25
    assert r.flag_counts["intent_match"] == 2
    assert r.flag_counts["v3_degrade"] == 1


def test_aggregate_latency_percentiles() -> None:
    records = [
        _make_record("d1", flags=["intent_match"], latency=10.0),
        _make_record("d1", flags=["intent_match"], latency=20.0),
        _make_record("d1", flags=["intent_match"], latency=30.0),
        _make_record("d1", flags=["intent_match"], latency=40.0),
        _make_record("d1", flags=["intent_match"], latency=100.0),
    ]
    r = aggregate_records(records)
    assert r.latency_ms_max == 100.0
    assert 30.0 - 1e-6 <= r.latency_ms_p50 <= 30.0 + 1e-6
    assert r.latency_ms_p95 >= r.latency_ms_p50


def test_aggregate_jsonl_file(tmp_path) -> None:
    f = tmp_path / "x.jsonl"
    rec = _make_record("d1", flags=["intent_match"])
    line = json.dumps(rec.model_dump(mode="json"), ensure_ascii=False)
    f.write_text(line + "\n", encoding="utf-8")
    r = aggregate_jsonl_file(f)
    assert r.total_records == 1
    assert r.intent_match_rate == 1.0


def test_format_report_text_contains_key_lines() -> None:
    records = [_make_record("d1", flags=["intent_match"])]
    r = aggregate_records(records)
    text = format_report_text(r)
    assert "intent_match_rate" in text
    assert "latency_ms_p50" in text
    assert "intent_match: 1" in text
