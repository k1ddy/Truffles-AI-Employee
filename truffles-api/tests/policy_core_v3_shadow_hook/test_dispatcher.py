"""Dispatcher tests for policy_core_v3_shadow_hook.

The dispatcher must:
- never raise into the caller
- be a no-op when wiring is incomplete
- schedule a shadow-run task when wiring is complete and an event loop is
  running, producing a JSONL line
"""
from __future__ import annotations

import asyncio
import json
import pathlib
from dataclasses import dataclass

import pytest

from app.policy_core_v3_shadow_hook import dispatcher, wiring


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
EXAMPLE_PACK = REPO_ROOT / "packs" / "beauty_salon_v1"


@dataclass
class _LegacyDecision:
    intent: str = "booking_request"
    action: str = "collect"
    tool_action: str | None = "calendar.list_slots"
    message_text: str = "Подскажите имя."
    rescue: bool = False
    policy_core_degrade: bool = False


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    monkeypatch.delenv("POLICY_CORE_V3_SHADOW_PACK_PATH", raising=False)
    monkeypatch.delenv("POLICY_CORE_V3_SHADOW_JSONL_PATH", raising=False)
    monkeypatch.delenv("POLICY_CORE_V3_SHADOW_USE_LLM", raising=False)
    wiring.reset_singletons()
    yield
    wiring.reset_singletons()


def test_dispatch_outside_event_loop_is_safe() -> None:
    """No event loop running → dispatcher returns silently, no exception."""
    dispatcher.dispatch_fire_and_forget(
        tenant_id="t",
        conversation_id="c",
        current_message="hi",
        legacy_decision=_LegacyDecision(),
    )


@pytest.mark.asyncio
async def test_dispatch_with_no_env_is_no_op() -> None:
    """Inside an event loop but with no wiring → silent no-op."""
    dispatcher.dispatch_fire_and_forget(
        tenant_id="t",
        conversation_id="c",
        current_message="hi",
        legacy_decision=_LegacyDecision(),
    )
    # nothing to assert beyond "no exception"


@pytest.mark.asyncio
async def test_dispatch_swallows_exceptions_from_broken_decision() -> None:
    """Even with a misshapen `legacy_decision`, dispatcher must not raise."""

    class _Broken:
        @property
        def intent(self):
            raise RuntimeError("boom")

    dispatcher.dispatch_fire_and_forget(
        tenant_id="t",
        conversation_id="c",
        current_message="hi",
        legacy_decision=_Broken(),
    )


@pytest.mark.asyncio
async def test_dispatch_writes_jsonl_when_fully_wired(monkeypatch, tmp_path) -> None:
    target = tmp_path / "shadow.jsonl"
    monkeypatch.setenv("POLICY_CORE_V3_SHADOW_PACK_PATH", str(EXAMPLE_PACK))
    monkeypatch.setenv("POLICY_CORE_V3_SHADOW_JSONL_PATH", str(target))
    # default mock LLM produces an unknown intent → degrade after retries
    wiring.reset_singletons()

    dispatcher.dispatch_fire_and_forget(
        tenant_id="t1",
        conversation_id="c1",
        current_message="можно завтра в 6 вечера на брови",
        legacy_decision=_LegacyDecision(),
        turn_index=5,
    )

    # Wait for the scheduled task to complete. asyncio doesn't expose it
    # directly, so drain the loop until the file appears or timeout.
    deadline = asyncio.get_event_loop().time() + 2.0
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(0.02)
        if target.exists() and target.read_text(encoding="utf-8").strip():
            break

    assert target.exists(), "shadow JSONL file was not created"
    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1, f"expected exactly one record, got {lines!r}"
    record = json.loads(lines[0])
    assert record["tenant_id"] == "t1"
    assert record["conversation_id"] == "c1"
    assert record["turn_index"] == 5
    assert record["pack_id"] == "beauty_salon_v1"
    assert record["legacy_summary"]["intent"] == "booking_request"
    assert record["divergence"] is not None
    # mock returns an out-of-enum intent → v3 degrades after retries
    assert record["v3_outcome_kind"] == "degrade"
    assert record["divergence"]["v3_degraded"] is True
    assert "v3_degrade" in record["divergence"]["flags"]


@pytest.mark.asyncio
async def test_dispatch_with_pack_only_is_no_op(monkeypatch) -> None:
    """Pack set but JSONL path missing → silent no-op (no partial wiring)."""
    monkeypatch.setenv("POLICY_CORE_V3_SHADOW_PACK_PATH", str(EXAMPLE_PACK))
    wiring.reset_singletons()
    dispatcher.dispatch_fire_and_forget(
        tenant_id="t",
        conversation_id="c",
        current_message="hi",
        legacy_decision=_LegacyDecision(),
    )
