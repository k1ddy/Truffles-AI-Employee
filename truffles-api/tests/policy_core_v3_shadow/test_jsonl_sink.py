"""JsonlArtifactSink tests."""
from __future__ import annotations

import asyncio
import json

import pytest

from app.policy_core_v3_shadow import (
    ArtifactSink,
    ComparisonRecord,
    JsonlArtifactSink,
    LegacySummary,
)


def _record(turn_index: int = 0, message: str = "m") -> ComparisonRecord:
    return ComparisonRecord(
        tenant_id="t",
        conversation_id="c",
        turn_index=turn_index,
        current_message=message,
        legacy_summary=LegacySummary(intent="x", action="y"),
        v3_outcome_kind="decision",
        v3_decision={"intent": "x"},
        v3_degrade=None,
        v3_latency_ms=1.0,
        v3_attempts=1,
        policy_version="v3-shadow",
        pack_id="p",
        pack_version=1,
    )


@pytest.mark.asyncio
async def test_satisfies_artifact_sink_protocol(tmp_path) -> None:
    sink = JsonlArtifactSink(tmp_path / "shadow.jsonl")
    assert isinstance(sink, ArtifactSink)


@pytest.mark.asyncio
async def test_creates_parent_dir(tmp_path) -> None:
    target = tmp_path / "deep" / "nested" / "shadow.jsonl"
    sink = JsonlArtifactSink(target)
    await sink.emit(_record())
    assert target.exists()
    assert target.read_text(encoding="utf-8").strip() != ""


@pytest.mark.asyncio
async def test_appends_one_line_per_record(tmp_path) -> None:
    target = tmp_path / "shadow.jsonl"
    sink = JsonlArtifactSink(target)
    await sink.emit(_record(turn_index=0))
    await sink.emit(_record(turn_index=1))
    await sink.emit(_record(turn_index=2))
    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    parsed = [json.loads(line) for line in lines]
    assert [p["turn_index"] for p in parsed] == [0, 1, 2]


@pytest.mark.asyncio
async def test_each_line_is_valid_json(tmp_path) -> None:
    target = tmp_path / "shadow.jsonl"
    sink = JsonlArtifactSink(target)
    await sink.emit(_record(message="можно завтра в 6 вечера на брови"))
    line = target.read_text(encoding="utf-8").strip()
    payload = json.loads(line)
    assert payload["current_message"] == "можно завтра в 6 вечера на брови"


@pytest.mark.asyncio
async def test_concurrent_emit_writes_serialized_lines(tmp_path) -> None:
    """Lock must prevent interleaved writes from corrupting JSONL."""
    target = tmp_path / "shadow.jsonl"
    sink = JsonlArtifactSink(target)
    await asyncio.gather(*(sink.emit(_record(turn_index=i)) for i in range(50)))
    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 50
    indices = sorted(json.loads(line)["turn_index"] for line in lines)
    assert indices == list(range(50))


@pytest.mark.asyncio
async def test_path_property(tmp_path) -> None:
    target = tmp_path / "x.jsonl"
    sink = JsonlArtifactSink(target)
    assert sink.path == target
