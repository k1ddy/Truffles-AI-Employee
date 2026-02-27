from __future__ import annotations

from dataclasses import dataclass

EXPECTED_REPLY_SERVICE = "service_choice"
EXPECTED_REPLY_TIME = "time"
EXPECTED_REPLY_NAME = "name"
EXPECTED_REPLY_INTENT_CHOICE = "intent_choice"

EXPECTED_REPLY_ALLOWED_TYPES = {
    EXPECTED_REPLY_SERVICE,
    EXPECTED_REPLY_TIME,
    EXPECTED_REPLY_NAME,
    EXPECTED_REPLY_INTENT_CHOICE,
}


@dataclass(frozen=True)
class ExpectedReplyContractUpdate:
    expected_reply_type: str
    reason: str


@dataclass(frozen=True)
class ExpectedReplyContractDecision:
    expected_reply_type: str | None = None
    reason: str | None = None
    requires_handoff: bool = False
    clear_expected_reply: bool = False


def _normalize_token(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().casefold()
    return cleaned or None


def normalize_expected_reply_type(value: str | None) -> str | None:
    cleaned = _normalize_token(value)
    if not cleaned:
        return None
    if cleaned not in EXPECTED_REPLY_ALLOWED_TYPES:
        return None
    return cleaned


def resolve_services_overview_contract_update(
    *,
    tool_action: str | None,
    tool_decision: str | None,
    current_expected_reply_type: str | None,
    memory_expected_reply_type: str | None,
) -> ExpectedReplyContractUpdate | None:
    if _normalize_token(tool_action) != "catalog.service_query":
        return None
    if _normalize_token(tool_decision) != "services_overview":
        return None
    if normalize_expected_reply_type(current_expected_reply_type):
        return None
    if normalize_expected_reply_type(memory_expected_reply_type):
        return None
    return ExpectedReplyContractUpdate(
        expected_reply_type=EXPECTED_REPLY_SERVICE,
        reason="services_overview",
    )


def _missing_booking_slot_expected_reply(
    *,
    booking_has_service: bool,
    booking_has_datetime: bool,
    booking_has_name: bool,
) -> str | None:
    if not booking_has_service:
        return EXPECTED_REPLY_SERVICE
    if not booking_has_datetime:
        return EXPECTED_REPLY_TIME
    if not booking_has_name:
        return EXPECTED_REPLY_NAME
    return None


def resolve_tool_expected_reply_contract(
    *,
    tool_action: str | None,
    tool_decision: str | None,
    current_expected_reply_type: str | None,
    memory_expected_reply_type: str | None,
    booking_has_service: bool,
    booking_has_datetime: bool,
    booking_has_name: bool,
    booking_active: bool,
) -> ExpectedReplyContractDecision | None:
    normalized_action = _normalize_token(tool_action)
    normalized_decision = _normalize_token(tool_decision)
    current_expected = normalize_expected_reply_type(current_expected_reply_type)
    memory_expected = normalize_expected_reply_type(memory_expected_reply_type)
    expected_from_slots = _missing_booking_slot_expected_reply(
        booking_has_service=booking_has_service,
        booking_has_datetime=booking_has_datetime,
        booking_has_name=booking_has_name,
    )

    if normalized_action == "catalog.service_query":
        services_overview_update = resolve_services_overview_contract_update(
            tool_action=normalized_action,
            tool_decision=normalized_decision,
            current_expected_reply_type=current_expected,
            memory_expected_reply_type=memory_expected,
        )
        if services_overview_update:
            return ExpectedReplyContractDecision(
                expected_reply_type=services_overview_update.expected_reply_type,
                reason=services_overview_update.reason,
            )
        if (
            booking_active
            and normalized_decision
            in {
                "ok",
                "truth_fallback",
                "duration",
                "promotions",
                "presence_fallback",
                "price_item_fallback",
                "service_not_found",
                "not_found_fallback",
            }
            and booking_has_service
            and not booking_has_datetime
        ):
            return ExpectedReplyContractDecision(
                expected_reply_type=EXPECTED_REPLY_TIME,
                reason="catalog_service_booking_progress",
            )
        if (
            booking_active
            and normalized_decision in {"service_not_found", "not_found_fallback"}
            and not booking_has_service
        ):
            return ExpectedReplyContractDecision(
                expected_reply_type=EXPECTED_REPLY_SERVICE,
                reason="catalog_service_missing_service",
            )
        return None

    if normalized_action == "calendar.list_slots":
        if normalized_decision in {"ok", "specialist_missing"}:
            if booking_has_service:
                return ExpectedReplyContractDecision(
                    expected_reply_type=EXPECTED_REPLY_TIME,
                    reason="calendar_list_slots_time_followup",
                )
            return ExpectedReplyContractDecision(
                expected_reply_type=EXPECTED_REPLY_SERVICE,
                reason="calendar_list_slots_service_followup",
            )
        if normalized_decision in {"missing_slot", "contract_invalid", "verifier_blocked"} and expected_from_slots:
            return ExpectedReplyContractDecision(
                expected_reply_type=expected_from_slots,
                reason="calendar_list_slots_collect",
            )
        return None

    if normalized_action == "calendar.book_slot":
        if normalized_decision == "ok":
            return ExpectedReplyContractDecision(
                reason="calendar_book_slot_committed",
                clear_expected_reply=True,
            )
        if normalized_decision == "conflict":
            return ExpectedReplyContractDecision(
                expected_reply_type=EXPECTED_REPLY_TIME,
                reason="calendar_book_slot_conflict",
            )
        if normalized_decision in {"missing_slot", "contract_invalid", "verifier_blocked"} and expected_from_slots:
            return ExpectedReplyContractDecision(
                expected_reply_type=expected_from_slots,
                reason="calendar_book_slot_collect",
            )
        return None

    if normalized_action == "calendar.get_booking":
        if normalized_decision in {"ok"}:
            return ExpectedReplyContractDecision(
                reason="calendar_get_booking_resolved",
                clear_expected_reply=True,
            )
        if normalized_decision in {"verifier_blocked", "contract_invalid", "not_found", "time_mismatch"}:
            followup_type = EXPECTED_REPLY_TIME if booking_has_name else EXPECTED_REPLY_NAME
            return ExpectedReplyContractDecision(
                expected_reply_type=followup_type,
                reason="calendar_get_booking_collect_reference",
            )
        return None

    if normalized_action == "calendar.reschedule":
        if normalized_decision in {"ok"}:
            return ExpectedReplyContractDecision(
                reason="calendar_reschedule_resolved",
                clear_expected_reply=True,
            )
        if normalized_decision in {"missing_slot", "not_found", "contract_invalid", "verifier_blocked"}:
            return ExpectedReplyContractDecision(
                reason="calendar_reschedule_handoff",
                requires_handoff=True,
                clear_expected_reply=True,
            )
        return None

    if normalized_action == "calendar.cancel":
        if normalized_decision in {"ok"}:
            return ExpectedReplyContractDecision(
                reason="calendar_cancel_resolved",
                clear_expected_reply=True,
            )
        if normalized_decision in {"not_found", "contract_invalid", "verifier_blocked"}:
            return ExpectedReplyContractDecision(
                reason="calendar_cancel_handoff",
                requires_handoff=True,
                clear_expected_reply=True,
            )
        return None

    return None
