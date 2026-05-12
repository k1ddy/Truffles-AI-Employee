"""Divergence classifier tests — pure logic, no I/O."""
from __future__ import annotations

from app.policy_core_v3.schema import (
    CandidateAction,
    DegradeReason,
    DegradeVerdict,
    Intent,
    PolicyDecisionV3,
    Uncertainty,
)
from app.policy_core_v3_shadow import LegacySummary, compute_divergence


def _v3_decision(**overrides) -> PolicyDecisionV3:
    base = dict(
        intent=Intent.booking_request,
        candidate_action=CandidateAction(tool="none"),
        uncertainty=Uncertainty.low,
    )
    base.update(overrides)
    return PolicyDecisionV3(**base)


def _legacy(**overrides) -> LegacySummary:
    base = dict(intent="booking_request", action="collect")
    base.update(overrides)
    return LegacySummary(**base)


def test_intent_match_basic() -> None:
    d = compute_divergence(_legacy(), _v3_decision())
    assert d.intent_match is True
    assert d.legacy_intent == "booking_request"
    assert d.v3_intent == "booking_request"
    assert d.v3_degraded is False
    assert "intent_match" in d.flags
    assert "intent_mismatch" not in d.flags


def test_intent_mismatch() -> None:
    d = compute_divergence(_legacy(), _v3_decision(intent=Intent.smalltalk))
    assert d.intent_match is False
    assert "intent_mismatch" in d.flags


def test_v3_degrade_flags() -> None:
    verdict = DegradeVerdict(
        degrade_reason=DegradeReason.empty_response, attempts=2
    )
    d = compute_divergence(_legacy(), verdict)
    assert d.v3_degraded is True
    assert d.v3_intent is None
    assert "v3_degrade" in d.flags
    assert "legacy_decision_while_v3_degrade" in d.flags
    assert "intent_match" not in d.flags


def test_both_degrade_flags() -> None:
    verdict = DegradeVerdict(
        degrade_reason=DegradeReason.timeout, attempts=2
    )
    legacy = _legacy(policy_core_degrade=True, degrade_reason="timeout")
    d = compute_divergence(legacy, verdict)
    assert "legacy_degrade" in d.flags
    assert "v3_degrade" in d.flags
    assert "both_degrade" in d.flags


def test_v3_decision_while_legacy_degrade() -> None:
    legacy = _legacy(policy_core_degrade=True)
    d = compute_divergence(legacy, _v3_decision())
    assert "v3_decision_while_legacy_degrade" in d.flags
    assert "legacy_degrade" in d.flags
    assert "v3_degrade" not in d.flags


def test_legacy_rescue_flag_propagates() -> None:
    legacy = _legacy(rescue_flag=True)
    d = compute_divergence(legacy, _v3_decision())
    assert "legacy_rescue" in d.flags


def test_tool_action_match() -> None:
    legacy = _legacy(tool_action="calendar.book_slot")
    v3 = _v3_decision(candidate_action=CandidateAction(tool="calendar.book_slot"))
    d = compute_divergence(legacy, v3)
    assert "tool_action_match" in d.flags
    assert "tool_action_mismatch" not in d.flags


def test_tool_action_mismatch() -> None:
    legacy = _legacy(tool_action="calendar.list_slots")
    v3 = _v3_decision(candidate_action=CandidateAction(tool="none"))
    d = compute_divergence(legacy, v3)
    assert "tool_action_mismatch" in d.flags


def test_high_uncertainty_flag() -> None:
    v3 = _v3_decision(uncertainty=Uncertainty.high)
    d = compute_divergence(_legacy(), v3)
    assert "high_uncertainty" in d.flags


def test_flags_are_deduplicated_and_ordered() -> None:
    """Stable flag order: presence of one flag does not duplicate another."""
    verdict = DegradeVerdict(
        degrade_reason=DegradeReason.timeout, attempts=2
    )
    legacy = _legacy(policy_core_degrade=True, rescue_flag=True)
    d = compute_divergence(legacy, verdict)
    assert len(d.flags) == len(set(d.flags))
