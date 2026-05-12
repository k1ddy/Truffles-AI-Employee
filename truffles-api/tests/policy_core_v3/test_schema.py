"""Schema contract tests for policy_core_v3."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.policy_core_v3.schema import (
    CandidateAction,
    DegradeReason,
    DegradeVerdict,
    Intent,
    PolicyDecisionV3,
    Uncertainty,
)


def test_decision_minimal_valid() -> None:
    d = PolicyDecisionV3(
        intent=Intent.fact_question,
        candidate_action=CandidateAction(tool="none"),
    )
    assert d.intent == Intent.fact_question
    assert d.candidate_action.tool == "none"
    assert d.uncertainty == Uncertainty.medium
    assert d.evidence_refs == []


def test_decision_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        PolicyDecisionV3.model_validate(
            {
                "intent": "fact_question",
                "candidate_action": {"tool": "none", "args": {}},
                "wat": "nope",
            }
        )


def test_decision_message_draft_is_stripped() -> None:
    d = PolicyDecisionV3(
        intent=Intent.smalltalk,
        candidate_action=CandidateAction(tool="none"),
        message_draft="   привет!   ",
    )
    assert d.message_draft == "привет!"


def test_intent_enum_is_closed() -> None:
    with pytest.raises(ValidationError):
        PolicyDecisionV3.model_validate(
            {
                "intent": "make_coffee",
                "candidate_action": {"tool": "none", "args": {}},
            }
        )


def test_degrade_verdict_requires_reason_and_attempts() -> None:
    v = DegradeVerdict(degrade_reason=DegradeReason.empty_response, attempts=2)
    assert v.degrade_reason == DegradeReason.empty_response
    assert v.attempts == 2

    with pytest.raises(ValidationError):
        DegradeVerdict(degrade_reason=DegradeReason.empty_response, attempts=0)
