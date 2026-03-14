from app.services.expected_reply_contract import (
    EXPECTED_REPLY_NAME,
    EXPECTED_REPLY_PHONE,
    EXPECTED_REPLY_SERVICE,
    EXPECTED_REPLY_TIME,
    expected_reply_slot_key,
    normalize_expected_reply_type,
    resolve_services_overview_contract_update,
    resolve_tool_expected_reply_contract,
    should_allow_layout_swap_for_expected_reply,
    should_keep_booking_prompt_for_info_clarify_time_followup,
    should_mark_booking_time_service_candidate,
    should_override_truth_gate_off_topic_contract,
    should_prefer_info_class_for_booking_interrupt,
    should_repeat_booking_prompt,
    should_skip_booking_interrupt_for_expected_reply,
    should_use_expected_service_off_topic_prompt,
    truth_gate_expected_reply_prompt_contract,
)


def test_normalize_expected_reply_type_filters_unknown_values():
    assert normalize_expected_reply_type(" service_choice ") == EXPECTED_REPLY_SERVICE
    assert normalize_expected_reply_type(" phone ") == EXPECTED_REPLY_PHONE
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


def test_booking_interrupt_skip_requires_active_expected_reply_without_info_block():
    assert (
        should_skip_booking_interrupt_for_expected_reply(
            expected_reply_type=EXPECTED_REPLY_TIME,
            expected_reply_blocked_by_info=False,
            has_info_interrupt=False,
        )
        is True
    )


def test_booking_interrupt_skip_is_disabled_when_info_interrupt_exists():
    assert (
        should_skip_booking_interrupt_for_expected_reply(
            expected_reply_type=EXPECTED_REPLY_TIME,
            expected_reply_blocked_by_info=False,
            has_info_interrupt=True,
        )
        is False
    )


def test_booking_interrupt_skip_is_disabled_when_expected_reply_blocked():
    assert (
        should_skip_booking_interrupt_for_expected_reply(
            expected_reply_type=EXPECTED_REPLY_TIME,
            expected_reply_blocked_by_info=True,
            has_info_interrupt=False,
        )
        is False
    )


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


def test_tool_contract_catalog_service_query_preserves_booking_progress_when_slots_look_complete():
    decision = resolve_tool_expected_reply_contract(
        tool_action="catalog.service_query",
        tool_decision="truth_fallback",
        current_expected_reply_type=EXPECTED_REPLY_TIME,
        memory_expected_reply_type=None,
        booking_has_service=True,
        booking_has_datetime=True,
        booking_has_name=True,
        booking_active=True,
    )

    assert decision is not None
    assert decision.expected_reply_type == EXPECTED_REPLY_TIME
    assert decision.reason == "catalog_service_booking_progress"
    assert decision.requires_handoff is False


def test_tool_contract_list_slots_specialist_missing_requests_name():
    decision = resolve_tool_expected_reply_contract(
        tool_action="calendar.list_slots",
        tool_decision="specialist_missing",
        current_expected_reply_type=None,
        memory_expected_reply_type=None,
        booking_has_service=True,
        booking_has_datetime=False,
        booking_has_name=False,
        booking_active=True,
    )

    assert decision is not None
    assert decision.expected_reply_type == EXPECTED_REPLY_NAME
    assert decision.reason == "calendar_list_slots_specialist_followup"
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


def test_tool_contract_book_slot_specialist_missing_requests_name():
    decision = resolve_tool_expected_reply_contract(
        tool_action="calendar.book_slot",
        tool_decision="specialist_missing",
        current_expected_reply_type=EXPECTED_REPLY_NAME,
        memory_expected_reply_type=None,
        booking_has_service=True,
        booking_has_datetime=True,
        booking_has_name=True,
        booking_active=True,
    )

    assert decision is not None
    assert decision.expected_reply_type == EXPECTED_REPLY_NAME
    assert decision.reason == "calendar_book_slot_specialist_followup"
    assert decision.requires_handoff is False


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


def test_expected_reply_slot_key_maps_supported_types():
    assert expected_reply_slot_key(EXPECTED_REPLY_SERVICE) == "service"
    assert expected_reply_slot_key(EXPECTED_REPLY_TIME) == "datetime"
    assert expected_reply_slot_key(EXPECTED_REPLY_NAME) == "name"
    assert expected_reply_slot_key(EXPECTED_REPLY_PHONE) == "phone"
    assert expected_reply_slot_key("unknown") is None


def test_should_allow_layout_swap_for_expected_reply():
    assert should_allow_layout_swap_for_expected_reply(EXPECTED_REPLY_SERVICE) is True
    assert should_allow_layout_swap_for_expected_reply(EXPECTED_REPLY_TIME) is True
    assert should_allow_layout_swap_for_expected_reply(EXPECTED_REPLY_NAME) is False


def test_should_mark_booking_time_service_candidate_requires_unmatched_time():
    assert (
        should_mark_booking_time_service_candidate(
            expected_reply_type=EXPECTED_REPLY_TIME,
            expected_reply_matched=False,
            message_text="на завтра",
        )
        is True
    )
    assert (
        should_mark_booking_time_service_candidate(
            expected_reply_type=EXPECTED_REPLY_TIME,
            expected_reply_matched=True,
            message_text="на завтра",
        )
        is False
    )


def test_should_repeat_booking_prompt_requires_same_expected_and_unmatched():
    assert (
        should_repeat_booking_prompt(
            expected_reply_type=EXPECTED_REPLY_TIME,
            expected_reply_matched=False,
            booking_expected_reply_type=EXPECTED_REPLY_TIME,
        )
        is True
    )
    assert (
        should_repeat_booking_prompt(
            expected_reply_type=EXPECTED_REPLY_TIME,
            expected_reply_matched=False,
            booking_expected_reply_type=EXPECTED_REPLY_SERVICE,
        )
        is False
    )


def test_truth_gate_expected_reply_prompt_contract_maps_prompt_keys():
    assert truth_gate_expected_reply_prompt_contract(EXPECTED_REPLY_SERVICE) == (
        "service_clarify",
        "service_clarify",
    )
    assert truth_gate_expected_reply_prompt_contract(EXPECTED_REPLY_TIME) == (
        "booking_ask_datetime",
        "booking_followup",
    )
    assert truth_gate_expected_reply_prompt_contract(EXPECTED_REPLY_PHONE) == (
        "booking_ask_phone",
        "booking_followup",
    )
    assert truth_gate_expected_reply_prompt_contract("unknown") == (None, None)


def test_should_override_truth_gate_off_topic_contract():
    assert (
        should_override_truth_gate_off_topic_contract(
            expected_reply_type=EXPECTED_REPLY_SERVICE,
            expected_reply_matched=None,
            has_message_text=True,
            current_goal="booking",
            is_short_reply=False,
            has_booking_slot_signal=False,
            has_service_hint=False,
            has_datetime_slot=False,
            has_name_slot=False,
        )
        is True
    )
    assert (
        should_override_truth_gate_off_topic_contract(
            expected_reply_type=EXPECTED_REPLY_TIME,
            expected_reply_matched=None,
            has_message_text=True,
            current_goal="info",
            is_short_reply=False,
            has_booking_slot_signal=False,
            has_service_hint=False,
            has_datetime_slot=True,
            has_name_slot=False,
        )
        is True
    )
    assert (
        should_override_truth_gate_off_topic_contract(
            expected_reply_type="unknown",
            expected_reply_matched=None,
            has_message_text=True,
            current_goal="info",
            is_short_reply=False,
            has_booking_slot_signal=False,
            has_service_hint=False,
            has_datetime_slot=False,
            has_name_slot=False,
        )
        is False
    )


def test_should_prefer_info_class_for_booking_interrupt():
    assert (
        should_prefer_info_class_for_booking_interrupt(
            info_class_intents_present=True,
            booking_time_service_candidate=False,
            expected_reply_type=EXPECTED_REPLY_SERVICE,
        )
        is True
    )
    assert (
        should_prefer_info_class_for_booking_interrupt(
            info_class_intents_present=False,
            booking_time_service_candidate=True,
            expected_reply_type=EXPECTED_REPLY_SERVICE,
        )
        is False
    )


def test_should_use_expected_service_off_topic_prompt():
    assert should_use_expected_service_off_topic_prompt(EXPECTED_REPLY_SERVICE) is True
    assert should_use_expected_service_off_topic_prompt(EXPECTED_REPLY_TIME) is False


def test_should_keep_booking_prompt_for_info_clarify_time_followup():
    assert (
        should_keep_booking_prompt_for_info_clarify_time_followup(
            info_intent="info_clarify",
            booking_active=True,
            expected_reply_type=EXPECTED_REPLY_TIME,
            booking_expected_reply_type=EXPECTED_REPLY_TIME,
            domain_out_of_domain=True,
        )
        is True
    )
    assert (
        should_keep_booking_prompt_for_info_clarify_time_followup(
            info_intent="info_clarify",
            booking_active=True,
            expected_reply_type=EXPECTED_REPLY_SERVICE,
            booking_expected_reply_type=EXPECTED_REPLY_TIME,
            domain_out_of_domain=True,
        )
        is False
    )
