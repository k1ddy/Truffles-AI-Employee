"""Vocabulary normalizer + semantic_match tests."""
from __future__ import annotations

from app.policy_core_v3.schema import (
    CandidateAction,
    DegradeReason,
    DegradeVerdict,
    Intent,
    PolicyDecisionV3,
    Uncertainty,
)
from app.policy_core_v3_corpus import normalize_legacy_intent, semantic_match
from app.policy_core_v3_shadow import LegacySummary


def test_identity_rows() -> None:
    for legacy in ("fact_question", "smalltalk", "unsupported", "booking_manage"):
        assert normalize_legacy_intent(legacy) == legacy


def test_escalation_rows_collapse_to_handoff() -> None:
    for legacy in (
        "cancel_request", "reschedule", "medical", "complaint",
        "refund", "legal", "payment",
    ):
        assert normalize_legacy_intent(legacy) == "handoff_request"


def test_master_and_discount_collapse_to_fact() -> None:
    assert normalize_legacy_intent("master_query") == "fact_question"
    assert normalize_legacy_intent("discount_haggle") == "fact_question"


def test_unknown_legacy_label_maps_to_unknown() -> None:
    assert normalize_legacy_intent("not_a_real_intent") == "unknown"


def test_booking_request_without_full_slots_is_slot_collect() -> None:
    out = normalize_legacy_intent(
        "booking_request",
        legacy_tool_action="calendar.list_slots",
        state_slots={"service_id": "manicure"},
        required_for_booking=["service", "datetime", "name", "phone"],
    )
    assert out == "slot_collect"


def test_booking_request_with_full_slots_and_book_slot_tool_is_booking_request() -> None:
    out = normalize_legacy_intent(
        "booking_request",
        legacy_tool_action="calendar.book_slot",
        state_slots={
            "service_id": "manicure",
            "datetime": "2026-05-12T17:00:00+05:00",
            "customer_name": "Айгуль",
            "customer_phone": "87015705555",
        },
        required_for_booking=["service", "datetime", "name", "phone"],
    )
    assert out == "booking_request"


def test_semantic_match_handoff_with_reason_arg() -> None:
    legacy = LegacySummary(intent="cancel_request", action="escalate", tool_action="handoff.create")
    v3 = PolicyDecisionV3(
        intent=Intent.handoff_request,
        candidate_action=CandidateAction(tool="handoff.create", args={"reason": "cancel_request"}),
    )
    assert semantic_match(legacy, v3) is True


def test_semantic_match_handoff_intent_alone_matches_via_direct_map() -> None:
    """Cancel maps directly to handoff_request; reason arg is a bonus check
    used when v3 intent does not equal the normalized legacy intent."""
    legacy = LegacySummary(intent="cancel_request", action="escalate", tool_action="handoff.create")
    v3 = PolicyDecisionV3(
        intent=Intent.handoff_request,
        candidate_action=CandidateAction(tool="handoff.create"),
    )
    assert semantic_match(legacy, v3) is True


def test_semantic_match_booking_request_collecting_matches_slot_collect() -> None:
    legacy = LegacySummary(
        intent="booking_request", action="collect",
        tool_action="calendar.list_slots",
    )
    v3 = PolicyDecisionV3(
        intent=Intent.slot_collect,
        candidate_action=CandidateAction(tool="none"),
    )
    assert semantic_match(
        legacy, v3,
        state_slots={"service_id": "manicure"},
        required_for_booking=["service", "datetime", "name", "phone"],
    ) is True


def test_semantic_match_master_query_matches_fact_question() -> None:
    legacy = LegacySummary(intent="master_query", action="reply")
    v3 = PolicyDecisionV3(
        intent=Intent.fact_question,
        candidate_action=CandidateAction(tool="none"),
    )
    assert semantic_match(legacy, v3) is True


def test_semantic_match_degrade_never_matches() -> None:
    legacy = LegacySummary(intent="fact_question", action="reply")
    v3 = DegradeVerdict(degrade_reason=DegradeReason.empty_response, attempts=2)
    assert semantic_match(legacy, v3) is False
