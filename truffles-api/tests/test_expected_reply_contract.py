from app.services.expected_reply_contract import (
    EXPECTED_REPLY_NAME,
    EXPECTED_REPLY_SERVICE,
    EXPECTED_REPLY_TIME,
    normalize_expected_reply_type,
    resolve_services_overview_contract_update,
    resolve_tool_expected_reply_contract,
)


def test_normalize_expected_reply_type_filters_unknown_values():
    assert normalize_expected_reply_type(" service_choice ") == EXPECTED_REPLY_SERVICE
    assert normalize_expected_reply_type("unknown") is None
    assert normalize_expected_reply_type(None) is None


def test_services_overview_contract_update_sets_service_choice():
    update = resolve_services_overview_contract_update(
        tool_action="catalog.service_query",
        tool_decision="services_overview",
        current_expected_reply_type=None,
        memory_expected_reply_type=None,
    )

    assert update is not None
    assert update.expected_reply_type == EXPECTED_REPLY_SERVICE
    assert update.reason == "services_overview"


def test_services_overview_contract_update_skips_when_expected_reply_exists():
    update = resolve_services_overview_contract_update(
        tool_action="catalog.service_query",
        tool_decision="services_overview",
        current_expected_reply_type=EXPECTED_REPLY_SERVICE,
        memory_expected_reply_type=None,
    )

    assert update is None


def test_tool_contract_list_slots_prefers_time_when_service_known():
    decision = resolve_tool_expected_reply_contract(
        tool_action="calendar.list_slots",
        tool_decision="ok",
        current_expected_reply_type=None,
        memory_expected_reply_type=None,
        booking_has_service=True,
        booking_has_datetime=False,
        booking_has_name=False,
        booking_active=True,
    )

    assert decision is not None
    assert decision.expected_reply_type == EXPECTED_REPLY_TIME
    assert decision.reason == "calendar_list_slots_time_followup"
    assert decision.requires_handoff is False


def test_tool_contract_book_slot_conflict_requires_time_followup():
    decision = resolve_tool_expected_reply_contract(
        tool_action="calendar.book_slot",
        tool_decision="conflict",
        current_expected_reply_type=EXPECTED_REPLY_TIME,
        memory_expected_reply_type=None,
        booking_has_service=True,
        booking_has_datetime=True,
        booking_has_name=True,
        booking_active=True,
    )

    assert decision is not None
    assert decision.expected_reply_type == EXPECTED_REPLY_TIME
    assert decision.reason == "calendar_book_slot_conflict"


def test_tool_contract_reschedule_verifier_blocked_requires_handoff():
    decision = resolve_tool_expected_reply_contract(
        tool_action="calendar.reschedule",
        tool_decision="verifier_blocked",
        current_expected_reply_type=None,
        memory_expected_reply_type=None,
        booking_has_service=True,
        booking_has_datetime=True,
        booking_has_name=True,
        booking_active=True,
    )

    assert decision is not None
    assert decision.requires_handoff is True
    assert decision.clear_expected_reply is True
    assert decision.reason == "calendar_reschedule_handoff"


def test_tool_contract_get_booking_verifier_blocked_collects_time_when_name_known():
    decision = resolve_tool_expected_reply_contract(
        tool_action="calendar.get_booking",
        tool_decision="verifier_blocked",
        current_expected_reply_type=None,
        memory_expected_reply_type=None,
        booking_has_service=True,
        booking_has_datetime=False,
        booking_has_name=True,
        booking_active=True,
    )

    assert decision is not None
    assert decision.expected_reply_type == EXPECTED_REPLY_TIME
    assert decision.reason == "calendar_get_booking_collect_reference"


def test_tool_contract_get_booking_verifier_blocked_collects_name_when_name_missing():
    decision = resolve_tool_expected_reply_contract(
        tool_action="calendar.get_booking",
        tool_decision="verifier_blocked",
        current_expected_reply_type=None,
        memory_expected_reply_type=None,
        booking_has_service=True,
        booking_has_datetime=True,
        booking_has_name=False,
        booking_active=True,
    )

    assert decision is not None
    assert decision.expected_reply_type == EXPECTED_REPLY_NAME
    assert decision.reason == "calendar_get_booking_collect_reference"
