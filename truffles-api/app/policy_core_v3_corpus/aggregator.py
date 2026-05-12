"""ComparisonRecord JSONL → histogram report.

Spec: SPECS/SHADOW_RUN_V3.md (Phase B.3 acceptance — divergence histograms).

Pure: no I/O beyond reading the JSONL file in `aggregate_jsonl_file`.
"""
from __future__ import annotations

import json
import math
import pathlib
from collections import Counter
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field

from app.policy_core_v3.schema import (
    CandidateAction,
    DegradeVerdict,
    Intent,
    PolicyDecisionV3,
    Uncertainty,
)
from app.policy_core_v3_shadow import ComparisonRecord, LegacySummary

from .intent_vocabulary import semantic_match


class CorpusAggregateReport(BaseModel):
    """Output of one aggregation pass over a JSONL of ComparisonRecord."""

    model_config = ConfigDict(extra="forbid")

    total_records: int
    dialogs_seen: int
    intent_match_rate: float
    semantic_match_rate: float
    intent_mismatch_rate: float
    v3_degrade_rate: float
    legacy_degrade_rate: float
    both_degrade_rate: float
    tool_match_rate: float
    tool_mismatch_rate: float
    legacy_rescue_rate: float
    high_uncertainty_rate: float
    flag_counts: dict[str, int] = Field(default_factory=dict)
    latency_ms_p50: float
    latency_ms_p95: float
    latency_ms_max: float
    by_dialog_record_counts: dict[str, int] = Field(default_factory=dict)


def _safe_div(num: int, den: int) -> float:
    return (num / den) if den else 0.0


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * pct
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return sorted_values[int(k)]
    frac = k - lo
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


def aggregate_records(records: Iterable[ComparisonRecord]) -> CorpusAggregateReport:
    """Aggregate an iterable of ComparisonRecord into a histogram report."""
    rec_list = list(records)
    n = len(rec_list)
    if n == 0:
        return CorpusAggregateReport(
            total_records=0,
            dialogs_seen=0,
            intent_match_rate=0.0,
            semantic_match_rate=0.0,
            intent_mismatch_rate=0.0,
            v3_degrade_rate=0.0,
            legacy_degrade_rate=0.0,
            both_degrade_rate=0.0,
            tool_match_rate=0.0,
            tool_mismatch_rate=0.0,
            legacy_rescue_rate=0.0,
            high_uncertainty_rate=0.0,
            flag_counts={},
            latency_ms_p50=0.0,
            latency_ms_p95=0.0,
            latency_ms_max=0.0,
            by_dialog_record_counts={},
        )

    intent_match = 0
    semantic_match_count = 0
    intent_mismatch = 0
    v3_degrade = 0
    legacy_degrade = 0
    both_degrade = 0
    tool_match = 0
    tool_mismatch = 0
    legacy_rescue = 0
    high_uncertainty = 0
    flag_counter: Counter[str] = Counter()
    latencies: list[float] = []
    by_dialog: Counter[str] = Counter()

    for rec in rec_list:
        by_dialog[rec.conversation_id] += 1
        latencies.append(rec.v3_latency_ms)
        # Reconstruct typed v3 outcome to feed semantic_match.
        v3_outcome = _rebuild_v3_outcome(rec)
        if v3_outcome is not None and semantic_match(rec.legacy_summary, v3_outcome):
            semantic_match_count += 1
        d = rec.divergence
        if d is None:
            continue
        flag_counter.update(d.flags)
        if "intent_match" in d.flags:
            intent_match += 1
        if "intent_mismatch" in d.flags:
            intent_mismatch += 1
        if "v3_degrade" in d.flags:
            v3_degrade += 1
        if "legacy_degrade" in d.flags:
            legacy_degrade += 1
        if "both_degrade" in d.flags:
            both_degrade += 1
        if "tool_action_match" in d.flags:
            tool_match += 1
        if "tool_action_mismatch" in d.flags:
            tool_mismatch += 1
        if "legacy_rescue" in d.flags:
            legacy_rescue += 1
        if "high_uncertainty" in d.flags:
            high_uncertainty += 1

    latencies.sort()
    return CorpusAggregateReport(
        total_records=n,
        dialogs_seen=len(by_dialog),
        intent_match_rate=_safe_div(intent_match, n),
        semantic_match_rate=_safe_div(semantic_match_count, n),
        intent_mismatch_rate=_safe_div(intent_mismatch, n),
        v3_degrade_rate=_safe_div(v3_degrade, n),
        legacy_degrade_rate=_safe_div(legacy_degrade, n),
        both_degrade_rate=_safe_div(both_degrade, n),
        tool_match_rate=_safe_div(tool_match, n),
        tool_mismatch_rate=_safe_div(tool_mismatch, n),
        legacy_rescue_rate=_safe_div(legacy_rescue, n),
        high_uncertainty_rate=_safe_div(high_uncertainty, n),
        flag_counts=dict(flag_counter.most_common()),
        latency_ms_p50=_percentile(latencies, 0.50),
        latency_ms_p95=_percentile(latencies, 0.95),
        latency_ms_max=latencies[-1] if latencies else 0.0,
        by_dialog_record_counts=dict(by_dialog),
    )


def _rebuild_v3_outcome(
    rec: ComparisonRecord,
) -> PolicyDecisionV3 | DegradeVerdict | None:
    """Reconstruct the typed v3 outcome from the JSON-dump fields in a record."""
    if rec.v3_outcome_kind == "decision" and rec.v3_decision is not None:
        try:
            return PolicyDecisionV3.model_validate(rec.v3_decision)
        except Exception:
            return None
    if rec.v3_outcome_kind == "degrade" and rec.v3_degrade is not None:
        try:
            return DegradeVerdict.model_validate(rec.v3_degrade)
        except Exception:
            return None
    return None


def aggregate_jsonl_file(path: pathlib.Path | str) -> CorpusAggregateReport:
    """Read JSONL of ComparisonRecord and aggregate."""
    p = pathlib.Path(path)
    records: list[ComparisonRecord] = []
    with p.open("r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            payload = json.loads(line)
            records.append(ComparisonRecord.model_validate(payload))
    return aggregate_records(records)


def format_report_text(report: CorpusAggregateReport) -> str:
    """Human-readable text rendering of the report (for stdout)."""
    lines = [
        "=== Policy-Core v3 shadow-run aggregate ===",
        f"total_records:            {report.total_records}",
        f"dialogs_seen:             {report.dialogs_seen}",
        f"intent_match_rate:        {report.intent_match_rate:.3f}",
        f"semantic_match_rate:      {report.semantic_match_rate:.3f}",
        f"intent_mismatch_rate:     {report.intent_mismatch_rate:.3f}",
        f"v3_degrade_rate:          {report.v3_degrade_rate:.3f}",
        f"legacy_degrade_rate:      {report.legacy_degrade_rate:.3f}",
        f"both_degrade_rate:        {report.both_degrade_rate:.3f}",
        f"tool_match_rate:          {report.tool_match_rate:.3f}",
        f"tool_mismatch_rate:       {report.tool_mismatch_rate:.3f}",
        f"legacy_rescue_rate:       {report.legacy_rescue_rate:.3f}",
        f"high_uncertainty_rate:    {report.high_uncertainty_rate:.3f}",
        f"latency_ms_p50/p95/max:   {report.latency_ms_p50:.2f} / {report.latency_ms_p95:.2f} / {report.latency_ms_max:.2f}",
        "--- flags ---",
    ]
    for flag, count in report.flag_counts.items():
        lines.append(f"  {flag}: {count}")
    return "\n".join(lines)
