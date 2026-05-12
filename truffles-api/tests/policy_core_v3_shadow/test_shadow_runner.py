"""Shadow runner tests: never raises, emits a typed record."""
from __future__ import annotations

import json

import pytest

from app.policy_core_v3 import PolicyCoreV3Invoker
from app.policy_core_v3.invoker import LLMProviderError
from app.policy_core_v3_shadow import (
    InMemoryArtifactSink,
    LegacySummary,
    run_shadow,
)


def _good_decision_json() -> str:
    return json.dumps(
        {
            "intent": "booking_request",
            "slots": {"service_id": "brows"},
            "candidate_action": {"tool": "none", "args": {}},
            "evidence_refs": ["ev-1"],
            "message_draft": "Подскажите имя.",
            "uncertainty": "low",
            "notes": "",
        }
    )


@pytest.mark.asyncio
async def test_happy_path_emits_decision_record(legacy_ctx, legacy_summary) -> None:
    async def llm(prompt: str) -> str:
        return _good_decision_json()

    sink = InMemoryArtifactSink()
    rec = await run_shadow(
        ctx=legacy_ctx,
        legacy_summary=legacy_summary,
        invoker=PolicyCoreV3Invoker(llm),
        sink=sink,
        turn_index=3,
    )
    assert rec.v3_outcome_kind == "decision"
    assert rec.v3_decision is not None
    assert rec.v3_degrade is None
    assert rec.tenant_id == legacy_ctx.tenant_id
    assert rec.pack_id == legacy_ctx.pack.pack_id
    assert rec.pack_version == legacy_ctx.pack.pack_version
    assert rec.turn_index == 3
    assert rec.v3_latency_ms >= 0.0
    assert sink.records == [rec]


@pytest.mark.asyncio
async def test_two_empty_responses_emit_degrade_record(legacy_ctx, legacy_summary) -> None:
    async def llm(prompt: str) -> str:
        return ""

    sink = InMemoryArtifactSink()
    rec = await run_shadow(
        ctx=legacy_ctx,
        legacy_summary=legacy_summary,
        invoker=PolicyCoreV3Invoker(llm),
        sink=sink,
    )
    assert rec.v3_outcome_kind == "degrade"
    assert rec.v3_decision is None
    assert rec.v3_degrade is not None
    assert rec.v3_degrade["degrade_reason"] == "empty_response"
    assert rec.v3_attempts == 2


@pytest.mark.asyncio
async def test_provider_error_in_invoker_emits_degrade(legacy_ctx, legacy_summary) -> None:
    async def llm(prompt: str) -> str:
        raise LLMProviderError("upstream")

    sink = InMemoryArtifactSink()
    rec = await run_shadow(
        ctx=legacy_ctx,
        legacy_summary=legacy_summary,
        invoker=PolicyCoreV3Invoker(llm),
        sink=sink,
    )
    assert rec.v3_outcome_kind == "degrade"
    assert rec.v3_degrade["degrade_reason"] == "provider_error"


@pytest.mark.asyncio
async def test_runner_never_raises_even_on_internal_failure(
    legacy_ctx, legacy_summary
) -> None:
    """A broken invoker that raises on .invoke() must not propagate."""

    class _BoomInvoker:
        async def invoke(self, _):
            raise RuntimeError("internal bug")

    sink = InMemoryArtifactSink()
    rec = await run_shadow(
        ctx=legacy_ctx,
        legacy_summary=legacy_summary,
        invoker=_BoomInvoker(),  # type: ignore[arg-type]
        sink=sink,
    )
    assert rec.v3_outcome_kind == "degrade"
    assert rec.v3_degrade["degrade_reason"] == "provider_error"
    assert "shadow_runner_exception" in rec.v3_degrade["notes"]
    assert "internal bug" in rec.notes


@pytest.mark.asyncio
async def test_sink_failure_is_swallowed(legacy_ctx, legacy_summary) -> None:
    """Sink errors must not affect callers — shadow path is never blocking."""

    class _BadSink:
        async def emit(self, record):
            raise RuntimeError("disk full")

    async def llm(prompt: str) -> str:
        return _good_decision_json()

    rec = await run_shadow(
        ctx=legacy_ctx,
        legacy_summary=legacy_summary,
        invoker=PolicyCoreV3Invoker(llm),
        sink=_BadSink(),
    )
    assert rec.v3_outcome_kind == "decision"


@pytest.mark.asyncio
async def test_legacy_summary_is_preserved(legacy_ctx) -> None:
    summary = LegacySummary(
        intent="booking_request",
        action="collect",
        tool_action="calendar.list_slots",
        message_text="Имя?",
        rescue_flag=True,
        policy_core_degrade=False,
        extras={"raw_thing": [1, 2, 3]},
    )

    async def llm(prompt: str) -> str:
        return _good_decision_json()

    sink = InMemoryArtifactSink()
    rec = await run_shadow(
        ctx=legacy_ctx,
        legacy_summary=summary,
        invoker=PolicyCoreV3Invoker(llm),
        sink=sink,
    )
    assert rec.legacy_summary == summary
    assert rec.legacy_summary.rescue_flag is True
    assert rec.legacy_summary.extras == {"raw_thing": [1, 2, 3]}


@pytest.mark.asyncio
async def test_runner_attaches_divergence(legacy_ctx, legacy_summary) -> None:
    async def llm(prompt: str) -> str:
        return _good_decision_json()

    sink = InMemoryArtifactSink()
    rec = await run_shadow(
        ctx=legacy_ctx,
        legacy_summary=legacy_summary,
        invoker=PolicyCoreV3Invoker(llm),
        sink=sink,
    )
    assert rec.divergence is not None
    assert rec.divergence.legacy_intent == legacy_summary.intent
    assert rec.divergence.v3_intent == "booking_request"
    assert rec.divergence.intent_match is True
    assert "intent_match" in rec.divergence.flags
    assert "tool_action_mismatch" in rec.divergence.flags  # legacy=list_slots, v3=none


@pytest.mark.asyncio
async def test_runner_divergence_for_v3_degrade(legacy_ctx, legacy_summary) -> None:
    async def llm(prompt: str) -> str:
        return ""

    sink = InMemoryArtifactSink()
    rec = await run_shadow(
        ctx=legacy_ctx,
        legacy_summary=legacy_summary,
        invoker=PolicyCoreV3Invoker(llm),
        sink=sink,
    )
    assert rec.divergence is not None
    assert rec.divergence.v3_degraded is True
    assert "v3_degrade" in rec.divergence.flags
    assert "legacy_decision_while_v3_degrade" in rec.divergence.flags
    assert rec.divergence.intent_match is False
