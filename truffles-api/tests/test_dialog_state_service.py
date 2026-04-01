from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core import ConversationProjectionV1, DialogStateService, SemanticDecisionV1, TurnJournalV1, TurnPlanner
from tests import (
    build_test_policy_override_decision,
    build_test_reset_session_memory,
    build_test_sync_session_memory_interaction_state,
)


def test_dialog_state_service_projects_session_memory_interaction_state() -> None:
    projection, error = DialogStateService().project_session_memory_interaction_state(
        {
            "resume_slot": " Datetime ",
            "interaction_target": " TIME ",
            "interaction_relation": " Ask_About_Requested_Slot ",
            "interaction_owner": " booking   time  followup ",
            "grounded_referents": {
                "service": "  manicure deluxe  ",
                "branch": "  almaty center  ",
                "ignored": "skip",
            },
            "confirmation_state": {
                "required": True,
                "slot": " Name ",
                "value": "  Aigerim  ",
                "source": "  llm  ",
            },
            "degrade_reason": "  timeout  ",
        }
    )

    assert error is None
    assert projection == {
        "resume_slot": "datetime",
        "interaction_target": "time",
        "interaction_relation": "ask_about_requested_slot",
        "interaction_owner": "booking time followup",
        "grounded_referents": {
            "service": "manicure deluxe",
            "branch": "almaty center",
        },
        "confirmation_state": {
            "required": True,
            "slot": "name",
            "value": "Aigerim",
            "source": "llm",
        },
        "degrade_reason": "timeout",
    }


def test_dialog_state_service_rejects_interaction_state_without_resume_slot() -> None:
    projection, error = DialogStateService().project_session_memory_interaction_state(
        {
            "interaction_target": "time",
            "interaction_owner": "booking_time_followup",
        }
    )

    assert projection is None
    assert error == "interaction_state_resume_slot"


def test_dialog_state_service_projects_expected_reply_fields() -> None:
    service = DialogStateService()
    projections = service.project_expected_reply_projections(
        expected_reply_type="  time  ",
        expected_reply_reason="  booking_prompt  ",
    )

    assert projections.expected_reply_type == "time"
    assert projections.expected_reply_reason == "booking_prompt"


def test_dialog_state_service_projects_expected_reply_fields_without_mutating_other_projections() -> None:
    service = DialogStateService()
    base = service.normalize(
        {
            "projections": {
                "expected_reply_type": "service",
                "expected_reply_reason": "services_overview",
                "session_memory_interaction_state": {
                    "resume_slot": "service",
                    "interaction_owner": "question_contract",
                },
            }
        }
    ).projections

    projections = service.project_expected_reply_projections(
        base,
        expected_reply_type="  ",
        expected_reply_reason="  booking_interrupt  ",
    )

    assert projections.expected_reply_type is None
    assert projections.expected_reply_reason == "booking_interrupt"
    assert projections.session_memory_interaction_state.resume_slot == "service"
    assert projections.session_memory_interaction_state.interaction_owner == "question_contract"


def test_dialog_state_service_omits_empty_pending_question_contract_projection() -> None:
    service = DialogStateService()
    dialog_state = service.normalize({})

    projected = service.project_pending_question_contract(dialog_state.pending_question_contract)

    assert projected is None


def test_dialog_state_service_projects_context_pending_question_contract_from_canonical_state() -> None:
    service = DialogStateService()

    projected = service.project_context_pending_question_contract(
        {
            "expected_reply_type": "service_choice",
            "expected_reply_reason": "stale_projection",
            "context_manager": {
                "canonical_dialog_state": {
                    "pending_question_contract": {
                        "expected_reply_type": " time ",
                        "reason": " booking_interrupt ",
                        "next_question": " datetime ",
                        "open_questions": [" datetime "],
                    }
                }
            },
        }
    )

    assert projected == {
        "expected_reply_type": "time",
        "reason": "booking_interrupt",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }


def test_dialog_state_service_load_runtime_payload_prefers_canonical_question_contract_over_legacy_context() -> None:
    service = DialogStateService()

    loaded = service.load_runtime_payload(
        {
            "expected_reply_type": "time",
            "expected_reply_reason": "collect:datetime",
            "current_goal": "booking",
            "consultant_runtime": {
                "schema_version": "consultant_runtime.v1",
                "dialog_state": {
                    "schema_version": "dialog_state.v1",
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "reason": "collect:name",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "generic_info_interrupt",
                        "next_question": "name",
                        "open_questions": ["name"],
                    },
                    "projections": {
                        "expected_reply_type": "name",
                        "expected_reply_reason": "collect:name",
                    },
                },
                "pending_question_contract": {
                    "expected_reply_type": "name",
                    "reason": "collect:name",
                    "pending_question_act": "ask_about_requested_slot",
                    "pending_question_target": "time",
                    "active_question_relation": "generic_info_interrupt",
                    "next_question": "name",
                    "open_questions": ["name"],
                },
                "expected_reply_type": "name",
                "expected_reply_reason": "collect:name",
                "current_goal": "booking",
            },
        }
    )

    assert loaded["expected_reply_type"] == "name"
    assert loaded["expected_reply_reason"] == "collect:name"
    assert loaded["current_goal"] == "booking"
    assert loaded["dialog_state"].pending_question_contract.next_question == "name"
    assert loaded["dialog_state"].pending_question_contract.active_question_relation == "generic_info_interrupt"


def test_dialog_state_service_load_runtime_payload_reprojects_stale_legacy_fields_from_semantic_state() -> None:
    service = DialogStateService()

    loaded = service.load_runtime_payload(
        {
            "consultant_runtime": {
                "schema_version": "consultant_runtime.v1",
                "dialog_state": {
                    "schema_version": "dialog_state.v1",
                    "semantic_state": {
                        "schema_version": "canonical_semantic_state.v1",
                        "materialized_frame": {
                            "schema_version": "semantic_frame.v2",
                            "user_goal": "booking",
                            "requested_effect": "collect_missing_input",
                            "subject": {"kind": "service", "value": "Маникюр"},
                            "referents": {
                                "service": {
                                    "value": "Маникюр",
                                    "entity_id": "svc:manicure",
                                    "entity_type": "service",
                                    "source_ref": "memory",
                                }
                            },
                            "constraints": {},
                            "preferences": {},
                            "continuation": {
                                "expected_reply_type": "time",
                                "reason": "collect:datetime",
                                "pending_question_act": "ask_about_requested_slot",
                                "pending_question_target": "time",
                                "active_question_relation": "ask_about_requested_slot",
                                "next_question": "datetime",
                                "open_questions": ["datetime"],
                            },
                            "capability_selection": {"capability": "bookability"},
                            "needs_human": False,
                            "reason": "collect_datetime",
                        },
                        "event_log": [],
                    },
                    "current_referents": {"service": "Педикюр"},
                    "pending_question_contract": {
                        "expected_reply_type": "name",
                        "reason": "collect:name",
                        "next_question": "name",
                        "open_questions": ["name"],
                    },
                    "projections": {
                        "expected_reply_type": "name",
                        "expected_reply_reason": "collect:name",
                    },
                    "meta": {
                        "current_goal": "handoff",
                        "semantic_contract": {"contract_version": "semantic_contract.v1"},
                    },
                },
            }
        }
    )

    dialog_state = loaded["dialog_state"]
    assert loaded["current_goal"] == "booking"
    assert dialog_state.current_referents.service == "Маникюр"
    assert dialog_state.pending_question_contract.expected_reply_type == "time"
    assert dialog_state.pending_question_contract.next_question == "datetime"
    assert dialog_state.projections.expected_reply_type == "time"
    assert dialog_state.meta["current_goal"] == "booking"
    assert dialog_state.meta["semantic_contract"]["capability"] == "bookability"


def test_dialog_state_service_projects_context_goal_and_question_from_runtime_semantic_state() -> None:
    service = DialogStateService()
    context = {
        "consultant_runtime": {
            "schema_version": "consultant_runtime.v1",
            "dialog_state": {
                "schema_version": "dialog_state.v1",
                "semantic_state": {
                    "schema_version": "canonical_semantic_state.v1",
                    "materialized_frame": {
                        "schema_version": "semantic_frame.v2",
                        "user_goal": "booking",
                        "requested_effect": "collect_missing_input",
                        "subject": {"kind": "service", "value": "Маникюр"},
                        "referents": {},
                        "constraints": {},
                        "preferences": {},
                        "continuation": {
                            "expected_reply_type": "time",
                            "reason": "collect:datetime",
                            "next_question": "datetime",
                            "open_questions": ["datetime"],
                        },
                        "capability_selection": {"capability": "bookability"},
                        "needs_human": False,
                        "reason": "collect_datetime",
                    },
                    "event_log": [],
                },
                "pending_question_contract": {
                    "expected_reply_type": "name",
                    "reason": "collect:name",
                    "next_question": "name",
                    "open_questions": ["name"],
                },
                "meta": {"current_goal": "handoff"},
            },
            "current_goal": "handoff",
        },
        "current_goal": "handoff",
    }

    assert service.project_context_current_goal(context) == "booking"
    assert service.project_context_pending_question_contract(context) == {
        "expected_reply_type": "time",
        "reason": "collect:datetime",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }


def test_dialog_state_service_projects_session_memory_pending_question_contract() -> None:
    service = DialogStateService()

    projected = service.project_session_memory_pending_question_contract(
        {
            "last_question_type": " service_choice ",
            "pending_question_contract": {
                "expected_reply_type": " time ",
                "reason": " booking_interrupt ",
                "next_question": " datetime ",
                "open_questions": [" datetime "],
            },
        }
    )

    assert projected == {
        "expected_reply_type": "time",
        "reason": "booking_interrupt",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }


def test_expected_reply_context_sync_result_carries_canonical_pending_question_contract() -> None:
    service = DialogStateService()
    now = datetime.now(timezone.utc)

    result = service.build_expected_reply_context_sync_result(
        {
            "context_manager": {
                "message_count": 7,
                "current_goal": "booking",
            },
            "booking": {
                "active": True,
                "service": "Маникюр",
                "last_question": "datetime",
            },
        },
        expected_reply_type=" time ",
        reason=" booking_prompt ",
        now=now,
    )

    assert result.pending_question_contract == {
        "expected_reply_type": "time",
        "reason": "booking_prompt",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }


def test_dialog_state_service_builds_collect_owner_state() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "master_query",
            "action": "collect",
            "tool_action": "collect",
            "pack_refs": ["master"],
            "next_question": "service",
            "open_questions": ["service"],
            "subject_kind": "service",
            "resolution_mode": "clarify_missing_subject",
        },
        interaction_owner="turn_planner.safe_master_query_collect.v1",
        interaction_relation="turn_planner_safe_master_query_collect",
    )

    state = DialogStateService().build_collect_owner_state(
        decision=decision,
        expected_reply_type="service_choice",
        expected_reply_reason="service_clarify",
        grounded_referents={"branch": "almaty-center"},
        owner_cutover="turn_planner.safe_master_query_collect.v1",
    )

    assert state.pending_question_contract.expected_reply_type == "service_choice"
    assert state.pending_question_contract.reason == "service_clarify"
    assert state.pending_question_contract.pending_question_act is None
    assert state.pending_question_contract.pending_question_target is None
    assert state.pending_question_contract.next_question == "service"
    assert state.pending_question_contract.open_questions == ["service"]
    assert state.interaction_state.resume_slot == "service"
    assert state.interaction_state.interaction_target is None
    assert state.interaction_state.interaction_owner == "turn_planner.safe_master_query_collect.v1"
    assert state.interaction_state.grounded_referents == {"branch": "almaty-center"}
    assert state.current_referents.branch == "almaty-center"
    assert state.projections.expected_reply_type == "service_choice"
    assert state.projections.expected_reply_reason == "service_clarify"
    assert state.meta["owner_cutover"] == "turn_planner.safe_master_query_collect.v1"


def test_dialog_state_service_builds_booking_prompt_owner_state() -> None:
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "reason": "booking_prompt",
            "goal": "booking",
            "slots": {"service": "Маникюр"},
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="turn_planner.safe_booking_prompt_owner.v1",
        interaction_relation="turn_planner_safe_booking_prompt_owner",
    )

    state = DialogStateService().build_collect_owner_state(
        decision=decision,
        expected_reply_type="time",
        expected_reply_reason="booking_prompt",
        grounded_referents={"service": "Маникюр"},
        owner_cutover="turn_planner.safe_booking_prompt_owner.v1",
    )

    assert state.pending_question_contract.expected_reply_type == "time"
    assert state.pending_question_contract.reason == "booking_prompt"
    assert state.pending_question_contract.pending_question_act is None
    assert state.pending_question_contract.pending_question_target is None
    assert state.pending_question_contract.next_question == "datetime"
    assert state.pending_question_contract.open_questions == ["datetime"]
    assert state.interaction_state.resume_slot == "datetime"
    assert state.interaction_state.interaction_target is None
    assert state.interaction_state.interaction_owner == "turn_planner.safe_booking_prompt_owner.v1"
    assert state.current_referents.service == "Маникюр"
    assert state.projections.expected_reply_type == "time"
    assert state.projections.expected_reply_reason == "booking_prompt"
    assert state.meta["owner_cutover"] == "turn_planner.safe_booking_prompt_owner.v1"


def test_dialog_state_service_builds_collect_owner_booking_payload() -> None:
    service = DialogStateService()
    existing_booking = {
        "active": False,
        "started_at": "2026-03-16T10:00:00+00:00",
        "service": " Маникюр ",
        "last_question": "service",
    }
    slot_values = {
        "service": "Педикюр",
        "datetime": " завтра вечером ",
        "ignored": "skip",
    }

    payload = service.build_collect_owner_booking_payload(
        existing_booking=existing_booking,
        now=datetime(2026, 3, 17, 6, 0, tzinfo=timezone.utc),
        last_question=" datetime ",
        slot_values=slot_values,
    )

    existing_booking["service"] = "changed"
    slot_values["datetime"] = "changed"

    assert payload == {
        "active": True,
        "started_at": "2026-03-16T10:00:00+00:00",
        "service": "Маникюр",
        "datetime": "завтра вечером",
        "last_question": "datetime",
    }


def test_dialog_state_service_sets_context_booking_payload_with_detached_copy() -> None:
    service = DialogStateService()
    context = {
        "booking": {"service": "old"},
        "other": {"keep": True},
    }
    payload = {
        "service": " Маникюр ",
        "datetime": " завтра 18:00 ",
        "last_question": " datetime ",
    }

    updated = service.set_context_booking_payload(
        context,
        payload,
        key="booking",
    )
    cleared = service.set_context_booking_payload(
        updated,
        {"last_question": " "},
        key="booking",
    )

    payload["service"] = "changed"

    assert updated["booking"] == {
        "active": True,
        "service": "Маникюр",
        "datetime": "завтра 18:00",
        "last_question": "datetime",
    }
    assert context["booking"] == {"service": "old"}
    assert updated["other"] == {"keep": True}
    assert "booking" not in cleared


def test_dialog_state_service_sets_expected_reply_context_fields_and_clears_stale_values() -> None:
    service = DialogStateService()
    context = {
        "expected_reply_type": " name ",
        "expected_reply_reason": " old_reason ",
        "session_memory": {
            "active_goal": "booking",
        },
    }

    updated = service.set_expected_reply_context_fields(
        context,
        expected_reply_type="  time  ",
        expected_reply_reason="  booking_prompt  ",
    )
    cleared = service.set_expected_reply_context_fields(
        updated,
        expected_reply_type=" ",
        expected_reply_reason=None,
    )

    updated["session_memory"]["active_goal"] = "info"

    assert updated["expected_reply_type"] == "time"
    assert updated["expected_reply_reason"] == "booking_prompt"
    assert "expected_reply_type" not in cleared
    assert "expected_reply_reason" not in cleared
    assert context["session_memory"]["active_goal"] == "booking"


def test_dialog_state_service_updates_session_memory_on_question_with_detached_goal_stack() -> None:
    service = DialogStateService()
    memory = {
        "unanswered_questions": [" name ", " "],
        "goal_stack": ["info", "booking", "booking"],
    }

    updated = service.update_session_memory_on_question(
        memory,
        expected_reply_type="  time  ",
        active_goal=" consult ",
    )
    memory["goal_stack"].append("other")
    memory["unanswered_questions"].append("service_choice")

    assert updated["last_question_type"] == "time"
    assert updated["unanswered_questions"] == ["name", "time"]
    assert updated["active_goal"] == "consult"
    assert updated["goal_stack"] == ["booking", "booking", "consult"]
    assert memory["goal_stack"] == ["info", "booking", "booking", "other"]


def test_dialog_state_service_updates_session_memory_on_answer_and_clears_expected_reply() -> None:
    service = DialogStateService()
    memory = {
        "last_question_type": "time",
        "unanswered_questions": ["time", "name"],
        "pending_slots": {"datetime": "2026-02-12 18:00"},
    }

    answered = service.update_session_memory_on_answer(
        memory,
        expected_reply_type="  name  ",
        value=" Лена ",
    )
    cleared, changed = service.clear_session_memory_expected_reply(
        answered,
        expected_reply_type=" time ",
    )

    memory["pending_slots"]["datetime"] = "2026-02-13 09:00"

    assert answered["pending_slots"] == {
        "datetime": "2026-02-12 18:00",
        "name": "Лена",
    }
    assert answered["unanswered_questions"] == ["time"]
    assert changed is True
    assert cleared["pending_slots"] == {"name": "Лена"}
    assert cleared["unanswered_questions"] == []
    assert "last_question_type" not in cleared
    assert memory["pending_slots"] == {"datetime": "2026-02-13 09:00"}


def test_dialog_state_service_updates_session_memory_goal_without_duplicate_tail() -> None:
    service = DialogStateService()

    updated = service.update_session_memory_goal(
        {"goal_stack": ["booking", "info", "info"]},
        active_goal=" info ",
    )

    assert updated["active_goal"] == "info"
    assert updated["goal_stack"] == ["booking", "info", "info"]


def test_dialog_state_service_touches_and_expires_session_memory_payload() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 16, 17, 0, tzinfo=timezone.utc)

    touched = service.touch_session_memory_payload(
        {"active_goal": "booking"},
        now=now,
        default_ttl_hours="oops",
    )

    assert touched == {
        "active_goal": "booking",
        "last_updated_at": now.isoformat(),
        "ttl_hours": 24,
    }
    assert (
        service.is_session_memory_expired(
            {
                "last_updated_at": (now - timedelta(hours=25)).isoformat(),
                "ttl_hours": "oops",
            },
            now=now,
            default_ttl_hours=24,
        )
        is True
    )
    assert (
        service.is_session_memory_expired(
            {
                "last_updated_at": (now - timedelta(hours=1)).isoformat(),
                "ttl_hours": "oops",
            },
            now=now,
            default_ttl_hours=24,
        )
        is False
    )
    assert (
        service.is_session_memory_expired(
            {"last_updated_at": "not-a-datetime"},
            now=now,
            default_ttl_hours=24,
        )
        is True
    )


def test_dialog_state_service_syncs_session_memory_interaction_state_with_freshness() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 16, 18, 15, tzinfo=timezone.utc)

    updated, changed = service.sync_session_memory_interaction_state(
        {"active_goal": "booking"},
        interaction_state={
            "resume_slot": " Name ",
            "interaction_target": "time",
            "interaction_relation": "slot_compare",
        },
        now=now,
        default_ttl_hours=24,
    )
    untouched, untouched_changed = service.sync_session_memory_interaction_state(
        updated,
        interaction_state={
            "resume_slot": "name",
            "interaction_target": "time",
            "interaction_relation": "slot_compare",
        },
        now=now + timedelta(minutes=5),
        default_ttl_hours=24,
    )

    assert changed is True
    assert updated["interaction_state"] == {
        "resume_slot": "name",
        "interaction_target": "time",
        "interaction_relation": "slot_compare",
    }
    assert updated["last_updated_at"] == now.isoformat()
    assert updated["ttl_hours"] == 24
    assert untouched_changed is False
    assert untouched == updated


def test_dialog_state_service_normalizes_session_memory_payload() -> None:
    service = DialogStateService()
    payload = {
        "mode": "  remember  ",
        "summary": "  booking in progress  ",
        "last_updated": "  2026-03-16T15:00:00+00:00  ",
        "last_updated_at": " 2026-03-16T15:05:00+00:00 ",
        "active_goal": " booking ",
        "last_question_type": " time ",
        "ttl": "7",
        "ttl_hours": "24",
        "goal_stack": ["info", None, " booking ", " ", "consult"],
        "unanswered_questions": [" time ", 1, " name "],
        "slots": {"service": "Маникюр", "branch": "Алматы"},
        "pending_slots": {" datetime ": " 15:00 ", "": "skip"},
        "interaction_state": {
            "resume_slot": " Datetime ",
            "interaction_target": " TIME ",
            "interaction_relation": " Ask_About_Requested_Slot ",
            "interaction_owner": " booking   time  followup ",
        },
    }

    normalized, error = service.normalize_session_memory_payload(payload)
    payload["goal_stack"].append("other")
    payload["pending_slots"][" datetime "] = "18:00"

    assert error is None
    assert normalized == {
        "mode": "remember",
        "summary": "booking in progress",
        "last_updated": "2026-03-16T15:00:00+00:00",
        "last_updated_at": "2026-03-16T15:05:00+00:00",
        "active_goal": "booking",
        "ttl": 7,
        "ttl_hours": 24,
        "goal_stack": ["info", "booking", "consult"],
        "unanswered_questions": ["time", "name"],
        "slots": {"service": "Маникюр", "branch": "Алматы"},
        "pending_slots": {"datetime": "15:00"},
        "interaction_state": {
            "resume_slot": "datetime",
            "interaction_target": "time",
            "interaction_relation": "ask_about_requested_slot",
            "interaction_owner": "booking time followup",
        },
        "pending_question_contract": {
            "expected_reply_type": "time",
        },
    }
    assert normalized["goal_stack"] == ["info", "booking", "consult"]
    assert normalized["pending_slots"] == {"datetime": "15:00"}


def test_dialog_state_service_reports_session_memory_normalization_errors() -> None:
    service = DialogStateService()

    invalid_type, invalid_type_error = service.normalize_session_memory_payload(None)
    invalid_ttl, invalid_ttl_error = service.normalize_session_memory_payload({"ttl_hours": "oops"})
    invalid_interaction, invalid_interaction_error = service.normalize_session_memory_payload(
        {"interaction_state": {"interaction_target": "time"}}
    )

    assert invalid_type == {}
    assert invalid_type_error == "invalid_type"
    assert invalid_ttl == {}
    assert invalid_ttl_error == "ttl_hours_type"
    assert invalid_interaction == {}
    assert invalid_interaction_error == "interaction_state_resume_slot"


def test_dialog_state_service_sets_and_clears_session_memory_context_payload() -> None:
    service = DialogStateService()
    payload = {
        "active_goal": "booking",
        "interaction_state": {
            "resume_slot": "service",
            "interaction_owner": "question_contract",
        },
    }

    updated = service.set_context_session_memory(
        {"session_memory": {"active_goal": "stale"}},
        payload,
        key="session_memory",
    )
    payload["interaction_state"]["resume_slot"] = "name"

    assert updated["session_memory"] == {
        "active_goal": "booking",
        "interaction_state": {
            "resume_slot": "service",
            "interaction_owner": "question_contract",
        },
    }

    cleared = service.set_context_session_memory(updated, {}, key="session_memory")

    assert "session_memory" not in cleared


def test_dialog_state_service_sets_and_clears_context_manager_payload() -> None:
    service = DialogStateService()
    payload = {
        "current_goal": "booking",
        "canonical_dialog_state": {
            "owner_id": "context_manager.dialog_state.v1",
            "version": "v1",
        },
    }

    updated = service.set_context_manager_payload(
        {"context_manager": {"current_goal": "stale"}},
        payload,
        key="context_manager",
    )
    payload["canonical_dialog_state"]["version"] = "changed"

    assert updated["context_manager"] == {
        "current_goal": "booking",
        "canonical_dialog_state": {
            "owner_id": "context_manager.dialog_state.v1",
            "version": "v1",
        },
    }

    cleared = service.set_context_manager_payload(updated, {}, key="context_manager")

    assert "context_manager" not in cleared


def test_dialog_state_service_increments_context_manager_message_count() -> None:
    service = DialogStateService()

    updated, count = service.increment_context_manager_message_count(
        {
            "message_count": " 4 ",
            "current_goal": "booking",
        }
    )
    assert count == 5
    assert updated == {
        "message_count": 5,
        "current_goal": "booking",
    }

    empty_updated, empty_count = service.increment_context_manager_message_count({})
    assert empty_count == 1
    assert empty_updated == {"message_count": 1}


def test_dialog_state_service_captures_pending_resume_payload_as_isolated_snapshot() -> None:
    service = DialogStateService()
    context = {
        "context_manager": {"current_goal": "booking"},
        "expected_reply_type": "  time  ",
        "expected_reply_reason": "  booking_prompt  ",
        "intent_queue": ["booking"],
        "booking": {"active": True, "service": "Маникюр"},
        "session_memory": {
            "active_goal": "booking",
            "interaction_state": {
                "resume_slot": " datetime ",
                "interaction_target": " time ",
                "interaction_owner": " llm_policy_core ",
            },
        },
        "last_service_hint": "  Маникюр  ",
        "last_service_hint_at": " 2026-03-15T10:00:00+00:00 ",
    }

    payload = service.capture_pending_resume_payload(
        context,
        snapshot_keys={
            "context_manager",
            "expected_reply_type",
            "expected_reply_reason",
            "intent_queue",
            "booking",
            "session_memory",
            "last_service_hint",
            "last_service_hint_at",
        },
    )

    context["context_manager"]["current_goal"] = "changed"
    context["intent_queue"].append("handoff")
    context["booking"]["service"] = "Педикюр"
    context["session_memory"]["interaction_state"]["resume_slot"] = "name"

    assert payload["context_manager"]["current_goal"] == "booking"
    assert payload["expected_reply_type"] == "time"
    assert payload["expected_reply_reason"] == "booking_prompt"
    assert payload["intent_queue"] == ["booking"]
    assert payload["booking"]["service"] == "Маникюр"
    assert payload["session_memory"]["interaction_state"]["resume_slot"] == "datetime"
    assert payload["last_service_hint"] == "Маникюр"
    assert payload["last_service_hint_at"] == "2026-03-15T10:00:00+00:00"


def test_dialog_state_service_captures_pending_resume_payload_from_runtime_canonical_state() -> None:
    service = DialogStateService()
    context = {
        "consultant_runtime": {
            "schema_version": "consultant_runtime.v1",
            "dialog_state": {
                "schema_version": "dialog_state.v1",
                "pending_question_contract": {
                    "expected_reply_type": " time ",
                    "reason": " collect:datetime ",
                    "next_question": " datetime ",
                    "open_questions": [" datetime "],
                },
                "projections": {
                    "expected_reply_type": "name",
                    "expected_reply_reason": "stale_projection",
                },
                "meta": {"current_goal": " booking "},
            },
            "booking": {"active": True, "service": "Маникюр", "last_question": "datetime"},
        }
    }

    payload = service.capture_pending_resume_payload(
        context,
        snapshot_keys={
            "context_manager",
            "expected_reply_type",
            "expected_reply_reason",
            "booking",
        },
    )

    assert payload["context_manager"]["current_goal"] == "booking"
    assert payload["context_manager"]["canonical_dialog_state"]["pending_question_contract"] == {
        "expected_reply_type": "time",
        "reason": "collect:datetime",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }
    assert payload["expected_reply_type"] == "time"
    assert payload["expected_reply_reason"] == "collect:datetime"
    assert payload["booking"] == {"active": True, "service": "Маникюр", "last_question": "datetime"}


def test_dialog_state_service_restores_pending_resume_payload() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 15, 18, 40, tzinfo=timezone.utc)

    restored = service.restore_pending_resume_payload(
        {
            "context_manager": {
                "canonical_dialog_state": {
                    "pending_question_contract": {
                        "expected_reply_type": "  name  ",
                        "reason": "  booking_prompt  ",
                    }
                }
            },
            "intent_queue": ["booking", "check_booking"],
            "booking": {"active": True, "service": "Маникюр"},
            "session_memory": {
                "active_goal": "booking",
                "interaction_state": {
                    "resume_slot": " Name ",
                    "interaction_target": " time ",
                    "interaction_relation": " slot_compare ",
                    "interaction_owner": " booking name ",
                },
            },
            "service_hint": "  Маникюр  ",
            "service_hint_at": " 2026-03-15T10:00:00+00:00 ",
        },
        now=now,
    )

    assert restored["expected_reply_type"] == "name"
    assert restored["expected_reply_reason"] == "booking_prompt"
    assert restored["intent_queue"] == ["booking", "check_booking"]
    assert restored["booking"]["service"] == "Маникюр"
    assert restored["session_memory"]["interaction_state"]["resume_slot"] == "name"
    assert restored["session_memory"]["last_updated_at"] == now.isoformat()
    assert restored["last_service_hint"] == "Маникюр"
    assert restored["last_service_hint_at"] == "2026-03-15T10:00:00+00:00"
    assert restored["re_entry_required"]["reason"] == "pending_resume"


def test_dialog_state_service_restore_pending_resume_payload_ignores_noncanonical_expected_reply() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 15, 18, 40, tzinfo=timezone.utc)

    restored = service.restore_pending_resume_payload(
        {
            "expected_reply_type": "  name  ",
            "expected_reply_reason": "  booking_prompt  ",
            "session_memory": {
                "active_goal": "booking",
                "last_question_type": " time ",
            },
        },
        now=now,
    )

    assert "expected_reply_type" not in restored
    assert "expected_reply_reason" not in restored
    assert restored["session_memory"]["active_goal"] == "booking"


def test_dialog_state_service_restores_pending_resume_payload_from_canonical_question_contract() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 15, 18, 40, tzinfo=timezone.utc)

    restored = service.restore_pending_resume_payload(
        {
            "expected_reply_type": "service_choice",
            "expected_reply_reason": "stale_projection",
            "context_manager": {
                "current_goal": "booking",
                "canonical_dialog_state": {
                    "pending_question_contract": {
                        "expected_reply_type": " time ",
                        "reason": " booking_interrupt ",
                        "next_question": " datetime ",
                        "open_questions": [" datetime "],
                    }
                },
            },
            "booking": {"active": True, "service": "Маникюр", "last_question": "datetime"},
            "session_memory": {
                "active_goal": "booking",
                "last_question_type": " time ",
                "pending_question_contract": {
                    "expected_reply_type": " time ",
                    "reason": " booking_interrupt ",
                    "next_question": " datetime ",
                },
            },
        },
        now=now,
    )

    assert restored["expected_reply_type"] == "time"
    assert restored["expected_reply_reason"] == "booking_interrupt"
    assert restored["context_manager"]["canonical_dialog_state"]["pending_question_contract"] == {
        "expected_reply_type": "time",
        "reason": "booking_interrupt",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }
    assert restored["session_memory"]["pending_question_contract"] == {
        "expected_reply_type": "time",
        "reason": "booking_interrupt",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }
    assert restored["session_memory"]["last_updated_at"] == now.isoformat()


def test_dialog_state_service_derives_pending_resume_boundary_payload() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 15, 18, 41, tzinfo=timezone.utc)

    payload = service.derive_pending_booking_resume_boundary_payload(
        {
            "pending_resume": {
                "context_manager": {"current_goal": "booking"},
                "expected_reply_reason": " booking_interrupt ",
                "booking": {
                    "active": True,
                    "service": "Маникюр",
                    "last_question": "datetime",
                },
                "session_memory": {
                    "active_goal": "booking",
                    "last_question_type": " time ",
                },
            }
        },
        now=now,
        prompt_builder=lambda expected_reply_type: {
            "service_choice": "Какая услуга вас интересует?",
            "time": "Когда вам удобно?",
            "name": "Подскажите, как к вам обращаться?",
        }.get(expected_reply_type),
    )

    assert payload == {
        "booking_state": {
            "active": True,
            "service": "Маникюр",
            "last_question": "datetime",
        },
        "expected_reply_type": "time",
        "prompt": "Когда вам удобно?",
        "resume_slot": "datetime",
    }


def test_dialog_state_service_derives_pending_resume_boundary_from_canonical_question_contract() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 15, 18, 41, tzinfo=timezone.utc)

    payload = service.derive_pending_booking_resume_boundary_payload(
        {
            "pending_resume": {
                "context_manager": {
                    "current_goal": "booking",
                    "canonical_dialog_state": {
                        "pending_question_contract": {
                            "expected_reply_type": " time ",
                            "reason": " booking_interrupt ",
                            "next_question": " datetime ",
                            "open_questions": [" datetime "],
                        }
                    },
                },
                "booking": {
                    "active": True,
                    "service": "Маникюр",
                    "last_question": "datetime",
                },
                "session_memory": {
                    "active_goal": "booking",
                    "last_question_type": "service_choice",
                },
            }
        },
        now=now,
        prompt_builder=lambda expected_reply_type: {
            "service_choice": "Какая услуга вас интересует?",
            "time": "Когда вам удобно?",
            "name": "Подскажите, как к вам обращаться?",
        }.get(expected_reply_type),
    )

    assert payload == {
        "booking_state": {
            "active": True,
            "service": "Маникюр",
            "last_question": "datetime",
        },
        "expected_reply_type": "time",
        "prompt": "Когда вам удобно?",
        "resume_slot": "datetime",
    }


def test_dialog_state_service_derives_pending_resume_boundary_from_active_booking_gap() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 15, 18, 42, tzinfo=timezone.utc)

    payload = service.derive_pending_booking_resume_boundary_payload(
        {
            "context_manager": {"current_goal": "booking"},
            "booking": {
                "active": True,
            },
        },
        now=now,
        prompt_builder=lambda expected_reply_type: {
            "service_choice": "Какая услуга вас интересует?",
            "time": "Когда вам удобно?",
            "name": "Подскажите, как к вам обращаться?",
        }.get(expected_reply_type),
    )

    assert payload == {
        "booking_state": {
            "active": True,
            "last_question": "service",
        },
        "expected_reply_type": "service_choice",
        "prompt": "Какая услуга вас интересует?",
        "resume_slot": "service",
    }


def test_dialog_state_service_normalizes_re_entry_required_payload() -> None:
    payload = DialogStateService().normalize_re_entry_required(
        {
            "required": True,
            "reason": "  pending_resume  ",
            "set_at": " 2026-03-15T18:40:00+00:00 ",
            "ignored": "skip",
        }
    )

    assert payload == {
        "required": True,
        "reason": "pending_resume",
        "set_at": "2026-03-15T18:40:00+00:00",
    }


def test_dialog_state_service_sets_and_clears_re_entry_required_payload() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 15, 18, 41, tzinfo=timezone.utc)

    required_payload = service.set_re_entry_required(reason="  pending_resume  ", now=now)
    cleared_payload = service.clear_re_entry_required(reason="  booking_interrupt  ", now=now)

    assert required_payload == {
        "required": True,
        "reason": "pending_resume",
        "set_at": now.isoformat(),
    }
    assert cleared_payload == {
        "required": False,
        "reason": "booking_interrupt",
        "cleared_at": now.isoformat(),
    }
    assert service.is_re_entry_required(required_payload) is True
    assert service.is_re_entry_required(cleared_payload) is False


def test_dialog_state_service_sets_and_clears_re_entry_required_context_payload() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 15, 19, 10, tzinfo=timezone.utc)

    updated = service.set_context_re_entry_required(
        {"re_entry_required": {"required": False, "reason": "stale"}},
        reason="  pending_resume  ",
        now=now,
        key="re_entry_required",
    )

    assert updated["re_entry_required"] == {
        "required": True,
        "reason": "pending_resume",
        "set_at": now.isoformat(),
    }

    cleared = service.clear_context_re_entry_required(
        updated,
        reason="  booking_interrupt  ",
        now=now,
        key="re_entry_required",
    )

    assert cleared["re_entry_required"] == {
        "required": False,
        "reason": "booking_interrupt",
        "cleared_at": now.isoformat(),
    }


def test_dialog_state_service_normalizes_confirmation_payloads() -> None:
    service = DialogStateService()

    handover = service.normalize_handover_confirmation(
        {
            "asked_at": " 2026-03-15T18:40:00+00:00 ",
            "status": " pending ",
            "trigger_type": " low_confidence ",
            "trigger_value": " low_confidence ",
            "user_message": "  help me  ",
        }
    )
    reengage = service.normalize_reengage_confirmation(
        {
            "asked_at": " 2026-03-15T18:40:00+00:00 ",
            "booking_messages": [" запишите меня ", " ", "на завтра"],
        }
    )
    asr = service.normalize_asr_confirmation(
        {
            "asked_at": " 2026-03-15T18:40:00+00:00 ",
            "transcript": "  маникюр завтра  ",
            "attempt": 2,
        }
    )

    assert handover == {
        "asked_at": "2026-03-15T18:40:00+00:00",
        "status": "pending",
        "trigger_type": "low_confidence",
        "trigger_value": "low_confidence",
        "user_message": "help me",
    }
    assert reengage == {
        "asked_at": "2026-03-15T18:40:00+00:00",
        "booking_messages": ["запишите меня", "на завтра"],
    }
    assert asr == {
        "asked_at": "2026-03-15T18:40:00+00:00",
        "transcript": "маникюр завтра",
        "attempt": 2,
    }


def test_dialog_state_service_checks_confirmation_windows() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 15, 18, 50, tzinfo=timezone.utc)

    assert service.is_confirmation_active(
        {"asked_at": "2026-03-15T18:45:00+00:00"},
        now=now,
        ttl_minutes=10,
    )
    assert service.is_confirmation_active(
        {"asked_at": "2026-03-15T18:45:00"},
        now=now,
        ttl_minutes=10,
    )
    assert (
        service.is_confirmation_active(
            {"asked_at": "2026-03-15T18:30:00+00:00"},
            now=now,
            ttl_minutes=10,
        )
        is False
    )


def test_dialog_state_service_gets_asr_inflight_and_detects_expiry() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 15, 18, 50, tzinfo=timezone.utc)

    active, active_expired = service.get_asr_inflight(
        {
            "started_at": " 2026-03-15T18:49:00+00:00 ",
            "expires_at": " 2026-03-15T18:55:00+00:00 ",
        },
        now=now,
    )
    expired, expired_flag = service.get_asr_inflight(
        {
            "started_at": "2026-03-15T18:40:00+00:00",
            "expires_at": "2026-03-15T18:45:00+00:00",
        },
        now=now,
    )

    assert active == {
        "started_at": "2026-03-15T18:49:00+00:00",
        "expires_at": "2026-03-15T18:55:00+00:00",
    }
    assert active_expired is False
    assert expired is None
    assert expired_flag is True


def test_dialog_state_service_normalizes_style_reference_pending_payload() -> None:
    service = DialogStateService()
    payload = {
        "reason": " photo_only ",
        "created_at": " 2026-03-15T18:40:00+00:00 ",
        "expires_at": " 2026-03-15T18:55:00+00:00 ",
        "media": {
            "media_type": " photo ",
            "raw_type": " image ",
            "mime": " image/jpeg ",
            "size_bytes": 123,
            "duration_seconds": 0,
            "url": " https://example.com/raw.jpg ",
            "file_name": " style.jpg ",
            "caption": " reference ",
            "ptt": False,
        },
        "storage_path": " /tmp/stored.jpg ",
        "public_url": " https://example.com/stored.jpg ",
        "public_url_expires_at": " 2026-03-15T19:10:00+00:00 ",
        "sha256": " abc123 ",
    }

    normalized = service.set_style_reference_pending(payload)
    payload["media"]["url"] = "changed"

    assert normalized == {
        "reason": "photo_only",
        "created_at": "2026-03-15T18:40:00+00:00",
        "expires_at": "2026-03-15T18:55:00+00:00",
        "media": {
            "media_type": "photo",
            "raw_type": "image",
            "mime": "image/jpeg",
            "size_bytes": 123,
            "duration_seconds": 0,
            "url": "https://example.com/raw.jpg",
            "file_name": "style.jpg",
            "caption": "reference",
            "ptt": False,
        },
        "storage_path": "/tmp/stored.jpg",
        "public_url": "https://example.com/stored.jpg",
        "public_url_expires_at": "2026-03-15T19:10:00+00:00",
        "sha256": "abc123",
    }
    assert normalized["media"]["url"] == "https://example.com/raw.jpg"


def test_dialog_state_service_normalizes_memory_profile_and_prunes_expired_items() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 15, 18, 50, tzinfo=timezone.utc)
    payload = {
        "version": 0,
        "ttl_days": 0,
        "consent": {
            "status": "granted",
            "prompt_count": 1,
            "asked_at": "2026-03-15T18:40:00+00:00",
        },
        "items": {
            "preferred_master": {
                "value": "Алия",
                "expires_at": "2099-01-01T00:00:00+00:00",
                "meta": {"source": "memory"},
            },
            "expired": {
                "value": "skip",
                "expires_at": "2026-03-15T18:45:00+00:00",
            },
            "bad": "skip",
        },
        "last_updated_at": "not-a-datetime",
    }

    normalized, changed = service.get_memory_profile(
        payload,
        now=now,
        default_ttl_days=180,
    )
    payload["items"]["preferred_master"]["meta"]["source"] = "changed"

    assert changed is True
    assert normalized == {
        "version": 1,
        "ttl_days": 180,
        "consent": {
            "status": "granted",
            "prompt_count": 1,
            "asked_at": "2026-03-15T18:40:00+00:00",
        },
        "items": {
            "preferred_master": {
                "value": "Алия",
                "expires_at": "2099-01-01T00:00:00+00:00",
                "meta": {"source": "memory"},
            }
        },
    }


def test_dialog_state_service_gets_memory_pending_and_detects_expiry() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 15, 18, 50, tzinfo=timezone.utc)
    active_payload = {
        "items": {
            "preferred_master": {
                "value": "Алия",
                "expires_at": "2099-01-01T00:00:00+00:00",
            }
        },
        "expires_at": "2099-01-01T00:00:00+00:00",
    }

    active, active_expired = service.get_memory_pending(active_payload, now=now)
    expired, expired_flag = service.get_memory_pending(
        {
            "items": {"preferred_master": {"value": "skip"}},
            "expires_at": "2026-03-15T18:45:00+00:00",
        },
        now=now,
    )
    active_payload["items"]["preferred_master"]["value"] = "changed"

    assert active == {
        "items": {
            "preferred_master": {
                "value": "Алия",
                "expires_at": "2099-01-01T00:00:00+00:00",
            }
        },
        "expires_at": "2099-01-01T00:00:00+00:00",
    }
    assert active_expired is False
    assert expired is None
    assert expired_flag is True


def test_dialog_state_service_sets_memory_carriers_as_isolated_payloads() -> None:
    service = DialogStateService()
    profile = {
        "consent": {"status": "granted"},
        "items": {"preferred_master": {"value": "Алия"}},
    }
    pending = {
        "items": {"preferred_master": {"value": "Алия"}},
        "expires_at": "2099-01-01T00:00:00+00:00",
    }

    stored_profile = service.set_memory_profile(profile)
    stored_pending = service.set_memory_pending(pending)
    profile["items"]["preferred_master"]["value"] = "changed"
    pending["items"]["preferred_master"]["value"] = "changed"

    assert stored_profile == {
        "consent": {"status": "granted"},
        "items": {"preferred_master": {"value": "Алия"}},
    }
    assert stored_pending == {
        "items": {"preferred_master": {"value": "Алия"}},
        "expires_at": "2099-01-01T00:00:00+00:00",
    }
    assert service.set_memory_profile({}) is None
    assert service.set_memory_pending({}) is None


def test_dialog_state_service_sets_and_clears_confirmation_context_carriers() -> None:
    service = DialogStateService()
    context = {
        "handover_confirmation": {"asked_at": "stale"},
        "legacy_reengage": {"asked_at": "stale"},
        "legacy_asr_confirmation": {"asked_at": "stale"},
    }
    reengage_payload = {
        "asked_at": " 2026-03-15T18:40:00+00:00 ",
        "booking_messages": [" запишите меня ", "на завтра"],
    }
    asr_payload = {
        "asked_at": " 2026-03-15T18:40:00+00:00 ",
        "transcript": "  маникюр завтра  ",
        "attempt": 2,
    }

    updated = service.set_context_handover_confirmation(
        context,
        {
            "asked_at": " 2026-03-15T18:40:00+00:00 ",
            "status": " pending ",
        },
    )
    updated = service.set_context_reengage_confirmation(
        updated,
        reengage_payload,
        key="legacy_reengage",
    )
    updated = service.set_context_asr_confirmation(
        updated,
        asr_payload,
        key="legacy_asr_confirmation",
    )
    reengage_payload["booking_messages"][0] = "changed"
    asr_payload["transcript"] = "changed"

    assert updated["handover_confirmation"] == {
        "asked_at": "2026-03-15T18:40:00+00:00",
        "status": "pending",
    }
    assert updated["legacy_reengage"] == {
        "asked_at": "2026-03-15T18:40:00+00:00",
        "booking_messages": ["запишите меня", "на завтра"],
    }
    assert updated["legacy_asr_confirmation"] == {
        "asked_at": "2026-03-15T18:40:00+00:00",
        "transcript": "маникюр завтра",
        "attempt": 2,
    }

    cleared = service.set_context_handover_confirmation(updated, None)
    cleared = service.set_context_reengage_confirmation(cleared, None, key="legacy_reengage")
    cleared = service.set_context_asr_confirmation(cleared, None, key="legacy_asr_confirmation")

    assert "handover_confirmation" not in cleared
    assert "legacy_reengage" not in cleared
    assert "legacy_asr_confirmation" not in cleared


def test_dialog_state_service_sets_and_clears_pending_context_carriers() -> None:
    service = DialogStateService()
    context = {
        "legacy_asr_inflight": {"started_at": "stale"},
        "legacy_style_pending": {"reason": "stale"},
    }
    style_payload = {
        "reason": " photo_only ",
        "created_at": " 2026-03-15T18:40:00+00:00 ",
        "expires_at": " 2026-03-15T18:55:00+00:00 ",
        "media": {
            "media_type": " photo ",
            "raw_type": " image ",
            "mime": " image/jpeg ",
            "size_bytes": 123,
            "url": " https://example.com/raw.jpg ",
        },
    }

    updated = service.set_context_asr_inflight(
        context,
        {
            "started_at": " 2026-03-15T18:49:00+00:00 ",
            "expires_at": " 2026-03-15T18:55:00+00:00 ",
        },
        key="legacy_asr_inflight",
    )
    updated = service.set_context_style_reference_pending(
        updated,
        style_payload,
        key="legacy_style_pending",
    )
    style_payload["media"]["url"] = "changed"

    assert updated["legacy_asr_inflight"] == {
        "started_at": "2026-03-15T18:49:00+00:00",
        "expires_at": "2026-03-15T18:55:00+00:00",
    }
    assert updated["legacy_style_pending"] == {
        "reason": "photo_only",
        "created_at": "2026-03-15T18:40:00+00:00",
        "expires_at": "2026-03-15T18:55:00+00:00",
        "media": {
            "media_type": "photo",
            "raw_type": "image",
            "mime": "image/jpeg",
            "size_bytes": 123,
            "url": "https://example.com/raw.jpg",
        },
    }

    cleared = service.set_context_asr_inflight(updated, None, key="legacy_asr_inflight")
    cleared = service.set_context_style_reference_pending(cleared, None, key="legacy_style_pending")

    assert "legacy_asr_inflight" not in cleared
    assert "legacy_style_pending" not in cleared


def test_dialog_state_service_sets_and_clears_memory_context_carriers() -> None:
    service = DialogStateService()
    context = {
        "legacy_memory_profile": {"version": 1},
        "legacy_memory_pending": {"expires_at": "stale"},
    }
    profile_payload = {
        "consent": {"status": "granted"},
        "items": {"preferred_master": {"value": "Алия"}},
    }
    pending_payload = {
        "items": {"preferred_master": {"value": "Алия"}},
        "expires_at": "2099-01-01T00:00:00+00:00",
    }

    updated = service.set_context_memory_profile(
        context,
        profile_payload,
        key="legacy_memory_profile",
    )
    updated = service.set_context_memory_pending(
        updated,
        pending_payload,
        key="legacy_memory_pending",
    )
    profile_payload["items"]["preferred_master"]["value"] = "changed"
    pending_payload["items"]["preferred_master"]["value"] = "changed"

    assert updated["legacy_memory_profile"] == {
        "consent": {"status": "granted"},
        "items": {"preferred_master": {"value": "Алия"}},
    }
    assert updated["legacy_memory_pending"] == {
        "items": {"preferred_master": {"value": "Алия"}},
        "expires_at": "2099-01-01T00:00:00+00:00",
    }

    cleared = service.set_context_memory_profile(updated, None, key="legacy_memory_profile")
    cleared = service.set_context_memory_pending(cleared, None, key="legacy_memory_pending")

    assert "legacy_memory_profile" not in cleared
    assert "legacy_memory_pending" not in cleared


def test_dialog_state_service_builds_and_reads_class_carryover_payload() -> None:
    service = DialogStateService()
    payload = service.build_class_carryover_payload(
        class_name=" Info_Bundle ",
        intents=[" parking ", "parking", " HOURS ", 1],
        info_sections=[" parking ", "hours", " ", 1],
        message_count=4,
        default_ttl=4,
        allowed_intents={
            "location",
            "hours",
            "parking",
            "guest_policy",
            "pricing",
            "duration",
            "promotions",
            "master",
            "contact",
        },
        normalize_class_name=lambda value: value.strip().casefold(),
    )

    projection = service.get_class_carryover(payload, message_count=5)

    assert payload == {
        "class": "info_bundle",
        "intents": ["parking", "hours"],
        "info_sections": ["parking", "hours"],
        "message_count": 4,
        "ttl": 4,
    }
    assert projection == {
        "class": "info_bundle",
        "intents": ["parking", "hours"],
        "info_sections": ["parking", "hours"],
        "age": 1,
        "ttl": 4,
        "remaining": 4,
    }


def test_dialog_state_service_sets_and_clears_canonical_class_carryover() -> None:
    service = DialogStateService()
    payload = {
        "class": "info_bundle",
        "intents": ["parking"],
        "info_sections": ["parking"],
        "message_count": 4,
        "ttl": 4,
    }

    state = service.set_canonical_class_carryover(
        {"owner_id": " context_manager.dialog_state.v1 ", "version": " v1 "},
        payload=payload,
    )
    projection = service.get_canonical_class_carryover(state, message_count=5)
    payload["intents"].append("changed")
    cleared = service.clear_canonical_class_carryover(state)

    assert state["meta"]["class_carryover"] == {
        "class": "info_bundle",
        "intents": ["parking"],
        "info_sections": ["parking"],
        "message_count": 4,
        "ttl": 4,
    }
    assert projection == {
        "class": "info_bundle",
        "intents": ["parking"],
        "info_sections": ["parking"],
        "age": 1,
        "ttl": 4,
        "remaining": 4,
    }
    assert "class_carryover" not in (cleared.get("meta") or {})


def test_dialog_state_service_write_runtime_payload_materializes_touched_slice_class_carryover() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 30, 14, 0, tzinfo=timezone.utc)
    decision = build_test_policy_override_decision(
        {
            "intent": "hours",
            "action": "fact",
            "tool_action": "catalog.location",
            "fact_refs": ["hours"],
            "reason": "hours_lookup",
            "goal": "info",
            "capability": "hours",
            "subject_kind": "branch",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    updated, dialog_state, _ = service.write_runtime_payload(
        {
            "context_manager": {
                "message_count": 7,
                "canonical_dialog_state": {
                    "owner_id": "context_manager.dialog_state.v1",
                    "version": "v1",
                },
            }
        },
        decision=decision,
        execution_meta={
            "fact_family_cutover": "location_hours_parking",
            "info_sections": ["address", "hours"],
            "fact_emitted_refs": ["location", "hours"],
        },
        now=now,
    )

    expected = {
        "class": "info_bundle",
        "intents": ["location", "hours"],
        "info_sections": ["address", "hours"],
        "message_count": 7,
        "ttl": 4,
    }

    assert dialog_state.meta["class_carryover"] == expected
    assert updated["context_manager"]["class_carryover"] == expected
    assert updated["context_manager"]["canonical_dialog_state"]["meta"]["class_carryover"] == expected


def test_dialog_state_service_write_runtime_payload_preserves_existing_touched_slice_class_carryover() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 30, 14, 5, tzinfo=timezone.utc)
    touched_slice_decision = build_test_policy_override_decision(
        {
            "intent": "hours",
            "action": "fact",
            "tool_action": "catalog.location",
            "fact_refs": ["hours"],
            "reason": "hours_lookup",
            "goal": "info",
            "capability": "hours",
            "subject_kind": "branch",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )
    context = {
        "context_manager": {
            "message_count": 7,
            "canonical_dialog_state": {
                "owner_id": "context_manager.dialog_state.v1",
                "version": "v1",
            },
        }
    }
    updated, _dialog_state, _ = service.write_runtime_payload(
        context,
        decision=touched_slice_decision,
        execution_meta={
            "fact_family_cutover": "location_hours_parking",
            "info_sections": ["address", "hours"],
            "fact_emitted_refs": ["location", "hours"],
        },
        now=now,
    )
    updated["context_manager"]["message_count"] = 8

    followup_decision = build_test_policy_override_decision(
        {
            "intent": "promotions",
            "action": "fact",
            "tool_action": "catalog.service_query",
            "fact_refs": ["promotions"],
            "reason": "promo_lookup",
            "goal": "info",
            "capability": "promotions",
            "subject_kind": "service",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    next_updated, next_dialog_state, _ = service.write_runtime_payload(
        updated,
        decision=followup_decision,
        execution_meta={"info_sections": ["promotions"]},
        now=now + timedelta(minutes=1),
    )

    expected = {
        "class": "info_bundle",
        "intents": ["location", "hours"],
        "info_sections": ["address", "hours"],
        "message_count": 7,
        "ttl": 4,
    }

    assert next_dialog_state.meta["class_carryover"] == expected
    assert next_updated["context_manager"]["class_carryover"] == expected
    assert (
        service.get_canonical_class_carryover(
            next_updated["context_manager"]["canonical_dialog_state"],
            message_count=8,
        )
        == {
            "class": "info_bundle",
            "intents": ["location", "hours"],
            "info_sections": ["address", "hours"],
            "age": 1,
            "ttl": 4,
            "remaining": 4,
        }
    )


def test_dialog_state_service_builds_and_reads_service_carryover_payload() -> None:
    service = DialogStateService()
    payload = service.build_service_carryover_payload(
        service_query=" Маникюр ",
        source=" semantic_match ",
        score=0.72,
        message_count=4,
        default_ttl=4,
        projection_source=" canonical_dialog_state ",
        canonical_state_owner=" context_manager.dialog_state.v1 ",
    )

    projection = service.get_service_carryover(
        payload,
        message_count=5,
        default_ttl=4,
    )

    assert payload == {
        "service_query": "Маникюр",
        "service_query_source": "semantic_match",
        "service_query_score": 0.72,
        "message_count": 4,
        "ttl": 4,
        "projection_source": "canonical_dialog_state",
        "canonical_state_owner": "context_manager.dialog_state.v1",
    }
    assert projection == {
        "service_query": "Маникюр",
        "service_query_source": "semantic_match",
        "service_query_score": 0.72,
        "age": 1,
        "ttl": 4,
        "remaining": 4,
        "projection_source": "canonical_dialog_state",
        "canonical_state_owner": "context_manager.dialog_state.v1",
    }


def test_dialog_state_service_sets_and_projects_consult_context_payloads() -> None:
    service = DialogStateService()
    state = service.set_canonical_consult_state(
        {"owner_id": " context_manager.dialog_state.v1 ", "version": " v1 "},
        topic=" nails_design ",
        question=" Что нравится? ",
        questions=[" Что нравится ", " ", 1],
        message_count=4,
        default_ttl=4,
    )
    canonical_projection = service.get_canonical_consult_state(state, message_count=5)
    payload = service.build_consult_context_payload(
        topic=" nails_design ",
        question=" Что нравится? ",
        questions=[" Что нравится? ", " ", 1],
        message_count=4,
        default_ttl=4,
        projection_source=" canonical_dialog_state ",
        canonical_state_owner=" context_manager.dialog_state.v1 ",
    )
    fallback_projection = service.get_consult_context(
        payload,
        message_count=5,
        default_ttl=4,
    )

    assert state["consult_state"] == {
        "topic": "nails_design",
        "question": "Что нравится?",
        "questions": ["Что нравится"],
        "message_count": 4,
        "ttl": 4,
    }
    assert canonical_projection == {
        "topic": "nails_design",
        "question": "Что нравится?",
        "questions": ["Что нравится"],
        "age": 1,
        "ttl": 4,
        "remaining": 4,
        "projection_source": "canonical_dialog_state",
        "canonical_state_owner": "context_manager.dialog_state.v1",
    }
    assert payload == {
        "questions": ["Что нравится?"],
        "topic": "nails_design",
        "question": "Что нравится?",
        "message_count": 4,
        "ttl": 4,
        "projection_source": "canonical_dialog_state",
        "canonical_state_owner": "context_manager.dialog_state.v1",
    }
    assert fallback_projection == {
        "questions": ["Что нравится?"],
        "topic": "nails_design",
        "question": "Что нравится?",
        "age": 1,
        "ttl": 4,
        "remaining": 4,
        "projection_source": "canonical_dialog_state",
        "canonical_state_owner": "context_manager.dialog_state.v1",
    }


def test_dialog_state_service_sets_and_prunes_context_manager_class_carryover() -> None:
    service = DialogStateService()

    manager = service.set_context_manager_class_carryover(
        {"canonical_dialog_state": {"owner_id": " context_manager.dialog_state.v1 ", "version": " v1 "}},
        manager_key="class_carryover",
        canonical_state_key="canonical_dialog_state",
        class_name=" Info_Bundle ",
        intents=[" parking ", " HOURS "],
        info_sections=[" parking ", "hours"],
        message_count=4,
        default_ttl=4,
        allowed_intents={"parking", "hours"},
        normalize_class_name=lambda value: value.strip().casefold(),
    )
    pruned, event = service.prune_context_manager_class_carryover(
        manager,
        manager_key="class_carryover",
        canonical_state_key="canonical_dialog_state",
        message_count=9,
        default_ttl=4,
    )

    assert manager["class_carryover"] == {
        "class": "info_bundle",
        "intents": ["parking", "hours"],
        "info_sections": ["parking", "hours"],
        "message_count": 4,
        "ttl": 4,
    }
    assert manager["canonical_dialog_state"]["meta"]["class_carryover"] == manager["class_carryover"]
    assert "class_carryover" not in pruned
    assert "class_carryover" not in (pruned["canonical_dialog_state"].get("meta") or {})
    assert event == {
        "reason": "expired",
        "age": 5,
        "ttl": 4,
        "class": "info_bundle",
    }


def test_dialog_state_service_sets_and_prunes_context_manager_service_carryover() -> None:
    service = DialogStateService()

    manager = service.set_context_manager_service_carryover(
        {},
        manager_key="service_carryover",
        canonical_state_key="canonical_dialog_state",
        referent_key="service",
        service_query=" Маникюр ",
        source=" semantic_match ",
        score=0.72,
        message_count=4,
        default_ttl=4,
        projection_source=" canonical_dialog_state ",
        canonical_state_owner=" context_manager.dialog_state.v1 ",
    )
    pruned, event = service.prune_context_manager_service_carryover(
        manager,
        manager_key="service_carryover",
        canonical_state_key="canonical_dialog_state",
        referent_key="service",
        message_count=9,
        default_ttl=4,
        projection_source="canonical_dialog_state",
    )

    assert manager["service_carryover"] == {
        "service_query": "Маникюр",
        "service_query_source": "semantic_match",
        "service_query_score": 0.72,
        "message_count": 4,
        "ttl": 4,
        "projection_source": "canonical_dialog_state",
        "canonical_state_owner": "context_manager.dialog_state.v1",
    }
    assert manager["canonical_dialog_state"]["current_referents"]["service"] == {
        "value": "Маникюр",
        "message_count": 4,
        "source": "semantic_match",
        "score": 0.72,
        "ttl": 4,
    }
    assert "service_carryover" not in pruned
    assert pruned["canonical_dialog_state"]["current_referents"] == {}
    assert event == {
        "reason": "expired",
        "age": 5,
        "ttl": 4,
        "value": "Маникюр",
        "projection_source": "canonical_dialog_state",
        "canonical_state_owner": "context_manager.dialog_state.v1",
    }


def test_dialog_state_service_sets_and_prunes_context_manager_consult_context() -> None:
    service = DialogStateService()

    manager = service.set_context_manager_consult_context(
        {},
        manager_key="consult_context",
        canonical_state_key="canonical_dialog_state",
        topic=" nails_design ",
        question=" Что нравится? ",
        questions=[" Что нравится? ", " "],
        message_count=4,
        default_ttl=4,
        projection_source=" canonical_dialog_state ",
        canonical_state_owner=" context_manager.dialog_state.v1 ",
    )
    pruned, event = service.prune_context_manager_consult_context(
        manager,
        manager_key="consult_context",
        canonical_state_key="canonical_dialog_state",
        message_count=9,
        default_ttl=4,
    )

    assert manager["consult_context"] == {
        "questions": ["Что нравится?"],
        "topic": "nails_design",
        "question": "Что нравится?",
        "message_count": 4,
        "ttl": 4,
        "projection_source": "canonical_dialog_state",
        "canonical_state_owner": "context_manager.dialog_state.v1",
    }
    assert manager["canonical_dialog_state"]["consult_state"] == {
        "topic": "nails_design",
        "question": "Что нравится?",
        "questions": ["Что нравится?"],
        "message_count": 4,
        "ttl": 4,
    }
    assert "consult_context" not in pruned
    assert "consult_state" not in pruned["canonical_dialog_state"]
    assert event == {
        "reason": "expired",
        "age": 5,
        "ttl": 4,
        "projection_source": "canonical_dialog_state",
        "canonical_state_owner": "context_manager.dialog_state.v1",
    }


def test_dialog_state_service_clears_context_manager_carryover_family() -> None:
    service = DialogStateService()

    manager = service.clear_context_manager_carryover_family(
        {
            "class_carryover": {
                "class": "info_bundle",
                "message_count": 4,
                "ttl": 4,
            },
            "service_carryover": {
                "service_query": "Маникюр",
                "message_count": 4,
                "ttl": 4,
            },
            "consult_context": {
                "topic": "nails_design",
                "question": "Что нравится?",
                "questions": ["Что нравится?"],
                "message_count": 4,
                "ttl": 4,
            },
            "canonical_dialog_state": {
                "owner_id": " context_manager.dialog_state.v1 ",
                "version": " v1 ",
                "meta": {
                    "class_carryover": {
                        "class": "info_bundle",
                        "message_count": 4,
                        "ttl": 4,
                    }
                },
                "current_referents": {
                    "service": {
                        "value": "Маникюр",
                        "message_count": 4,
                        "ttl": 4,
                    }
                },
                "consult_state": {
                    "topic": "nails_design",
                    "question": "Что нравится?",
                    "questions": ["Что нравится?"],
                    "message_count": 4,
                    "ttl": 4,
                },
            },
            "other": {"keep": True},
        },
        class_manager_key="class_carryover",
        service_manager_key="service_carryover",
        consult_manager_key="consult_context",
        canonical_state_key="canonical_dialog_state",
        referent_key="service",
    )

    assert "class_carryover" not in manager
    assert "service_carryover" not in manager
    assert "consult_context" not in manager
    assert manager["other"] == {"keep": True}
    assert manager["canonical_dialog_state"] == {
        "owner_id": "context_manager.dialog_state.v1",
        "version": "v1",
        "current_referents": {},
    }


def test_dialog_state_service_gets_and_sets_intent_queue() -> None:
    service = DialogStateService()

    queue = service.get_intent_queue(
        {
            "intent_queue": [" Booking ", "pricing", " booking ", "", 1, None, "PRICING"],
        }
    )
    updated = service.set_intent_queue(
        {
            "other": "value",
            "nested": {"keep": True},
        },
        queue=[" Hours ", "hours", " booking ", "", 1],
    )
    cleared = service.set_intent_queue(
        {
            "intent_queue": ["booking"],
            "other": "value",
        },
        queue=[" ", None],
    )

    assert queue == ["booking", "pricing"]
    assert updated == {
        "other": "value",
        "nested": {"keep": True},
        "intent_queue": ["hours", "booking"],
    }
    assert cleared == {
        "other": "value",
    }


def test_dialog_state_service_normalizes_context_manager_canonical_state() -> None:
    service = DialogStateService()

    state = service.normalize_context_manager_canonical_state(
        {
            "owner_id": "  context_manager.dialog_state.v1  ",
            "version": "  v1  ",
            "current_referents": {
                "service": {
                    "value": "  Маникюр  ",
                    "message_count": "4",
                    "source": "  booking_state  ",
                    "score": 0.75,
                },
                "ignored": {"value": "skip"},
            },
            "pending_question_contract": {
                "slot": " datetime ",
                "expected_reply_type": " time ",
                "reason": " booking_prompt ",
                "message_count": "5",
            },
            "interaction_state": {
                "resume_slot": " datetime ",
                "interaction_target": " Time ",
                "interaction_relation": " Ask_About_Requested_Slot ",
                "interaction_owner": " llm_policy_core:ask_about_requested_slot ",
                "grounded_referents": {"service": " Маникюр "},
            },
            "consult_state": {
                "topic": "  care  ",
                "question": "  Что лучше?  ",
                "questions": ["  Что лучше?  ", " "],
                "message_count": "2",
            },
        }
    )

    assert state["current_referents"]["service"]["value"] == "Маникюр"
    assert state["pending_question_contract"] == {
        "expected_reply_type": "time",
        "reason": "booking_prompt",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }
    assert state["interaction_state"]["interaction_target"] == "time"
    assert state["consult_state"]["questions"] == ["Что лучше?"]


def test_dialog_state_service_sets_projects_and_prunes_canonical_referent() -> None:
    service = DialogStateService()
    state = service.set_canonical_referent(
        {
            "owner_id": "context_manager.dialog_state.v1",
            "version": "v1",
            "current_referents": {},
        },
        referent_key="service",
        value=" Маникюр ",
        source=" semantic_match ",
        score=0.72,
        message_count=4,
        default_ttl=4,
    )
    projection = service.project_canonical_referent(
        state,
        referent_key="service",
        message_count=5,
        projection_source="canonical_dialog_state",
    )
    pruned_state, pruned_event = service.prune_canonical_referent(
        state,
        referent_key="service",
        message_count=9,
        projection_source="canonical_dialog_state",
    )

    assert state["current_referents"]["service"] == {
        "value": "Маникюр",
        "message_count": 4,
        "source": "semantic_match",
        "score": 0.72,
        "ttl": 4,
    }
    assert projection == {
        "value": "Маникюр",
        "source": "semantic_match",
        "score": 0.72,
        "age": 1,
        "ttl": 4,
        "remaining": 4,
        "projection_source": "canonical_dialog_state",
        "canonical_state_owner": "context_manager.dialog_state.v1",
    }
    assert "service" not in pruned_state["current_referents"]
    assert pruned_event == {
        "reason": "expired",
        "age": 5,
        "ttl": 4,
        "value": "Маникюр",
        "projection_source": "canonical_dialog_state",
        "canonical_state_owner": "context_manager.dialog_state.v1",
    }


def test_dialog_state_service_canonical_referent_setter_keeps_state_detached_and_ignores_unknown_key() -> None:
    service = DialogStateService()
    state = {
        "owner_id": "context_manager.dialog_state.v1",
        "version": "v1",
        "current_referents": {
            "service": {
                "value": "Педикюр",
                "message_count": 2,
            }
        },
    }

    updated = service.set_canonical_referent(
        state,
        referent_key="branch",
        value=" Алматы центр ",
        source=" booking_state ",
        score=None,
        message_count=6,
        default_ttl=None,
    )
    ignored = service.set_canonical_referent(
        state,
        referent_key="unknown",
        value="skip",
        source="ignore",
        score=None,
        message_count=6,
        default_ttl=None,
    )
    state["current_referents"]["service"]["value"] = "changed"

    assert updated["current_referents"]["service"]["value"] == "Педикюр"
    assert updated["current_referents"]["branch"] == {
        "value": "Алматы центр",
        "message_count": 6,
        "source": "booking_state",
    }
    assert ignored["current_referents"] == {
        "service": {
            "value": "Педикюр",
            "message_count": 2,
        }
    }


def test_dialog_state_service_sets_canonical_pending_question_and_interaction_state() -> None:
    service = DialogStateService()
    state = service.set_canonical_pending_question_contract(
        {"current_referents": {}},
        expected_reply_type="  name  ",
        reason="  booking_followup  ",
        message_count=6,
    )
    state = service.set_canonical_interaction_state(
        state,
        resume_slot=" name ",
        interaction_target=" time ",
        interaction_relation=" slot_compare ",
        interaction_owner=" booking name owner ",
        grounded_referents={"service": " Маникюр "},
        confirmation_state={"required": True, "slot": " datetime ", "value": " 15:00 "},
        degrade_reason=" timeout ",
    )

    assert state["pending_question_contract"] == {
        "expected_reply_type": "name",
        "reason": "booking_followup",
        "next_question": "name",
        "open_questions": ["name"],
    }
    assert state["interaction_state"] == {
        "resume_slot": "name",
        "interaction_target": "time",
        "interaction_relation": "slot_compare",
        "interaction_owner": "booking name owner",
        "grounded_referents": {"service": "Маникюр"},
        "confirmation_state": {"required": True, "slot": "datetime", "value": "15:00"},
        "degrade_reason": "timeout",
    }


def test_dialog_state_service_syncs_canonical_question_contract_state_with_detached_payloads() -> None:
    service = DialogStateService()
    grounded_referents = {
        "service": " Маникюр ",
        "specialist": " Айгерим ",
    }
    confirmation_state = {
        "required": True,
        "slot": " datetime ",
        "value": " 18:00 ",
        "source": " llm_slot ",
    }

    state = service.sync_canonical_question_contract_state(
        {"current_referents": {}},
        expected_reply_type="  name  ",
        expected_reply_reason="  booking_followup  ",
        message_count=6,
        interaction_target=" time ",
        interaction_relation=" ask_about_requested_slot ",
        interaction_owner=None,
        grounded_referents=grounded_referents,
        confirmation_state=confirmation_state,
        degrade_reason=" timeout ",
    )

    grounded_referents["service"] = "Педикюр"
    confirmation_state["value"] = "09:00"

    assert state["pending_question_contract"] == {
        "expected_reply_type": "name",
        "reason": "booking_followup",
        "next_question": "name",
        "open_questions": ["name"],
    }
    assert state["interaction_state"] == {
        "resume_slot": "name",
        "interaction_target": "time",
        "interaction_relation": "ask_about_requested_slot",
        "interaction_owner": "llm_policy_core:ask_about_requested_slot",
        "grounded_referents": {
            "service": "Маникюр",
            "specialist": "Айгерим",
        },
        "confirmation_state": {
            "required": True,
            "slot": "datetime",
            "value": "18:00",
            "source": "llm_slot",
        },
        "degrade_reason": "timeout",
    }


def test_dialog_state_service_syncs_context_manager_expected_reply_state() -> None:
    service = DialogStateService()

    updated = service.sync_context_manager_expected_reply_state(
        {
            "message_count": "7",
            "service_carryover": {
                "service_query": " Маникюр ",
                "service_query_source": " carryover ",
                "service_query_score": 0.9,
                "message_count": "5",
            },
            "consult_context": {
                "topic": " nails ",
                "question": " Какой дизайн? ",
                "questions": [" Какой дизайн? "],
                "message_count": "4",
            },
        },
        booking_state={
            "active": True,
            "specialist_name": " Айгерим ",
            "appointment_id": " BK-1 ",
        },
        expected_reply_type="  name  ",
        expected_reply_reason="  booking_followup  ",
        message_count=7,
        branch_id="branch-1",
        interaction_target=" time ",
        interaction_relation=" ask_about_requested_slot ",
        canonical_state_key="canonical_dialog_state",
        service_default_ttl=4,
        consult_default_ttl=4,
        service_carryover={
            "service_query": " Маникюр ",
            "service_query_source": " carryover ",
            "service_query_score": 0.9,
            "message_count": "5",
        },
        legacy_consult_context={
            "topic": " nails ",
            "question": " Какой дизайн? ",
            "questions": [" Какой дизайн? "],
            "message_count": "4",
        },
    )

    state = updated["canonical_dialog_state"]
    assert state["current_referents"] == {
        "service": {
            "value": "Маникюр",
            "message_count": 5,
            "source": "carryover",
            "score": 0.9,
            "ttl": 4,
        },
        "master": {
            "value": "Айгерим",
            "message_count": 7,
            "source": "booking_state",
            "score": 1.0,
            "ttl": 4,
        },
        "booking_ref": {
            "value": "BK-1",
            "message_count": 7,
            "source": "booking_state",
            "score": 1.0,
        },
        "branch": {
            "value": "branch-1",
            "message_count": 7,
            "source": "conversation_branch",
            "score": 1.0,
        },
    }
    assert state["consult_state"] == {
        "topic": "nails",
        "question": "Какой дизайн?",
        "questions": ["Какой дизайн?"],
        "message_count": 4,
        "ttl": 4,
    }
    assert state["pending_question_contract"] == {
        "expected_reply_type": "name",
        "reason": "booking_followup",
        "next_question": "name",
        "open_questions": ["name"],
    }
    assert state["interaction_state"] == {
        "resume_slot": "name",
        "interaction_target": "time",
        "interaction_relation": "ask_about_requested_slot",
        "interaction_owner": "llm_policy_core:ask_about_requested_slot",
        "grounded_referents": {
            "service": "Маникюр",
            "specialist": "Айгерим",
            "branch": "branch-1",
            "booking_ref": "BK-1",
        },
    }


def test_dialog_state_service_builds_expected_reply_context_sync_result() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 17, 19, 45, tzinfo=timezone.utc)
    context = {
        "context_manager": {
            "message_count": "8",
            "current_goal": " booking ",
        },
        "booking": {
            "active": True,
            "service": " Маникюр ",
            "confirmation": {
                "slot": " datetime ",
                "value": " 15:00 ",
                "source": " llm_slot ",
            },
        },
        "session_memory": {
            "active_goal": "old",
            "interaction_state": {
                "resume_slot": "service",
                "interaction_owner": "old owner",
            },
        },
        "re_entry_required": {
            "required": True,
            "reason": " pending_resume ",
            "set_at": "2026-03-17T18:40:00+00:00",
        },
        "expected_reply_type": " old ",
        "expected_reply_reason": " old_reason ",
    }

    result = service.build_expected_reply_context_sync_result(
        context,
        expected_reply_type="  time  ",
        reason="  booking_prompt  ",
        now=now,
        context_manager_key="context_manager",
        canonical_state_key="canonical_dialog_state",
        booking_key="booking",
        session_memory_key="session_memory",
        re_entry_required_key="re_entry_required",
        service_carryover_key="service_carryover",
        consult_context_key="consult_context",
        session_memory_ttl_hours=24,
        service_default_ttl=4,
        consult_default_ttl=4,
    )

    state = result.context["context_manager"]["canonical_dialog_state"]
    assert result.expected_reply_type == "time"
    assert result.expected_reply_reason == "booking_prompt"
    assert result.re_entry_cleared is True
    assert result.question_memory == {
        "active_goal": "booking",
        "interaction_state": {
            "resume_slot": "datetime",
            "interaction_owner": "question_contract:booking_prompt",
            "grounded_referents": {"service": "Маникюр"},
            "confirmation_state": {
                "required": True,
                "slot": "datetime",
                "value": "15:00",
                "source": "llm_slot",
            },
        },
        "unanswered_questions": ["time"],
        "goal_stack": ["booking"],
        "pending_question_contract": {
            "expected_reply_type": "time",
            "reason": "booking_prompt",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        "last_updated_at": now.isoformat(),
        "ttl_hours": 24,
    }
    assert state["pending_question_contract"] == {
        "expected_reply_type": "time",
        "reason": "booking_prompt",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }
    assert state["interaction_state"] == {
        "resume_slot": "datetime",
        "interaction_owner": "question_contract:booking_prompt",
        "grounded_referents": {"service": "Маникюр"},
        "confirmation_state": {
            "required": True,
            "slot": "datetime",
            "value": "15:00",
            "source": "llm_slot",
        },
    }
    assert result.context["expected_reply_type"] == "time"
    assert result.context["expected_reply_reason"] == "booking_prompt"
    assert result.context["re_entry_required"] == {
        "required": False,
        "reason": "booking_prompt",
        "cleared_at": now.isoformat(),
    }
    assert result.context["session_memory"] == result.question_memory
    assert context["expected_reply_type"] == " old "
    assert context["re_entry_required"]["required"] is True


def test_dialog_state_service_rebuilds_session_memory_from_runtime_projection() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)
    context = {
        "consultant_runtime": {
            "conversation_projection": ConversationProjectionV1(
                current_goal="booking",
                pending_question_contract={
                    "expected_reply_type": "time",
                    "reason": "booking_prompt",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                },
                booking_state={"active": True, "service": "Маникюр"},
            ).model_dump(mode="python", exclude_none=True)
        }
    }

    updated_context, rebuilt_memory = service.rebuild_context_session_memory(
        context,
        base_memory={
            "active_goal": "info",
            "goal_stack": ["info"],
            "pending_question_contract": {
                "expected_reply_type": "service",
                "reason": "old_reason",
                "next_question": "service",
                "open_questions": ["service"],
            },
            "last_updated_at": "2026-03-27T08:00:00+00:00",
            "ttl_hours": 24,
        },
        now=now,
        default_ttl_hours=24,
    )

    assert rebuilt_memory["active_goal"] == "booking"
    assert rebuilt_memory["goal_stack"][-1] == "booking"
    assert rebuilt_memory["pending_question_contract"] == {
        "expected_reply_type": "time",
        "reason": "booking_prompt",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }
    assert updated_context["session_memory"] == rebuilt_memory
    assert rebuilt_memory["last_updated_at"] == now.isoformat()


def test_dialog_state_service_clear_expected_reply_rebuilds_projection_first_memory() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 27, 12, 30, tzinfo=timezone.utc)
    context = {
        "consultant_runtime": {
            "conversation_projection": ConversationProjectionV1(
                current_goal="booking",
                pending_question_contract={},
            ).model_dump(mode="python", exclude_none=True)
        },
        "session_memory": {
            "active_goal": "info",
            "pending_question_contract": {
                "expected_reply_type": "service",
                "reason": "stale_reason",
                "next_question": "service",
                "open_questions": ["service"],
            },
            "last_updated_at": "2026-03-27T08:00:00+00:00",
            "ttl_hours": 24,
        },
    }

    updated_context, rebuilt_memory, changed = service.clear_context_session_memory_expected_reply(
        context,
        expected_reply_type="service",
        now=now,
        default_ttl_hours=24,
    )

    assert changed is True
    assert rebuilt_memory["active_goal"] == "booking"
    assert "pending_question_contract" not in rebuilt_memory
    assert updated_context["session_memory"] == rebuilt_memory
    assert rebuilt_memory["last_updated_at"] == now.isoformat()


def test_dialog_state_service_prepares_conversation_context_write_with_simulation_and_trace_merge() -> None:
    service = DialogStateService()
    prepared = service.prepare_conversation_context_write(
        {
            "simulation": {"mode": True, "id": "sim-1"},
            "simulation_mode": True,
            "decision_trace": [
                {"stage": "seed", "decision": "start", "recorded_at": "t1"},
                {"stage": "carry", "decision": "keep", "recorded_at": "t2"},
            ],
        },
        {
            "context_manager": {"current_goal": "booking"},
            "decision_trace": [
                {"stage": "seed", "decision": "start", "recorded_at": "t1"},
                {"stage": "new", "decision": "append", "recorded_at": "t3"},
            ],
        },
        decision_trace_key="decision_trace",
        preserve_keys=("simulation", "simulation_mode"),
        retain_trace=lambda trace: trace,
    )

    assert prepared["simulation"] == {"mode": True, "id": "sim-1"}
    assert prepared["simulation_mode"] is True
    assert prepared["decision_trace"] == [
        {"stage": "seed", "decision": "start", "recorded_at": "t1"},
        {"stage": "carry", "decision": "keep", "recorded_at": "t2"},
        {"stage": "new", "decision": "append", "recorded_at": "t3"},
    ]


def test_dialog_state_service_load_runtime_payload_reprojects_stale_expected_reply_fields() -> None:
    service = DialogStateService()

    loaded = service.load_runtime_payload(
        {
            "consultant_runtime": {
                "schema_version": "consultant_runtime.v1",
                "expected_reply_type": "name",
                "expected_reply_reason": "stale_projection",
                "dialog_state": {
                    "schema_version": "dialog_state.v1",
                    "pending_question_contract": {
                        "expected_reply_type": "time",
                        "reason": "collect:datetime",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                    },
                    "projections": {
                        "expected_reply_type": "name",
                        "expected_reply_reason": "stale_projection",
                    },
                },
                "current_goal": "booking",
            }
        }
    )

    assert loaded["expected_reply_type"] == "time"
    assert loaded["expected_reply_reason"] == "collect:datetime"
    assert loaded["dialog_state"].projections.expected_reply_type == "time"
    assert loaded["dialog_state"].projections.expected_reply_reason == "collect:datetime"


def test_dialog_state_service_normalizes_low_confidence_retry_count() -> None:
    service = DialogStateService()

    assert service.get_low_confidence_retry_count({"low_confidence_retry_count": " 3 "}) == 3
    assert service.get_low_confidence_retry_count({"low_confidence_retry_count": "-2"}) == 0
    assert service.get_low_confidence_retry_count({"low_confidence_retry_count": "oops"}) == 0

    updated = service.set_low_confidence_retry_count({"other": "value"}, count="-4")

    assert updated == {
        "other": "value",
        "low_confidence_retry_count": 0,
    }


def test_dialog_state_service_resets_low_confidence_retry_count_with_legacy_truthy_semantics() -> None:
    service = DialogStateService()

    reset_payload, changed = service.reset_low_confidence_retry_count(
        {"low_confidence_retry_count": "oops", "other": "value"}
    )
    untouched_payload, untouched_changed = service.reset_low_confidence_retry_count(
        {"low_confidence_retry_count": 0, "other": "value"}
    )

    assert changed is True
    assert reset_payload == {
        "low_confidence_retry_count": 0,
        "other": "value",
    }
    assert untouched_changed is False
    assert untouched_payload == {
        "low_confidence_retry_count": 0,
        "other": "value",
    }


def test_dialog_state_service_builds_compact_summary_text_and_payload() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 15, 20, 25, tzinfo=timezone.utc)

    summary_text = service.build_compact_summary_text(
        booking={
            "service": "  Стрижка  ",
            "datetime": " завтра после 15:00 ",
        },
        refusal_flags={"phone": {"status": "active"}},
        language="ru",
        is_refusal_flag_active=lambda payload, key: bool(payload.get(key)),
    )
    manager = service.set_compact_summary(
        {"message_count": 8},
        summary_text=summary_text,
        reason="clarify_limit",
        now=now,
    )

    assert summary_text == "Услуга: Стрижка; Время: завтра после 15:00; Телефон: отказ; Язык: ru"
    assert manager["compact_summary"] == {
        "text": summary_text,
        "updated_at": now.isoformat(),
        "reason": "clarify_limit",
    }
    assert manager["message_count"] == 8


def test_dialog_state_service_gets_and_sets_clarify_attempt_state() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 15, 20, 26, tzinfo=timezone.utc)

    count, last_at = service.get_clarify_attempt_state(
        {
            "clarify_attempts": {
                "booking": {
                    "count": " 2 ",
                    "last_at": "2026-03-15T10:00:00+00:00",
                }
            }
        },
        intent="booking",
    )
    manager = service.set_clarify_attempt_state(
        {
            "message_count": 8,
            "clarify_attempts": {
                "info": {
                    "count": 1,
                    "last_at": "2026-03-15T09:00:00+00:00",
                }
            },
        },
        intent="booking",
        count="-3",
        now=now,
    )

    assert count == 2
    assert last_at == "2026-03-15T10:00:00+00:00"
    assert manager["message_count"] == 8
    assert manager["clarify_attempts"] == {
        "info": {
            "count": 1,
            "last_at": "2026-03-15T09:00:00+00:00",
        },
        "booking": {
            "count": 0,
            "last_at": now.isoformat(),
        },
    }


def test_sync_session_memory_interaction_state_uses_dialog_state_projection() -> None:
    now = datetime(2026, 3, 15, 18, 30, tzinfo=timezone.utc)
    context, memory = build_test_sync_session_memory_interaction_state(
        {},
        interaction_state={
            "resume_slot": " Name ",
            "interaction_target": "time",
            "interaction_relation": "slot_compare",
            "interaction_owner": " booking   name ",
            "degrade_reason": "  timeout  ",
        },
        now=now,
    )

    assert memory["interaction_state"] == {
        "resume_slot": "name",
        "interaction_target": "time",
        "interaction_relation": "slot_compare",
        "interaction_owner": "booking name",
        "degrade_reason": "timeout",
    }
    assert context["session_memory"]["interaction_state"] == memory["interaction_state"]
    assert context["session_memory"]["last_updated_at"] == now.isoformat()


def test_reset_session_memory_clears_carryover_family_from_canonical_state() -> None:
    now = datetime(2026, 3, 16, 12, 30, tzinfo=timezone.utc)
    context, manager, snapshot = build_test_reset_session_memory(
        context={
            "context_manager": {
                "class_carryover": {
                    "class": "info_bundle",
                    "message_count": 4,
                    "ttl": 4,
                },
                "service_carryover": {
                    "service_query": "Маникюр",
                    "message_count": 4,
                    "ttl": 4,
                },
                "consult_context": {
                    "topic": "nails_design",
                    "question": "Что нравится?",
                    "questions": ["Что нравится?"],
                    "message_count": 4,
                    "ttl": 4,
                },
                "canonical_dialog_state": {
                    "owner_id": "context_manager.dialog_state.v1",
                    "version": "v1",
                    "meta": {
                        "class_carryover": {
                            "class": "info_bundle",
                            "message_count": 4,
                            "ttl": 4,
                        }
                    },
                    "current_referents": {
                        "service": {
                            "value": "Маникюр",
                            "message_count": 4,
                            "ttl": 4,
                        }
                    },
                    "consult_state": {
                        "topic": "nails_design",
                        "question": "Что нравится?",
                        "questions": ["Что нравится?"],
                        "message_count": 4,
                        "ttl": 4,
                    },
                },
            },
            "expected_reply_type": "time",
            "booking": {"active": True, "service": "Маникюр"},
            "session_memory": {"active_goal": "booking"},
            "intent_queue": ["booking"],
            "last_service_hint": "Маникюр",
        },
        context_manager={
            "class_carryover": {
                "class": "info_bundle",
                "message_count": 4,
                "ttl": 4,
            },
            "service_carryover": {
                "service_query": "Маникюр",
                "message_count": 4,
                "ttl": 4,
            },
            "consult_context": {
                "topic": "nails_design",
                "question": "Что нравится?",
                "questions": ["Что нравится?"],
                "message_count": 4,
                "ttl": 4,
            },
            "canonical_dialog_state": {
                "owner_id": "context_manager.dialog_state.v1",
                "version": "v1",
                "meta": {
                    "class_carryover": {
                        "class": "info_bundle",
                        "message_count": 4,
                        "ttl": 4,
                    }
                },
                "current_referents": {
                    "service": {
                        "value": "Маникюр",
                        "message_count": 4,
                        "ttl": 4,
                    }
                },
                "consult_state": {
                    "topic": "nails_design",
                    "question": "Что нравится?",
                    "questions": ["Что нравится?"],
                    "message_count": 4,
                    "ttl": 4,
                },
            },
        },
        reason="manual_reset",
        now=now,
    )

    assert "session_memory" not in context
    assert "expected_reply_type" not in context
    assert context["booking"] == {"active": False}
    assert "last_service_hint" not in context
    assert context["context_manager"] == manager
    assert manager["canonical_dialog_state"] == {
        "owner_id": "context_manager.dialog_state.v1",
        "version": "v1",
        "current_referents": {},
    }
    assert snapshot == {
        "reason": "manual_reset",
        "active_goal": None,
        "goal_stack_depth": 0,
        "goal_stack_top": None,
        "pending_slots": [],
        "unanswered_questions_count": 0,
        "interaction_resume_slot": None,
        "interaction_owner": None,
    }


def test_dialog_state_service_resets_runtime_continuity_to_clean_runtime_state() -> None:
    service = DialogStateService()
    now = datetime(2026, 3, 24, 12, 0, tzinfo=timezone.utc)
    context = {
        "consultant_runtime": {
            "schema_version": "consultant_runtime.v1",
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "2026-03-25T15:00:00+00:00",
                "last_question": "name",
            },
            "expected_reply_type": "name",
            "expected_reply_reason": "collect:name",
            "current_goal": "booking",
        },
        "context_manager": {
            "message_count": 7,
            "current_goal": "booking",
            "class_carryover": {
                "class": "info_bundle",
                "message_count": 7,
                "ttl": 4,
            },
            "service_carryover": {
                "service_query": "Маникюр",
                "message_count": 7,
                "ttl": 4,
            },
            "consult_context": {
                "topic": "pricing",
                "question": "Сколько стоит?",
                "questions": ["Сколько стоит?"],
                "message_count": 7,
                "ttl": 4,
            },
            "canonical_dialog_state": {
                "owner_id": "context_manager.dialog_state.v1",
                "version": "v1",
                "pending_question_contract": {
                    "expected_reply_type": "time",
                    "slot": "datetime",
                    "reason": "booking_prompt",
                    "message_count": 7,
                },
                "interaction_state": {
                    "resume_slot": "datetime",
                    "interaction_owner": "llm_policy_core:fill_requested_slot",
                },
                "current_referents": {
                    "service": {
                        "value": "Маникюр",
                        "message_count": 7,
                        "ttl": 4,
                    },
                    "master": {
                        "value": "Алина",
                        "message_count": 7,
                        "ttl": 4,
                    },
                    "booking_ref": {
                        "value": "appt-1",
                        "message_count": 7,
                        "ttl": 4,
                    },
                },
                "consult_state": {
                    "topic": "pricing",
                    "question": "Сколько стоит?",
                    "questions": ["Сколько стоит?"],
                    "message_count": 7,
                    "ttl": 4,
                },
                "meta": {
                    "class_carryover": {
                        "class": "info_bundle",
                        "message_count": 7,
                        "ttl": 4,
                    }
                },
            },
        },
        "expected_reply_type": "name",
        "expected_reply_reason": "collect:name",
        "current_goal": "booking",
        "booking": {
            "active": True,
            "service": "Маникюр",
            "datetime": "2026-03-25T15:00:00+00:00",
            "last_question": "name",
        },
        "session_memory": {
            "active_goal": "booking",
            "last_question_type": "name",
            "unanswered_questions": ["name"],
            "interaction_state": {
                "resume_slot": "name",
                "interaction_owner": "question_contract",
            },
        },
        "pending_resume": {
            "expected_reply_type": "name",
            "booking": {
                "active": True,
                "service": "Маникюр",
            },
        },
        "re_entry_required": {
            "required": True,
            "reason": "pending_resume",
            "set_at": "2026-03-24T11:59:00+00:00",
        },
        "intent_queue": ["booking"],
        "last_service_hint": "Маникюр",
        "last_service_hint_at": "2026-03-24T11:58:00+00:00",
        "simulation": {"mode": True, "id": "run-42"},
    }

    updated = service.reset_runtime_continuity(
        context,
        now=now,
        reason="explicit_reset",
    )

    assert "consultant_runtime" not in updated
    assert "expected_reply_type" not in updated
    assert "expected_reply_reason" not in updated
    assert "current_goal" not in updated
    assert updated["booking"] == {"active": False}
    assert "session_memory" not in updated
    assert "pending_resume" not in updated
    assert updated["re_entry_required"] == {
        "required": False,
        "reason": "explicit_reset",
        "cleared_at": now.isoformat(),
    }
    assert updated["intent_queue"] == []
    assert "last_service_hint" not in updated
    assert "last_service_hint_at" not in updated
    assert updated["simulation"] == {"mode": True, "id": "run-42"}
    assert updated["context_manager"] == {
        "message_count": 7,
        "canonical_dialog_state": {
            "owner_id": "context_manager.dialog_state.v1",
            "version": "v1",
            "current_referents": {},
        },
    }


def test_dialog_state_service_merges_fact_interrupt_slots_into_active_booking() -> None:
    service = DialogStateService()
    planner = TurnPlanner()
    now = datetime(2026, 3, 25, 12, 0, tzinfo=timezone.utc)
    context = {
        "consultant_runtime": {
            "schema_version": "consultant_runtime.v1",
            "booking": {
                "active": True,
                "datetime": "2026-03-29T19:00:00+00:00",
                "last_question": "service",
            },
            "expected_reply_type": "service_choice",
            "expected_reply_reason": "collect:service",
            "current_goal": "booking",
        }
    }
    decision = build_test_policy_override_decision(
        {
            "action": "fact",
            "intent": "duration",
            "tool_action": "catalog.service_query",
            "slots": {"service": "Наращивание полигелем"},
        },
        interaction_owner="turn_planner_intent_routing",
        interaction_relation="generic_info_interrupt",
        source="turn_planner_intent_routing",
    )

    updated, dialog_state, booking_payload = service.write_runtime_payload(
        context,
        decision=decision,
        execution_meta={
            "slot_values": {"service": "Наращивание полигелем"},
            "info_sections": ["duration"],
        },
        now=now,
    )

    runtime_payload = updated["consultant_runtime"]
    assert runtime_payload["booking"]["service"] == "Наращивание полигелем"
    assert "expected_reply_type" not in runtime_payload
    assert "expected_reply_reason" not in runtime_payload
    assert "expected_reply_type" not in updated
    assert "expected_reply_reason" not in updated
    loaded = service.load_runtime_payload(updated)
    assert loaded["expected_reply_type"] == "service_choice"
    assert loaded["expected_reply_reason"] == "collect:service"
    assert dialog_state.current_referents.service == "Наращивание полигелем"
    assert booking_payload["service"] == "Наращивание полигелем"


def test_dialog_state_service_preserves_active_booking_contract_across_fact_interrupt() -> None:
    service = DialogStateService()
    planner = TurnPlanner()
    now = datetime(2026, 3, 25, 12, 15, tzinfo=timezone.utc)
    context = {
        "consultant_runtime": {
            "schema_version": "consultant_runtime.v1",
            "dialog_state": {
                "schema_version": "dialog_state.v1",
                "current_referents": {
                    "service": "Маникюр",
                    "specialist": "Айгерим",
                    "branch": None,
                    "booking": None,
                    "customer": None,
                },
                "pending_question_contract": {
                    "expected_reply_type": "time",
                    "pending_question_target": "time",
                    "active_question_relation": "ask_about_requested_slot",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                },
                "interaction_state": {
                    "resume_slot": "datetime",
                    "interaction_target": "time",
                    "interaction_relation": "ask_about_requested_slot",
                    "interaction_owner": "booking_time_followup",
                    "grounded_referents": {
                        "service": "Маникюр",
                        "specialist": "Айгерим",
                    },
                    "confirmation_state": None,
                    "degrade_reason": None,
                },
                "projections": {
                    "expected_reply_type": "time",
                    "expected_reply_reason": "collect:datetime",
                    "session_memory_interaction_state": {
                        "resume_slot": "datetime",
                        "interaction_target": "time",
                        "interaction_relation": "ask_about_requested_slot",
                        "interaction_owner": "booking_time_followup",
                        "grounded_referents": {
                            "service": "Маникюр",
                            "specialist": "Айгерим",
                        },
                        "confirmation_state": None,
                        "degrade_reason": None,
                    },
                },
                "meta": {"writer": "dialog_state_service", "current_goal": "booking"},
            },
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "2026-03-29T19:00:00+00:00",
                "last_question": "datetime",
            },
            "expected_reply_type": "time",
            "expected_reply_reason": "collect:datetime",
            "current_goal": "booking",
        }
    }
    decision = build_test_policy_override_decision(
        {
            "action": "fact",
            "intent": "duration",
            "tool_action": "catalog.service_query",
            "slots": {"service": "Маникюр"},
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    updated, dialog_state, booking_payload = service.write_runtime_payload(
        context,
        decision=decision,
        execution_meta={
            "slot_values": {"service": "Маникюр"},
            "info_sections": ["duration"],
        },
        now=now,
    )

    runtime_payload = updated["consultant_runtime"]
    assert "expected_reply_type" not in runtime_payload
    assert "expected_reply_reason" not in runtime_payload
    assert "expected_reply_type" not in updated
    assert "expected_reply_reason" not in updated
    loaded = service.load_runtime_payload(updated)
    assert loaded["expected_reply_type"] == "time"
    assert loaded["expected_reply_reason"] == "collect:datetime"
    assert dialog_state.pending_question_contract.reason == "collect:datetime"
    assert dialog_state.pending_question_contract.pending_question_act is None
    assert dialog_state.pending_question_contract.pending_question_target == "time"
    assert dialog_state.pending_question_contract.active_question_relation == "ask_about_requested_slot"
    assert dialog_state.pending_question_contract.next_question == "datetime"
    assert dialog_state.interaction_state.interaction_owner == "booking_time_followup"
    assert dialog_state.interaction_state.grounded_referents == {
        "service": "Маникюр",
        "specialist": "Айгерим",
    }
    assert dialog_state.current_referents.specialist == "Айгерим"
    assert booking_payload["service"] == "Маникюр"


def test_dialog_state_service_semantic_decision_state_write_ignores_conflicting_execution_semantics() -> None:
    service = DialogStateService()
    planner = TurnPlanner()
    now = datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)
    context = {
        "consultant_runtime": {
            "schema_version": "consultant_runtime.v1",
            "dialog_state": {
                "schema_version": "dialog_state.v1",
                "pending_question_contract": {
                    "expected_reply_type": "name",
                    "reason": "stale_reason",
                    "pending_question_target": "customer",
                    "active_question_relation": "stale_relation",
                    "next_question": "name",
                    "open_questions": ["name"],
                },
                "interaction_state": {
                    "interaction_owner": "stale_owner",
                },
                "meta": {
                    "writer": "dialog_state_service",
                    "current_goal": "booking",
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "subject_kind": "service",
                        "capability": "pricing",
                        "temporal_scope": "today",
                        "resolution_mode": "stale_resolution",
                    },
                },
            },
            "booking": {
                "active": True,
                "service": "Маникюр",
                "last_question": "datetime",
            },
        }
    }
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "action": "collect",
            "intent": "booking",
            "goal": "booking",
            "capability": "booking_manage",
            "tool_action": "calendar.book_slot",
            "slots": {"service": "Маникюр"},
            "subject_kind": "booking",
            "resolution_mode": "ask_about_requested_slot",
            "temporal_scope": "requested_slot",
            "expected_reply_type": "time",
            "reason": "collect:datetime",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "memory",
                }
            },
            "entity_refs": [
                {
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "memory",
                    "value": "Маникюр",
                }
            ],
        }
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="calendar.book_slot",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    _, dialog_state, _ = service.write_runtime_payload(
        context,
        decision=decision,
        execution_meta={
            "semantic_contract": {
                "contract_version": "semantic_contract.v1",
                "subject_kind": "service",
                "capability": "pricing",
                "temporal_scope": "today",
                "resolution_mode": "stale_resolution",
                "pending_question_act": "stale_act",
                "pending_question_target": "specialist",
                "active_question_relation": "stale_relation",
                "entity_refs": [
                    {
                        "entity_id": "spc:aigerim",
                        "entity_type": "specialist",
                        "source_ref": "execution",
                        "value": "Айгерим",
                    }
                ],
                "referents": {
                    "specialist": {
                        "value": "Айгерим",
                        "entity_id": "spc:aigerim",
                        "entity_type": "specialist",
                        "source_ref": "execution",
                    }
                },
                "grounding_provenance": {
                    "pack_id": "demo_salon",
                    "resolver_id": "catalog",
                    "resolver_version": "v2",
                },
            },
            "slot_values": {
                "service": "Маникюр",
                "datetime": "2026-03-29T19:00:00+00:00",
            },
        },
        now=now,
    )

    frame = dialog_state.semantic_state.materialized_frame.model_dump(
        mode="json",
        exclude_none=True,
    )
    assert frame["subject"]["kind"] == "booking"
    assert frame["capability_selection"]["capability"] == "booking_manage"
    assert frame["capability_selection"]["resolution_mode"] == "ask_about_requested_slot"
    assert frame["constraints"]["temporal_scope"] == "requested_slot"
    assert frame["continuation"]["pending_question_target"] == "time"
    assert frame["continuation"]["active_question_relation"] == "ask_about_requested_slot"
    assert frame["constraints"]["grounding_provenance"] == {
        "pack_id": "demo_salon",
        "resolver_id": "catalog",
        "resolver_version": "v2",
    }
    assert frame["referents"]["specialist"] == {
        "value": "Айгерим",
        "entity_id": "spc:aigerim",
        "entity_type": "specialist",
        "source_ref": "execution",
    }
    assert dialog_state.pending_question_contract.model_dump(mode="json", exclude_none=True) == {
        "expected_reply_type": "time",
        "reason": "collect:datetime",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }
    assert dialog_state.meta["semantic_contract"]["capability"] == "booking_manage"
    assert dialog_state.meta["semantic_contract"]["subject_kind"] == "booking"
    assert dialog_state.meta["semantic_contract"]["pending_question_target"] == "time"
    assert dialog_state.meta["semantic_contract"]["active_question_relation"] == "ask_about_requested_slot"
    assert dialog_state.meta["semantic_contract"]["grounding_provenance"] == {
        "pack_id": "demo_salon",
        "resolver_id": "catalog",
        "resolver_version": "v2",
    }


def test_dialog_state_service_semantic_decision_state_write_reads_executor_enrichment_only() -> None:
    service = DialogStateService()
    planner = TurnPlanner()
    now = datetime(2026, 3, 27, 12, 5, tzinfo=timezone.utc)
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "action": "collect",
            "intent": "booking",
            "goal": "booking",
            "capability": "booking_manage",
            "tool_action": "calendar.book_slot",
            "slots": {"service": "Маникюр"},
            "subject_kind": "booking",
            "resolution_mode": "ask_about_requested_slot",
            "temporal_scope": "requested_slot",
            "expected_reply_type": "time",
            "reason": "collect:datetime",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "memory",
                }
            },
        }
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="calendar.book_slot",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    _, dialog_state, _ = service.write_runtime_payload(
        {},
        decision=decision,
        execution_meta={
            "semantic_enrichment": {
                "referents": {
                    "specialist": {
                        "value": "Айгерим",
                        "entity_id": "spc:aigerim",
                        "entity_type": "specialist",
                        "source_ref": "execution",
                    }
                },
                "grounding_provenance": {
                    "pack_id": "demo_salon",
                    "resolver_id": "catalog",
                    "resolver_version": "v2",
                },
            },
            "slot_values": {
                "service": "Маникюр",
                "datetime": "2026-03-29T19:00:00+00:00",
            },
        },
        now=now,
    )

    frame = dialog_state.semantic_state.materialized_frame.model_dump(
        mode="json",
        exclude_none=True,
    )
    assert frame["subject"]["kind"] == "booking"
    assert frame["capability_selection"]["capability"] == "booking_manage"
    assert frame["constraints"]["grounding_provenance"] == {
        "pack_id": "demo_salon",
        "resolver_id": "catalog",
        "resolver_version": "v2",
    }
    assert frame["referents"]["specialist"] == {
        "value": "Айгерим",
        "entity_id": "spc:aigerim",
        "entity_type": "specialist",
        "source_ref": "execution",
    }
    assert dialog_state.pending_question_contract.model_dump(mode="json", exclude_none=True) == {
        "expected_reply_type": "time",
        "reason": "collect:datetime",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }
    assert dialog_state.meta["semantic_contract"]["capability"] == "booking_manage"
    assert dialog_state.meta["semantic_contract"]["subject_kind"] == "booking"
    assert dialog_state.meta["semantic_contract"]["grounding_provenance"] == {
        "pack_id": "demo_salon",
        "resolver_id": "catalog",
        "resolver_version": "v2",
    }


def test_dialog_state_service_owner_backed_state_write_ignores_conflicting_booking_semantics() -> None:
    service = DialogStateService()
    planner = TurnPlanner()
    now = datetime(2026, 3, 27, 12, 10, tzinfo=timezone.utc)
    context = {
        "consultant_runtime": {
            "schema_version": "consultant_runtime.v1",
            "dialog_state": {
                "schema_version": "dialog_state.v1",
                "meta": {
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "capability": "stale_meta",
                        "referents": {
                            "service": {
                                "value": "Педикюр",
                                "entity_id": "svc:pedicure",
                                "entity_type": "service",
                                "source_ref": "stale_meta",
                            }
                        },
                    }
                },
            },
            "booking": {
                "active": True,
                "service": "Педикюр",
                "last_question": "datetime",
            },
        }
    }
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "action": "collect",
            "intent": "booking",
            "goal": "booking",
            "capability": "booking_manage",
            "tool_action": "calendar.book_slot",
            "slots": {"service": "Маникюр"},
            "subject_kind": "booking",
            "resolution_mode": "ask_about_requested_slot",
            "expected_reply_type": "time",
            "reason": "collect:datetime",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "entity_refs": [
                {
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                    "value": "Маникюр",
                }
            ],
        }
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    _, dialog_state, booking_payload = service.write_runtime_payload(
        context,
        decision=decision,
        execution_meta={"slot_values": {"service": "Педикюр"}, "next_slot": "datetime"},
        now=now,
    )

    assert booking_payload["service"] == "Педикюр"
    assert dialog_state.current_referents.service == "Маникюр"
    assert dialog_state.meta["semantic_contract"]["capability"] == "booking_manage"
    assert dialog_state.meta["semantic_contract"]["referents"]["service"] == {
        "value": "Маникюр",
        "entity_id": "svc:manicure",
        "entity_type": "service",
        "source_ref": "message",
    }


def test_dialog_state_service_omits_empty_pending_question_contract_in_runtime_payload() -> None:
    service = DialogStateService()
    decision = build_test_policy_override_decision(
        {
            "intent": "hours",
            "action": "fact",
            "tool_action": "catalog.service_query",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    updated, dialog_state, _ = service.write_runtime_payload(
        {},
        decision=decision,
        execution_meta={"info_sections": ["hours"]},
        now=datetime(2026, 3, 25, 12, 18, tzinfo=timezone.utc),
    )

    assert dialog_state.pending_question_contract.next_question is None
    assert "pending_question_contract" not in updated["consultant_runtime"]


def test_dialog_state_service_fact_owner_contract_overrides_stale_booking_followup() -> None:
    service = DialogStateService()
    planner = TurnPlanner()
    now = datetime(2026, 3, 26, 12, 18, tzinfo=timezone.utc)
    context = {
        "expected_reply_type": "time",
        "expected_reply_reason": "collect:datetime",
        "current_goal": "booking",
        "consultant_runtime": {
            "schema_version": "consultant_runtime.v1",
            "dialog_state": {
                "schema_version": "dialog_state.v1",
                "current_referents": {
                    "service": "Маникюр",
                    "specialist": None,
                    "branch": None,
                    "booking": None,
                    "customer": None,
                },
                "pending_question_contract": {
                    "expected_reply_type": "time",
                    "reason": "collect:datetime",
                    "pending_question_act": "ask_about_requested_slot",
                    "pending_question_target": "time",
                    "active_question_relation": "ask_about_requested_slot",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                },
                "interaction_state": {
                    "resume_slot": "datetime",
                    "interaction_target": "time",
                    "interaction_relation": "ask_about_requested_slot",
                    "interaction_owner": "booking_time_followup",
                    "grounded_referents": {"service": "Маникюр"},
                },
                "projections": {
                    "expected_reply_type": "time",
                    "expected_reply_reason": "collect:datetime",
                },
                "meta": {"writer": "dialog_state_service", "current_goal": "booking"},
            },
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "2026-03-29T19:00:00+00:00",
                "last_question": "name",
            },
            "pending_question_contract": {
                "expected_reply_type": "time",
                "reason": "collect:datetime",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
                "next_question": "datetime",
                "open_questions": ["datetime"],
            },
            "expected_reply_type": "time",
            "expected_reply_reason": "collect:datetime",
            "current_goal": "booking",
        },
    }
    decision = build_test_policy_override_decision(
        {
            "action": "fact",
            "intent": "duration",
            "tool_action": "catalog.service_query",
            "reason": "collect:name",
            "slots": {"service": "Маникюр"},
            "next_question": "name",
            "open_questions": ["name"],
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "generic_info_interrupt",
            "goal": "booking",
            "subject_kind": "service",
            "capability": "duration",
            "resolution_mode": "policy_fact",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="generic_info_interrupt",
        source="llm_policy_core",
    )

    updated, dialog_state, booking_payload = service.write_runtime_payload(
        context,
        decision=decision,
        execution_meta={
            "slot_values": {"service": "Маникюр"},
            "info_sections": ["duration"],
        },
        now=now,
    )

    runtime_payload = updated["consultant_runtime"]
    assert "expected_reply_type" not in runtime_payload
    assert "expected_reply_reason" not in runtime_payload
    assert "pending_question_contract" not in runtime_payload
    assert "expected_reply_type" not in updated
    assert "expected_reply_reason" not in updated
    loaded = service.load_runtime_payload(updated)
    assert loaded["expected_reply_type"] == "name"
    assert loaded["expected_reply_reason"] == "collect:name"
    assert dialog_state.pending_question_contract.model_dump(mode="json", exclude_none=True) == {
        "expected_reply_type": "name",
        "reason": "collect:name",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "generic_info_interrupt",
        "next_question": "name",
        "open_questions": ["name"],
    }
    assert dialog_state.pending_question_contract.next_question == "name"
    assert dialog_state.pending_question_contract.expected_reply_type == "name"
    assert dialog_state.pending_question_contract.active_question_relation == "generic_info_interrupt"
    assert dialog_state.interaction_state.interaction_owner == "llm_policy_core_fact"
    assert booking_payload["service"] == "Маникюр"


def test_dialog_state_service_check_booking_fact_keeps_owner_reference_followup_without_stale_booking_interrupt() -> None:
    service = DialogStateService()
    planner = TurnPlanner()
    now = datetime(2026, 3, 26, 12, 24, tzinfo=timezone.utc)
    context = {
        "expected_reply_type": "time",
        "expected_reply_reason": "collect:datetime",
        "current_goal": "booking",
        "consultant_runtime": {
            "schema_version": "consultant_runtime.v1",
            "dialog_state": {
                "schema_version": "dialog_state.v1",
                "current_referents": {
                    "service": "Наращивание гелем",
                    "specialist": None,
                    "branch": None,
                    "booking": None,
                    "customer": None,
                },
                "pending_question_contract": {
                    "expected_reply_type": "time",
                    "reason": "collect:datetime",
                    "pending_question_act": "ask_about_requested_slot",
                    "pending_question_target": "time",
                    "active_question_relation": "ask_about_requested_slot",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                },
                "interaction_state": {
                    "resume_slot": "datetime",
                    "interaction_target": "time",
                    "interaction_relation": "ask_about_requested_slot",
                    "interaction_owner": "booking_time_followup",
                    "grounded_referents": {"service": "Наращивание гелем"},
                },
                "projections": {
                    "expected_reply_type": "time",
                    "expected_reply_reason": "collect:datetime",
                },
                "meta": {
                    "writer": "dialog_state_service",
                    "current_goal": "booking",
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "subject_kind": "booking",
                        "capability": "bookability",
                        "resolution_mode": "ask_about_requested_slot",
                        "pending_question_act": "ask_about_requested_slot",
                        "pending_question_target": "time",
                        "active_question_relation": "ask_about_requested_slot",
                        "referents": {
                            "service": {
                                "value": "Наращивание гелем",
                                "entity_id": "svc:gel_extension",
                                "entity_type": "service",
                                "source_ref": "memory",
                            }
                        },
                    },
                },
            },
            "booking": {
                "active": True,
                "service": "Наращивание гелем",
                "last_question": "datetime",
            },
            "pending_question_contract": {
                "expected_reply_type": "time",
                "reason": "collect:datetime",
                "pending_question_act": "ask_about_requested_slot",
                "pending_question_target": "time",
                "active_question_relation": "ask_about_requested_slot",
                "next_question": "datetime",
                "open_questions": ["datetime"],
            },
            "expected_reply_type": "time",
            "expected_reply_reason": "collect:datetime",
            "current_goal": "booking",
        },
    }
    decision = build_test_policy_override_decision(
        {
            "action": "fact",
            "intent": "check_booking",
            "tool_action": "calendar.get_booking",
            "reason": "calendar_get_booking_collect_reference",
            "expected_reply_type": "name",
            "next_question": "name",
            "open_questions": ["name"],
            "goal": "booking",
            "subject_kind": "booking",
            "capability": "booking_manage",
            "resolution_mode": "direct",
            "referents": {
                "service": {
                    "value": "Наращивание гелем",
                    "entity_id": "svc:gel_extension",
                    "entity_type": "service",
                    "source_ref": "memory",
                }
            },
        },
        interaction_owner="llm_policy_core",
        interaction_relation=None,
        source="llm_policy_core",
    )

    updated, dialog_state, booking_payload = service.write_runtime_payload(
        context,
        decision=decision,
        execution_meta={"tool_decision": "not_found"},
        now=now,
    )

    runtime_payload = updated["consultant_runtime"]
    assert "expected_reply_type" not in runtime_payload
    assert "expected_reply_reason" not in runtime_payload
    assert "pending_question_contract" not in runtime_payload
    assert "expected_reply_type" not in updated
    assert "expected_reply_reason" not in updated
    loaded = service.load_runtime_payload(updated)
    assert loaded["expected_reply_type"] == "name"
    assert loaded["expected_reply_reason"] == "calendar_get_booking_collect_reference"
    assert dialog_state.pending_question_contract.model_dump(mode="json", exclude_none=True) == {
        "expected_reply_type": "name",
        "reason": "calendar_get_booking_collect_reference",
        "next_question": "name",
        "open_questions": ["name"],
    }
    assert dialog_state.pending_question_contract.expected_reply_type == "name"
    assert dialog_state.pending_question_contract.next_question == "name"
    assert dialog_state.meta["semantic_contract"]["capability"] == "booking_manage"
    assert "pending_question_act" not in dialog_state.meta["semantic_contract"]
    assert "pending_question_target" not in dialog_state.meta["semantic_contract"]
    assert "active_question_relation" not in dialog_state.meta["semantic_contract"]
    assert booking_payload["service"] == "Наращивание гелем"


def test_dialog_state_service_clears_expected_reply_contract_on_handoff() -> None:
    service = DialogStateService()
    planner = TurnPlanner()
    now = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
    context = {
        "consultant_runtime": {
            "schema_version": "consultant_runtime.v1",
            "dialog_state": {
                "schema_version": "dialog_state.v1",
                "current_referents": {
                    "service": "Маникюр",
                    "specialist": None,
                    "branch": None,
                    "booking": None,
                    "customer": None,
                },
                "pending_question_contract": {
                    "expected_reply_type": "time",
                    "reason": "collect:datetime",
                    "pending_question_act": "ask_about_requested_slot",
                    "pending_question_target": "time",
                    "active_question_relation": "ask_about_requested_slot",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                },
                "interaction_state": {
                    "resume_slot": "datetime",
                    "interaction_target": "time",
                    "interaction_relation": "ask_about_requested_slot",
                    "interaction_owner": "booking_time_followup",
                    "grounded_referents": {"service": "Маникюр"},
                    "confirmation_state": None,
                    "degrade_reason": None,
                },
                "projections": {
                    "expected_reply_type": "time",
                    "expected_reply_reason": "collect:datetime",
                    "session_memory_interaction_state": {
                        "resume_slot": "datetime",
                        "interaction_target": "time",
                        "interaction_relation": "ask_about_requested_slot",
                        "interaction_owner": "booking_time_followup",
                        "grounded_referents": {"service": "Маникюр"},
                        "confirmation_state": None,
                        "degrade_reason": None,
                    },
                },
                "meta": {"writer": "dialog_state_service", "current_goal": "booking"},
            },
            "booking": {
                "active": True,
                "service": "Маникюр",
                "datetime": "2026-03-29T19:00:00+00:00",
                "last_question": "datetime",
            },
            "expected_reply_type": "time",
            "expected_reply_reason": "collect:datetime",
            "current_goal": "booking",
        }
    }
    decision = build_test_policy_override_decision(
        {
            "action": "handoff",
            "intent": "booking",
            "tool_action": "handoff",
            "reason": "handoff_booking",
            "subject_kind": "booking",
            "capability": "booking_manage",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "slots": {"service": "Маникюр"},
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="ask_about_requested_slot",
        source="llm_policy_core",
    )

    updated, dialog_state, booking_payload = service.write_runtime_payload(
        context,
        decision=decision,
        execution_meta={"handoff_requested": True},
        now=now,
    )

    runtime_payload = updated["consultant_runtime"]
    assert runtime_payload["booking"]["service"] == "Маникюр"
    assert "expected_reply_type" not in runtime_payload
    assert "expected_reply_reason" not in runtime_payload
    assert "pending_question_contract" not in runtime_payload
    assert "current_goal" not in runtime_payload
    assert "expected_reply_type" not in updated
    assert "expected_reply_reason" not in updated
    assert "current_goal" not in updated
    assert dialog_state.pending_question_contract.next_question is None
    assert dialog_state.projections.expected_reply_type is None
    assert booking_payload["service"] == "Маникюр"


def test_dialog_state_service_persists_specialist_followup_referent_on_collect() -> None:
    service = DialogStateService()
    planner = TurnPlanner()
    now = datetime(2026, 3, 25, 12, 20, tzinfo=timezone.utc)
    context = {
        "consultant_runtime": {
            "schema_version": "consultant_runtime.v1",
            "booking": {
                "active": True,
                "service": "Маникюр",
                "last_question": "datetime",
            },
            "expected_reply_type": "time",
            "expected_reply_reason": "collect:datetime",
            "current_goal": "booking",
        }
    }
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "goal": "booking",
            "slots": {"service": "Маникюр"},
            "tool_args": {},
            "entity_refs": [
                {
                    "entity_id": "spec:aigerim",
                    "entity_type": "specialist",
                    "value": "Айгерим",
                    "source_ref": "message",
                },
                {
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "value": "Маникюр",
                    "source_ref": "booking_state",
                }
            ],
            "referents": {
                "specialist": {
                    "value": "Айгерим",
                    "entity_id": "spec:aigerim",
                    "entity_type": "specialist",
                    "source_ref": "message",
                },
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "booking_state",
                },
            },
            "next_question": "datetime",
            "open_questions": ["datetime"],
            "pending_question_target": "specialist",
            "active_question_relation": "referent_followup",
            "resolution_mode": "referent_followup",
            "subject_kind": "specialist",
            "capability": "bookability",
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="referent_followup",
        source="llm_policy_core",
    )

    updated, dialog_state, booking_payload = service.write_runtime_payload(
        context,
        decision=decision,
        execution_meta={"slot_values": {"service": "Маникюр"}, "next_slot": "datetime"},
        now=now,
    )

    runtime_payload = updated["consultant_runtime"]
    assert "expected_reply_type" not in runtime_payload
    assert "expected_reply_type" not in updated
    loaded = service.load_runtime_payload(updated)
    assert loaded["expected_reply_type"] == "time"
    assert dialog_state.pending_question_contract.reason == "collect:datetime"
    assert dialog_state.pending_question_contract.pending_question_act is None
    assert dialog_state.pending_question_contract.pending_question_target == "specialist"
    assert dialog_state.pending_question_contract.active_question_relation == "referent_followup"
    assert dialog_state.pending_question_contract.next_question == "datetime"
    assert dialog_state.current_referents.specialist == "Айгерим"
    assert dialog_state.interaction_state.grounded_referents["specialist"] == "Айгерим"
    assert booking_payload["specialist_name"] == "Айгерим"
    assert "semantic_contract" not in runtime_payload
    semantic_contract = dialog_state.meta["semantic_contract"]
    assert semantic_contract["subject_kind"] == "specialist"
    assert semantic_contract["capability"] == "bookability"
    assert semantic_contract["pending_question_target"] == "specialist"
    assert semantic_contract["active_question_relation"] == "referent_followup"
    assert semantic_contract["referents"]["service"] == {
        "value": "Маникюр",
        "entity_id": "svc:manicure",
        "entity_type": "service",
        "source_ref": "booking_state",
    }
    assert semantic_contract["referents"]["specialist"] == {
        "value": "Айгерим",
        "entity_id": "spec:aigerim",
        "entity_type": "specialist",
        "source_ref": "message",
    }


def test_dialog_state_service_merges_execution_semantic_grounding_into_runtime_contract() -> None:
    service = DialogStateService()
    decision = build_test_policy_override_decision(
        {
            "intent": "pricing",
            "action": "fact",
            "tool_action": "info",
            "subject_kind": "service",
            "capability": "pricing",
            "temporal_scope": "none",
            "resolution_mode": "policy_fact",
            "goal": "info",
        },
        interaction_owner="llm_policy_core_fact",
        interaction_relation="grounded_fact",
        source="llm_policy_core",
    )

    execution_meta = {
        "semantic_contract": {
            "contract_version": "semantic_contract.v1",
            "entity_refs": [
                {
                    "entity_id": "service:manikyur",
                    "entity_type": "service",
                    "value": "Маникюр",
                    "source_ref": "truth:pricing",
                    "confidence": 0.91,
                }
            ],
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "service:manikyur",
                    "entity_type": "service",
                    "source_ref": "truth:pricing",
                }
            },
            "grounding_provenance": {
                "pack_id": "demo_salon",
                "entity_id": "price_item:manikyur",
                "source_ref": "truth:pricing",
                "resolver_id": "pack_query_engine",
                "resolver_version": "2026-03-25",
                "confidence": 0.91,
            },
        }
    }

    updated, dialog_state, _ = service.write_runtime_payload(
        {},
        decision=decision,
        execution_meta=execution_meta,
        now=datetime(2026, 3, 25, 12, 24, tzinfo=timezone.utc),
    )

    runtime_payload = updated["consultant_runtime"]
    assert "semantic_contract" not in runtime_payload
    semantic_contract = dialog_state.meta["semantic_contract"]
    assert semantic_contract["referents"]["service"] == {
        "value": "Маникюр",
        "entity_id": "service:manikyur",
        "entity_type": "service",
        "source_ref": "truth:pricing",
    }
    assert semantic_contract["entity_refs"] == [
        {
            "entity_id": "service:manikyur",
            "entity_type": "service",
            "value": "Маникюр",
            "source_ref": "truth:pricing",
            "confidence": 0.91,
        }
    ]
    assert semantic_contract["grounding_provenance"] == {
        "pack_id": "demo_salon",
        "entity_id": "price_item:manikyur",
        "source_ref": "truth:pricing",
        "resolver_id": "pack_query_engine",
        "resolver_version": "2026-03-25",
        "confidence": 0.91,
    }
    assert dialog_state.current_referents.service == "Маникюр"
    assert dialog_state.interaction_state.grounded_referents["service"] == "Маникюр"


def test_dialog_state_service_load_runtime_payload_prefers_conversation_projection_over_stale_dialog_state() -> None:
    service = DialogStateService()
    context = {
        "consultant_runtime": {
            "schema_version": "consultant_runtime.v1",
            "conversation_projection": {
                "schema_version": "conversation_projection.v1",
                "projection_version": "v1",
                "conversation_id": "conv-1",
                "last_turn_id": "turn-1",
                "current_semantic_decision_ref": "decision-1",
                "active_capability": "bookability",
                "semantic_slots": {"service": "Маникюр"},
                "missing_information": {
                    "expected_reply_type": "time",
                    "reason": "collect:datetime",
                    "pending_question_act": "ask_about_requested_slot",
                    "pending_question_target": "time",
                    "active_question_relation": "ask_about_requested_slot",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                },
                "active_workflow_ref": "calendar.list_slots",
                "pending_handoff_state": {},
                "last_reply_ref": None,
                "compatibility_view_refs": {
                    "dialog_state": "consultant_runtime.dialog_state.v1",
                },
                "semantic_frame": {
                    "schema_version": "semantic_frame.v2",
                    "user_goal": "booking",
                    "requested_effect": "collect_missing_input",
                    "subject": {"kind": "service", "value": "Маникюр"},
                    "referents": {
                        "service": {
                            "value": "Маникюр",
                            "entity_id": "svc:manicure",
                            "entity_type": "service",
                            "source_ref": "carryover",
                        }
                    },
                    "constraints": {},
                    "preferences": {},
                    "continuation": {
                        "expected_reply_type": "time",
                        "next_question": "datetime",
                        "open_questions": ["datetime"],
                        "slot_values": {"service": "Маникюр"},
                    },
                    "capability_selection": {"capability": "bookability"},
                    "needs_human": False,
                    "reason": "collect_datetime",
                },
                "semantic_contract": {
                    "contract_version": "semantic_contract.v1",
                    "capability": "bookability",
                },
                "pending_question_contract": {
                    "expected_reply_type": "time",
                    "reason": "collect:datetime",
                    "pending_question_act": "ask_about_requested_slot",
                    "pending_question_target": "time",
                    "active_question_relation": "ask_about_requested_slot",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                },
                "current_goal": "booking",
                "booking_state": {"active": True, "service": "Маникюр", "last_question": "datetime"},
            },
            "dialog_state": {
                "schema_version": "dialog_state.v1",
                "semantic_state": {
                    "schema_version": "canonical_semantic_state.v1",
                    "materialized_frame": {
                        "schema_version": "semantic_frame.v2",
                        "user_goal": "consult",
                        "requested_effect": "answer_question",
                        "subject": {},
                        "referents": {},
                        "constraints": {},
                        "preferences": {},
                        "continuation": {},
                        "capability_selection": {},
                        "needs_human": False,
                        "reason": "consult",
                    },
                    "event_log": [],
                },
                "pending_question_contract": {
                    "expected_reply_type": "service_choice",
                    "reason": "stale",
                    "next_question": "service",
                    "open_questions": ["service"],
                },
                "current_referents": {},
                "interaction_state": {"interaction_owner": "legacy"},
                "projections": {"expected_reply_type": "service_choice", "expected_reply_reason": "stale"},
                "meta": {"current_goal": "consult"},
            },
            "booking": {"active": True, "service": "Старый"},
        },
        "current_goal": "consult",
        "expected_reply_type": "service_choice",
    }

    payload = service.load_runtime_payload(context)

    assert isinstance(payload["conversation_projection"], ConversationProjectionV1)
    assert payload["current_goal"] == "booking"
    assert payload["booking_payload"]["service"] == "Маникюр"
    assert payload["dialog_state"].pending_question_contract.expected_reply_type == "time"
    assert payload["dialog_state"].meta["current_goal"] == "booking"


def test_dialog_state_service_load_runtime_payload_builds_projection_without_synthetic_policy_decision() -> None:
    service = DialogStateService()
    context = {
        "consultant_runtime": {
            "dialog_state": {
                "schema_version": "dialog_state.v1",
                "semantic_state": {
                    "schema_version": "canonical_semantic_state.v1",
                    "materialized_frame": {
                        "schema_version": "semantic_frame.v2",
                        "user_goal": "booking",
                        "requested_effect": "collect_missing_input",
                        "subject": {"kind": "service", "value": "Маникюр"},
                        "referents": {
                            "service": {
                                "value": "Маникюр",
                                "entity_id": "svc:manicure",
                                "entity_type": "service",
                                "source_ref": "carryover",
                            }
                        },
                        "constraints": {},
                        "preferences": {},
                        "continuation": {
                            "expected_reply_type": "time",
                            "next_question": "datetime",
                            "open_questions": ["datetime"],
                            "slot_values": {"service": "Маникюр"},
                        },
                        "capability_selection": {"capability": "bookability"},
                        "needs_human": False,
                        "reason": "collect_datetime",
                    },
                    "event_log": [],
                },
                "pending_question_contract": {
                    "expected_reply_type": "time",
                    "reason": "collect:datetime",
                    "pending_question_act": "ask_about_requested_slot",
                    "pending_question_target": "time",
                    "active_question_relation": "ask_about_requested_slot",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                },
                "current_referents": {},
                "interaction_state": {"interaction_owner": "dialog_state_service"},
                "projections": {"expected_reply_type": "time", "expected_reply_reason": "collect:datetime"},
                "meta": {
                    "current_goal": "booking",
                    "semantic_contract": {
                        "contract_version": "semantic_contract.v1",
                        "capability": "bookability",
                    },
                },
            },
            "booking": {"active": True, "service": "Маникюр", "last_question": "datetime"},
        },
    }

    payload = service.load_runtime_payload(context)

    projection = payload["conversation_projection"]
    assert isinstance(projection, ConversationProjectionV1)
    assert projection.current_semantic_decision_ref is None
    assert projection.last_turn_id is None
    assert projection.active_workflow_ref is None
    assert projection.pending_handoff_state == {}
    assert projection.current_goal == "booking"
    assert projection.semantic_contract["capability"] == "bookability"
    assert projection.pending_question_contract["expected_reply_type"] == "time"


def test_dialog_state_service_write_runtime_payload_reprojects_compatibility_continuity_from_canonical_runtime_state() -> None:
    service = DialogStateService()
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "tool_action_hint": "calendar.list_slots",
            "goal": "booking",
            "reason": "collect_datetime",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "ask_about_requested_slot",
            "slots": {"service": "Маникюр"},
            "expected_reply_type": "time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="ask_about_requested_slot",
        source="llm_policy_core",
    )
    context = {
        "context_manager": {
            "message_count": 4,
            "current_goal": "handoff",
            "canonical_dialog_state": {
                "owner_id": "context_manager.dialog_state.v1",
                "version": "v1",
                "pending_question_contract": {
                    "expected_reply_type": "name",
                    "reason": "stale_projection",
                    "next_question": "name",
                    "open_questions": ["name"],
                },
            },
        },
        "expected_reply_type": "name",
        "expected_reply_reason": "stale_projection",
        "current_goal": "handoff",
        "session_memory": {
            "active_goal": "handoff",
            "pending_question_contract": {
                "expected_reply_type": "name",
                "reason": "stale_projection",
                "next_question": "name",
                "open_questions": ["name"],
            },
        },
    }

    updated, dialog_state, _ = service.write_runtime_payload(
        context,
        decision=decision,
        execution_meta={},
        now=datetime(2026, 3, 31, 8, 0, tzinfo=timezone.utc),
    )

    expected_pending_question = {
        "expected_reply_type": "time",
        "reason": "collect_datetime",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }

    assert "expected_reply_type" not in updated
    assert "expected_reply_reason" not in updated
    assert "current_goal" not in updated
    assert dialog_state.pending_question_contract.model_dump(mode="json", exclude_none=True) == expected_pending_question
    assert dialog_state.meta["current_goal"] == "booking"
    assert updated["context_manager"]["current_goal"] == "booking"
    assert updated["context_manager"]["canonical_dialog_state"]["pending_question_contract"] == expected_pending_question
    assert updated["session_memory"]["active_goal"] == "booking"
    assert updated["session_memory"]["pending_question_contract"] == expected_pending_question
    assert updated["session_memory"]["interaction_state"]["resume_slot"] == "datetime"


def test_dialog_state_service_write_runtime_payload_captures_pending_resume_from_canonical_runtime_state() -> None:
    service = DialogStateService()
    collect = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "tool_action_hint": "calendar.list_slots",
            "goal": "booking",
            "reason": "collect_datetime",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "ask_about_requested_slot",
            "slots": {"service": "Маникюр"},
            "expected_reply_type": "time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="ask_about_requested_slot",
        source="llm_policy_core",
    )
    handoff = build_test_policy_override_decision(
        {
            "intent": "handoff",
            "action": "handoff",
            "tool_action": "handoff",
            "goal": "booking",
            "reason": "user_requests_human",
            "subject_kind": "conversation",
            "capability": "handoff",
            "resolution_mode": "policy_handoff",
        },
        interaction_owner="llm_policy_core_booking",
        interaction_relation="manager_handoff",
        source="llm_policy_core",
    )

    updated, _dialog_state, _ = service.write_runtime_payload(
        {},
        decision=collect,
        execution_meta={},
        now=datetime(2026, 3, 31, 8, 0, tzinfo=timezone.utc),
    )
    handoff_updated, _handoff_state, _ = service.write_runtime_payload(
        updated,
        decision=handoff,
        execution_meta={},
        now=datetime(2026, 3, 31, 8, 1, tzinfo=timezone.utc),
    )

    expected_pending_question = {
        "expected_reply_type": "time",
        "reason": "collect_datetime",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }
    pending_resume = handoff_updated["pending_resume"]

    assert pending_resume["context_manager"]["current_goal"] == "booking"
    assert pending_resume["context_manager"]["canonical_dialog_state"]["pending_question_contract"] == expected_pending_question
    assert pending_resume["expected_reply_type"] == "time"
    assert pending_resume["expected_reply_reason"] == "collect_datetime"
    assert pending_resume["booking"]["service"] == "Маникюр"
    assert "current_goal" not in handoff_updated



def test_dialog_state_service_write_runtime_payload_emits_turn_journal_and_conversation_projection() -> None:
    service = DialogStateService()
    decision = build_test_policy_override_decision(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "tool_action_hint": "calendar.list_slots",
            "goal": "booking",
            "reason": "collect_datetime",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "ask_about_requested_slot",
            "slots": {"service": "Маникюр"},
            "referents": {
                "service": {
                    "value": "Маникюр",
                    "entity_id": "svc:manicure",
                    "entity_type": "service",
                    "source_ref": "message",
                }
            },
            "expected_reply_type": "time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        },
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    updated, dialog_state, _ = service.write_runtime_payload(
        {},
        decision=decision,
        execution_meta={"slot_values": {"service": "Маникюр"}, "next_slot": "datetime"},
        now=datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc),
        conversation_id="conv-1",
        trace_id="trace-1",
    )

    runtime_payload = updated["consultant_runtime"]
    turn_journal = TurnJournalV1.model_validate(runtime_payload["turn_journal"])
    projection = ConversationProjectionV1.model_validate(runtime_payload["conversation_projection"])

    assert [event.event_type for event in turn_journal.events] == [
        "BindingPlanIssued",
        "ExecutionCompleted",
    ]
    assert turn_journal.conversation_id == "conv-1"
    assert projection.conversation_id == "conv-1"
    assert projection.current_semantic_decision_ref is None
    assert projection.active_capability == "bookability"
    assert projection.current_goal == "booking"
    assert projection.pending_question_contract["expected_reply_type"] == "time"
    assert projection.booking_state["service"] == "Маникюр"
    assert runtime_payload["dialog_state"]["semantic_state"]["materialized_frame"]["user_goal"] == "booking"
    assert dialog_state.meta["current_goal"] == "booking"


def test_dialog_state_service_owner_backed_projection_sets_semantic_decision_ref() -> None:
    service = DialogStateService()
    planner = TurnPlanner()
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(
        {
            "intent": "booking",
            "action": "collect",
            "tool_action": "collect",
            "tool_action_hint": "collect",
            "goal": "booking",
            "reason": "collect_datetime",
            "subject_kind": "service",
            "capability": "bookability",
            "resolution_mode": "ask_about_requested_slot",
            "slots": {"service": "Маникюр"},
            "expected_reply_type": "time",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
            "active_question_relation": "ask_about_requested_slot",
            "next_question": "datetime",
            "open_questions": ["datetime"],
        }
    )
    decision = planner.build_from_semantic_decision(
        semantic_decision,
        binding_tool_action="collect",
        interaction_owner="llm_policy_core",
        source="llm_policy_core",
    )

    updated, dialog_state, _ = service.write_runtime_payload(
        {},
        decision=decision,
        execution_meta={"slot_values": {"service": "Маникюр"}, "next_slot": "datetime"},
        now=datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc),
        conversation_id="conv-owner",
        trace_id="trace-owner",
    )

    projection = ConversationProjectionV1.model_validate(
        updated["consultant_runtime"]["conversation_projection"]
    )

    assert projection.current_semantic_decision_ref == semantic_decision.decision_id
    assert projection.semantic_slots == {"service": "Маникюр"}
    assert projection.current_goal == "booking"
    assert projection.missing_information == {
        "expected_reply_type": "time",
        "reason": "collect_datetime",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }
    assert dialog_state.meta["current_goal"] == "booking"
