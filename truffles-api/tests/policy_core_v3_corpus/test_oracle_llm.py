"""Oracle/drift mock LLM tests."""
from __future__ import annotations

import json

import pytest

from app.policy_core_v3.schema import (
    CandidateAction,
    Intent,
    PolicyDecisionV3,
)
from app.policy_core_v3_corpus import OracleLLMConfig, OracleLLMMode, build_oracle_llm
from app.policy_core_v3_corpus.oracle_llm import OracleRegistry


def _oracle() -> PolicyDecisionV3:
    return PolicyDecisionV3(
        intent=Intent.fact_question,
        candidate_action=CandidateAction(tool="none"),
        message_draft="oracle answer",
    )


@pytest.mark.asyncio
async def test_oracle_mode_returns_oracle_verbatim() -> None:
    reg = OracleRegistry()
    llm = build_oracle_llm(reg)
    reg.set_active(_oracle(), token="t1")
    raw = await llm("any prompt")
    payload = json.loads(raw)
    assert payload["intent"] == "fact_question"
    assert payload["message_draft"] == "oracle answer"


@pytest.mark.asyncio
async def test_oracle_mode_no_active_returns_empty() -> None:
    reg = OracleRegistry()
    llm = build_oracle_llm(reg)
    raw = await llm("any prompt")
    assert raw == ""


@pytest.mark.asyncio
async def test_degrade_mode_always_empty() -> None:
    reg = OracleRegistry()
    llm = build_oracle_llm(reg, OracleLLMConfig(mode=OracleLLMMode.degrade))
    reg.set_active(_oracle(), token="t1")
    raw = await llm("any prompt")
    assert raw == ""


@pytest.mark.asyncio
async def test_drift_mode_corruption_is_deterministic() -> None:
    reg = OracleRegistry()
    cfg = OracleLLMConfig(mode=OracleLLMMode.drift, drift_rate=1.0)
    llm = build_oracle_llm(reg, cfg)
    reg.set_active(_oracle(), token="t1")
    raw1 = await llm("p")
    raw2 = await llm("p")
    assert raw1 == raw2
    payload = json.loads(raw1)
    # drift_rate=1 → always drifted; intent should rotate to a sibling
    assert payload["intent"] != "fact_question"


@pytest.mark.asyncio
async def test_drift_mode_zero_rate_passes_oracle_through() -> None:
    reg = OracleRegistry()
    cfg = OracleLLMConfig(mode=OracleLLMMode.drift, drift_rate=0.0)
    llm = build_oracle_llm(reg, cfg)
    reg.set_active(_oracle(), token="t1")
    raw = await llm("p")
    payload = json.loads(raw)
    assert payload["intent"] == "fact_question"
