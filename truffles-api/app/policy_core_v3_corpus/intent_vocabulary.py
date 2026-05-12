"""Legacy intent → v3 intent vocabulary normalization.

Spec: SPECS/INTENT_VOCABULARY.md.

Pure mapping. No I/O. Closed vocabulary; additions go through a Decision
Ledger entry.
"""
from __future__ import annotations

from typing import Any

from app.policy_core_v3.schema import (
    DegradeVerdict,
    Intent,
    PolicyDecisionV3,
)
from app.policy_core_v3_shadow import LegacySummary


# Legacy → v3 mapping. Identity rows for completeness.
_DIRECT_MAP: dict[str, str] = {
    "fact_question": Intent.fact_question.value,
    "smalltalk": Intent.smalltalk.value,
    "unsupported": Intent.unsupported.value,
    "booking_manage": Intent.booking_manage.value,
    "cancel_request": Intent.handoff_request.value,
    "reschedule": Intent.handoff_request.value,
    "medical": Intent.handoff_request.value,
    "complaint": Intent.handoff_request.value,
    "refund": Intent.handoff_request.value,
    "legal": Intent.handoff_request.value,
    "payment": Intent.handoff_request.value,
    "master_query": Intent.fact_question.value,
    "discount_haggle": Intent.fact_question.value,
}

# Legacy intents that imply handoff also imply a `args.reason` value to
# expect on the v3 side.
_HANDOFF_REASONS: set[str] = {
    "cancel_request",
    "reschedule",
    "medical",
    "complaint",
    "refund",
    "legal",
    "payment",
}

# Slot-key → abstract slot kind mapping for required-slots discrimination.
_SLOT_KIND_MAP: dict[str, str] = {
    "service_id": "service",
    "service_query": "service",
    "datetime": "datetime",
    "start_at": "datetime",
    "customer_name": "name",
    "name": "name",
    "customer_phone": "phone",
    "phone": "phone",
    "lookup_identity": "identity",
}


def _collected_slot_kinds(
    state_slots: dict[str, Any] | None,
) -> set[str]:
    if not state_slots:
        return set()
    out: set[str] = set()
    for key, value in state_slots.items():
        if value in (None, "", [], {}):
            continue
        kind = _SLOT_KIND_MAP.get(key)
        if kind:
            out.add(kind)
    return out


def normalize_legacy_intent(
    legacy_intent: str,
    *,
    legacy_tool_action: str | None = None,
    state_slots: dict[str, Any] | None = None,
    required_for_booking: list[str] | None = None,
) -> str:
    """Map a legacy intent label to the v3 enum value (string).

    For `booking_request`, the discriminator between v3 `booking_request`
    and `slot_collect` uses `state_slots` and `required_for_booking`.
    Unknown labels map to `unknown`.
    """
    if legacy_intent == "booking_request":
        if legacy_tool_action == "calendar.book_slot":
            collected = _collected_slot_kinds(state_slots)
            required = set(required_for_booking or ())
            if required and required.issubset(collected):
                return Intent.booking_request.value
        return Intent.slot_collect.value
    return _DIRECT_MAP.get(legacy_intent, Intent.unknown.value)


def semantic_match(
    legacy_summary: LegacySummary,
    v3_outcome: PolicyDecisionV3 | DegradeVerdict,
    *,
    state_slots: dict[str, Any] | None = None,
    required_for_booking: list[str] | None = None,
) -> bool:
    """Return True if v3 semantically agrees with legacy after normalization.

    A v3 `DegradeVerdict` never matches.

    A v3 `handoff_request` with `args.reason == legacy_intent` matches a
    legacy escalation intent even when the v3 enum value differs.
    """
    if isinstance(v3_outcome, DegradeVerdict):
        return False

    expected = normalize_legacy_intent(
        legacy_summary.intent,
        legacy_tool_action=legacy_summary.tool_action,
        state_slots=state_slots,
        required_for_booking=required_for_booking,
    )
    actual = v3_outcome.intent.value

    if actual == expected:
        return True

    # When the caller cannot disambiguate booking_request vs slot_collect
    # (no state/rules), accept either side. The discriminator is purely
    # commit-readiness; both labels are semantically valid for a legacy
    # `booking_request` turn.
    if legacy_summary.intent == "booking_request":
        if actual in {
            Intent.booking_request.value,
            Intent.slot_collect.value,
        }:
            return True

    if (
        actual == Intent.handoff_request.value
        and legacy_summary.intent in _HANDOFF_REASONS
    ):
        reason = (v3_outcome.candidate_action.args or {}).get("reason")
        if isinstance(reason, str) and reason == legacy_summary.intent:
            return True

    return False
