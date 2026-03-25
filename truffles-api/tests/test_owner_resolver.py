from app.services.owner_resolver import (
    TimeoutOwnerBoundaryInput,
    build_semantic_contract_view,
    build_owner_resolution_input,
    extract_specialist_preference,
    resolve_interaction_owner,
    resolve_timeout_owner_boundary,
    should_preserve_specialist_followup_owner,
)


def test_owner_resolver_matches_m27_and_recovers_service_from_interaction_state() -> None:
    payload = build_owner_resolution_input(
        tool_action="info",
        info_refs=["pricing"],
        expected_reply_type="time",
        expected_reply_reason="booking_confirm_reject",
        interaction_state={
            "interaction_target": "time",
            "interaction_relation": "ask_about_requested_slot",
            "grounded_referents": {"service": "Маникюр"},
        },
        booking_state={"active": True, "last_question": "datetime"},
        service_query=None,
    )

    resolution = resolve_interaction_owner(payload)

    assert resolution is not None
    assert resolution.row_id == "M27"
    assert resolution.execution_owner == "booking-confirm pricing-interrupt service-carryover owner"
    assert resolution.reason_code == "owner_matrix_m27"
    assert resolution.service_query == "Маникюр"
    assert resolution.preserve_expected_reply_type == "time"
    assert resolution.bypass_service_clarify is True


def test_owner_resolver_requires_grounded_service_and_booking_confirm_reject() -> None:
    payload = build_owner_resolution_input(
        tool_action="info",
        info_refs=["pricing"],
        expected_reply_type="time",
        expected_reply_reason="booking_prompt",
        interaction_state={
            "interaction_target": "time",
            "interaction_relation": "ask_about_requested_slot",
            "grounded_referents": {},
        },
        booking_state={"active": True, "last_question": "datetime"},
        service_query=None,
    )

    assert resolve_interaction_owner(payload) is None


def test_owner_resolver_matches_m33_and_preserves_active_name_service_info_resume() -> None:
    payload = build_owner_resolution_input(
        tool_action="catalog.service_query",
        info_refs=["pricing"],
        expected_reply_type="name",
        expected_reply_reason="booking_time_availability_followup",
        interaction_state={
            "interaction_target": "time",
            "interaction_relation": "ask_about_requested_slot",
            "grounded_referents": {"service": "Маникюр"},
        },
        booking_state={"active": True, "last_question": "name"},
        service_query="Маникюр",
    )

    resolution = resolve_interaction_owner(payload)

    assert resolution is not None
    assert resolution.row_id == "M33"
    assert resolution.execution_owner == "active-name service-info interrupt owner"
    assert resolution.reason_code == "owner_matrix_m33"
    assert resolution.service_query is None
    assert resolution.preserve_expected_reply_type == "name"
    assert resolution.bypass_service_clarify is False


def test_timeout_owner_boundary_prefers_matched_expected_reply_continuity() -> None:
    resolution = resolve_timeout_owner_boundary(
        TimeoutOwnerBoundaryInput(
            booking_active=True,
            current_goal="booking",
            matched_booking_followup_state={
                "active": True,
                "service": "Маникюр",
                "datetime": "завтра",
                "name": "Динара",
                "last_question": "datetime",
            },
            matched_booking_followup_prompt=(
                "Понял, завтра по услуге «Маникюр». Подскажите, пожалуйста, точное время."
            ),
            matched_booking_followup_expected="time",
            matched_booking_filled_slots=("name",),
            slot_fill_followup_state={
                "active": True,
                "service": "Маникюр",
                "datetime": "завтра",
                "last_question": "datetime",
            },
            slot_fill_followup_prompt=(
                "Понял, завтра по услуге «Маникюр». Подскажите, пожалуйста, точное время."
            ),
            slot_fill_followup_expected="time",
            slot_fill_applied=("name",),
        )
    )

    assert resolution is not None
    assert resolution.source == "matched_expected_reply"
    assert resolution.reason_code == "timeout_owner_boundary_matched_expected_reply"
    assert resolution.recovery == "timeout_owner_boundary_collect"
    assert resolution.expected_reply_type == "time"
    assert resolution.expected_reply_reason == "policy_core_timeout_owner_boundary"
    assert resolution.filled_slots == ("name",)
    assert resolution.missing_slot == "datetime"


def test_timeout_owner_boundary_requires_booking_context() -> None:
    resolution = resolve_timeout_owner_boundary(
        TimeoutOwnerBoundaryInput(
            booking_active=False,
            current_goal=None,
            matched_booking_followup_state={
                "active": False,
                "service": "Маникюр",
                "last_question": "datetime",
            },
            matched_booking_followup_prompt="Подскажите, пожалуйста, точное время.",
            matched_booking_followup_expected="time",
            matched_booking_filled_slots=("name",),
        )
    )

    assert resolution is None


def test_timeout_owner_boundary_uses_resume_contract_when_other_sources_missing() -> None:
    resolution = resolve_timeout_owner_boundary(
        TimeoutOwnerBoundaryInput(
            booking_active=True,
            current_goal="booking",
            resume_contract_state={
                "active": True,
                "service": "Маникюр",
                "last_question": "datetime",
            },
            resume_contract_prompt="На какую дату и время вам удобно?",
            resume_contract_expected="time",
        )
    )

    assert resolution is not None
    assert resolution.source == "resume_contract"
    assert resolution.reason_code == "timeout_owner_boundary_resume_contract"
    assert resolution.recovery == "timeout_owner_boundary_collect"
    assert resolution.expected_reply_reason == "policy_core_timeout_owner_boundary"
    assert resolution.expected_reply_type == "time"
    assert resolution.missing_slot == "datetime"
    assert resolution.filled_slots == ()


def test_build_semantic_contract_view_prefers_canonical_specialist_referent() -> None:
    semantic_view = build_semantic_contract_view(
        semantic_contract={
            "subject_kind": "specialist",
            "capability": "bookability",
            "resolution_mode": "referent_followup",
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
            "referents": {
                "specialist": {
                    "value": "Айгерим",
                    "entity_id": "spec:aigerim",
                    "entity_type": "specialist",
                }
            },
            "entity_refs": [
                {
                    "entity_id": "spec:other",
                    "entity_type": "specialist",
                    "value": "Другой мастер",
                }
            ],
        },
        tool_args={"specialist_name": "Старое имя"},
        subject_kind="service",
        capability="pricing",
    )

    assert semantic_view.subject_kind == "specialist"
    assert semantic_view.capability == "bookability"
    assert semantic_view.resolution_mode == "referent_followup"
    assert semantic_view.pending_question_target == "specialist"
    assert semantic_view.active_question_relation == "referent_followup"
    assert semantic_view.specialist_name == "Айгерим"
    assert semantic_view.specialist_id is None


def test_specialist_followup_owner_preserves_canonical_referent_followup_contract() -> None:
    specialist_name, specialist_id = extract_specialist_preference(
        semantic_contract={
            "referents": {
                "specialist": {
                    "value": "Айгерим",
                    "entity_id": "spec:aigerim",
                    "entity_type": "specialist",
                }
            }
        }
    )
    semantic_view = build_semantic_contract_view(
        semantic_contract={
            "subject_kind": "specialist",
            "capability": "bookability",
            "resolution_mode": "referent_followup",
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
            "referents": {
                "specialist": {
                    "value": specialist_name,
                    "entity_id": "spec:aigerim",
                    "entity_type": "specialist",
                }
            },
        },
        tool_args={
            "specialist_name": specialist_name,
            "specialist_id": specialist_id,
        },
    )

    assert should_preserve_specialist_followup_owner(
        semantic_view=semantic_view,
        policy_goal="booking",
        policy_collect_slot=None,
        expected_reply_type="time",
    )
