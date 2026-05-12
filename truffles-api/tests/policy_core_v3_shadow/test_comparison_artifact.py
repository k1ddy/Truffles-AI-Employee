"""ComparisonRecord and InMemoryArtifactSink tests."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.policy_core_v3_shadow import (
    ArtifactSink,
    ComparisonRecord,
    InMemoryArtifactSink,
    LegacySummary,
)


def _record(**overrides) -> ComparisonRecord:
    base = dict(
        tenant_id="t",
        conversation_id="c",
        turn_index=0,
        current_message="m",
        legacy_summary=LegacySummary(intent="smalltalk", action="reply"),
        v3_outcome_kind="decision",
        v3_decision={"intent": "smalltalk"},
        v3_degrade=None,
        v3_latency_ms=12.5,
        v3_attempts=1,
        policy_version="v3-shadow",
        pack_id="x",
        pack_version=1,
    )
    base.update(overrides)
    return ComparisonRecord(**base)


def test_record_minimal_valid() -> None:
    r = _record()
    assert r.v3_outcome_kind == "decision"
    assert r.v3_decision == {"intent": "smalltalk"}


def test_record_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ComparisonRecord.model_validate(
            {**_record().model_dump(), "weird": True}
        )


def test_record_rejects_negative_latency() -> None:
    with pytest.raises(ValidationError):
        _record(v3_latency_ms=-1.0)


@pytest.mark.asyncio
async def test_in_memory_sink_collects() -> None:
    sink = InMemoryArtifactSink()
    assert isinstance(sink, ArtifactSink)
    rec = _record()
    await sink.emit(rec)
    await sink.emit(rec)
    assert len(sink.records) == 2
    assert sink.records[0] is rec
