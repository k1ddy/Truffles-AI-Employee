"""Invoker integration tests with a mock LLM."""
from __future__ import annotations

import json

import pytest

from app.policy_core_v3.invoker import (
    LLMProviderError,
    LLMTimeout,
    PolicyCoreV3Invoker,
)
from app.policy_core_v3.schema import (
    DegradeReason,
    DegradeVerdict,
    Intent,
    PolicyDecisionV3,
)


def _good_decision_json(tool: str = "none") -> str:
    return json.dumps(
        {
            "intent": "fact_question",
            "slots": {},
            "candidate_action": {"tool": tool, "args": {}},
            "evidence_refs": ["ev-1"],
            "message_draft": "Адрес: Абая 1.",
            "uncertainty": "low",
            "notes": "",
        },
        ensure_ascii=False,
    )


@pytest.mark.asyncio
async def test_happy_path_returns_decision(sample_input) -> None:
    calls = []

    async def llm(prompt: str) -> str:
        calls.append(prompt)
        return _good_decision_json()

    inv = PolicyCoreV3Invoker(llm)
    out = await inv.invoke(sample_input)
    assert isinstance(out, PolicyDecisionV3)
    assert out.intent == Intent.fact_question
    assert out.candidate_action.tool == "none"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_handles_fenced_json(sample_input) -> None:
    async def llm(prompt: str) -> str:
        return f"```json\n{_good_decision_json()}\n```"

    out = await PolicyCoreV3Invoker(llm).invoke(sample_input)
    assert isinstance(out, PolicyDecisionV3)


@pytest.mark.asyncio
async def test_empty_then_valid_retries_once(sample_input) -> None:
    sequence = ["   ", _good_decision_json()]
    calls = []

    async def llm(prompt: str) -> str:
        calls.append(prompt)
        return sequence.pop(0)

    out = await PolicyCoreV3Invoker(llm).invoke(sample_input)
    assert isinstance(out, PolicyDecisionV3)
    assert len(calls) == 2
    # second prompt must include the retry hint
    assert "RETRY HINT" in calls[1]


@pytest.mark.asyncio
async def test_two_empty_returns_degrade(sample_input) -> None:
    async def llm(prompt: str) -> str:
        return ""

    out = await PolicyCoreV3Invoker(llm).invoke(sample_input)
    assert isinstance(out, DegradeVerdict)
    assert out.degrade_reason == DegradeReason.empty_response
    assert out.attempts == 2


@pytest.mark.asyncio
async def test_schema_invalid_then_valid_retries(sample_input) -> None:
    sequence = ['{"intent": "fact_question"}', _good_decision_json()]

    async def llm(prompt: str) -> str:
        return sequence.pop(0)

    out = await PolicyCoreV3Invoker(llm).invoke(sample_input)
    assert isinstance(out, PolicyDecisionV3)


@pytest.mark.asyncio
async def test_unknown_tool_id_routes_to_correct_hint(sample_input) -> None:
    bad = json.dumps(
        {
            "intent": "booking_request",
            "slots": {},
            "candidate_action": {"tool": "calendar.invent_slot", "args": {}},
            "evidence_refs": [],
            "message_draft": "ok",
            "uncertainty": "low",
            "notes": "",
        }
    )
    sequence = [bad, _good_decision_json()]
    calls = []

    async def llm(prompt: str) -> str:
        calls.append(prompt)
        return sequence.pop(0)

    out = await PolicyCoreV3Invoker(llm).invoke(sample_input)
    assert isinstance(out, PolicyDecisionV3)
    assert "allowed_tool_ids" in calls[1]


@pytest.mark.asyncio
async def test_unknown_intent_returns_degrade_after_retries(sample_input) -> None:
    bad = json.dumps(
        {
            "intent": "make_coffee",
            "slots": {},
            "candidate_action": {"tool": "none", "args": {}},
            "evidence_refs": [],
            "message_draft": "ok",
            "uncertainty": "low",
            "notes": "",
        }
    )

    async def llm(prompt: str) -> str:
        return bad

    out = await PolicyCoreV3Invoker(llm).invoke(sample_input)
    assert isinstance(out, DegradeVerdict)
    assert out.degrade_reason == DegradeReason.intent_not_in_enum


@pytest.mark.asyncio
async def test_timeout_returns_degrade(sample_input) -> None:
    async def llm(prompt: str) -> str:
        raise LLMTimeout()

    out = await PolicyCoreV3Invoker(llm).invoke(sample_input)
    assert isinstance(out, DegradeVerdict)
    assert out.degrade_reason == DegradeReason.timeout
    assert out.attempts == 2


@pytest.mark.asyncio
async def test_provider_error_returns_degrade(sample_input) -> None:
    async def llm(prompt: str) -> str:
        raise LLMProviderError("upstream 502")

    out = await PolicyCoreV3Invoker(llm).invoke(sample_input)
    assert isinstance(out, DegradeVerdict)
    assert out.degrade_reason == DegradeReason.provider_error


@pytest.mark.asyncio
async def test_invoker_does_no_io_beyond_llm(sample_input) -> None:
    """The invoker must be a pure orchestrator; verify it never imports
    anything from app.services/app.core."""
    import app.policy_core_v3.invoker as inv_mod
    src = inv_mod.__file__
    with open(src, encoding="utf-8") as f:
        text = f.read()
    assert "from app.services" not in text
    assert "from app.core" not in text
    assert "import app.services" not in text
    assert "import app.core" not in text
