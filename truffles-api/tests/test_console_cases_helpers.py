from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import ConsoleCaseAssigneeOption
from app.services.console_case_routing import (
    CaseRoutingBookingContext,
    CaseRoutingSignalContext,
    annotate_case_assignee_options,
)
from app.services.console_errors import ConsoleAPIError


def test_parse_sort_param_defaults_to_last_activity():
    assert console_router._parse_sort_param("sort_by", None) == "last_activity"
    assert console_router._parse_sort_param("sort_by", "") == "last_activity"
    assert console_router._parse_sort_param("sort_by", "last_activity") == "last_activity"


def test_parse_sort_param_accepts_created_at():
    assert console_router._parse_sort_param("sort_by", "created_at") == "created_at"
    assert console_router._parse_sort_param("sort_by", "CREATED_AT") == "created_at"


def test_parse_sort_param_accepts_sla():
    assert console_router._parse_sort_param("sort_by", "sla") == "sla"
    assert console_router._parse_sort_param("sort_by", "SLA") == "sla"


def test_parse_sort_param_accepts_resolved_at():
    assert console_router._parse_sort_param("sort_by", "resolved_at") == "resolved_at"
    assert console_router._parse_sort_param("sort_by", "RESOLVED_AT") == "resolved_at"


def test_parse_sort_param_rejects_invalid():
    with pytest.raises(ConsoleAPIError):
        console_router._parse_sort_param("sort_by", "oops")


def test_case_status_open_param():
    assert console_router._parse_case_status_param("status", None) is None
    assert console_router._parse_case_status_param("status", "") is None
    assert console_router._parse_case_status_param("status", "open") == ["pending", "active"]
    assert console_router._parse_case_status_param("status", "OPEN") == ["pending", "active"]
    assert console_router._parse_case_status_param("status", "pending") == ["pending"]
    assert console_router._parse_case_status_param("status", "active") == ["active"]
    assert console_router._parse_case_status_param("status", "resolved") == ["resolved"]


def test_parse_case_status_param_rejects_invalid():
    with pytest.raises(ConsoleAPIError):
        console_router._parse_case_status_param("status", "oops")


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (None, None),
        ("", None),
        ("needs_reply", "needs_reply"),
        ("WAITING_CLIENT", "waiting_client"),
        ("snoozed", "snoozed"),
        ("delivery", "delivery"),
        ("unassigned", "unassigned"),
    ],
)
def test_parse_case_queue_view_param_accepts_supported_views(raw_value, expected):
    assert console_router._parse_case_queue_view_param("queue_view", raw_value) == expected


def test_parse_case_queue_view_param_rejects_invalid():
    with pytest.raises(ConsoleAPIError):
        console_router._parse_case_queue_view_param("queue_view", "paused")


def test_build_sync_status_maps_operator_message_for_client_notify_failure():
    status = console_router._build_sync_status("failed", "chatflow_failed", target="client_notify")

    assert status.status == "failed"
    assert status.detail == "chatflow_failed"
    assert status.operator_message == "Не удалось отправить системное уведомление клиенту."


def test_build_sync_status_maps_operator_message_for_telegram_failure():
    status = console_router._build_sync_status("failed", "telegram_edit_failed", target="telegram")

    assert status.status == "failed"
    assert status.detail == "telegram_edit_failed"
    assert status.operator_message == "Не удалось обновить отметку заявки в Telegram."


def test_get_case_booking_attention_reason_maps_pending_confirmation():
    assert (
        console_router._get_case_booking_attention_reason(
            "PENDING_CONFIRMATION",
            followup_done=False,
        )
        == "Нужно подтвердить визит"
    )


def test_build_case_booking_operator_summary_marks_rebooked_no_show_as_closed_loop():
    summary = console_router._build_case_booking_operator_summary(
        status="NO_SHOW",
        slot_label="06.03 10:00 · Айжан · Маникюр",
        attention_reason="Связаться после неявки",
        no_show_followup_done=True,
        no_show_followup_result="rebooked",
    )

    assert summary == "После неявки клиента уже перезаписали."


def test_parse_case_owner_filters_accepts_assignee_id():
    agent_id = uuid4()

    parsed_assignee_id, unassigned = console_router._parse_case_owner_filters(
        assigned_to_me=False,
        assignee_id=str(agent_id),
        unassigned=False,
    )

    assert parsed_assignee_id == agent_id
    assert unassigned is False


def test_parse_case_owner_filters_accepts_unassigned():
    parsed_assignee_id, unassigned = console_router._parse_case_owner_filters(
        assigned_to_me=False,
        assignee_id=None,
        unassigned=True,
    )

    assert parsed_assignee_id is None
    assert unassigned is True


def test_map_case_assignee_loads_prefers_direct_agent_id() -> None:
    agent_id = uuid4()
    options = {
        agent_id: ConsoleCaseAssigneeOption(
            agent_id=agent_id,
            agent_name="Manager",
            role="manager",
            open_case_count=0,
        ),
    }

    load_map = console_router._map_case_assignee_loads(
        options,
        [(str(agent_id), "Manager", 3)],
    )

    assert load_map[agent_id] == 3


def test_map_case_assignee_loads_uses_unique_legacy_name_fallback() -> None:
    agent_id = uuid4()
    options = {
        agent_id: ConsoleCaseAssigneeOption(
            agent_id=agent_id,
            agent_name="Manager Two",
            role="manager",
            open_case_count=0,
        ),
    }

    load_map = console_router._map_case_assignee_loads(
        options,
        [(None, "Manager Two", 2)],
    )

    assert load_map[agent_id] == 2


def test_map_case_assignee_loads_ignores_ambiguous_legacy_name() -> None:
    agent_one_id = uuid4()
    agent_two_id = uuid4()
    options = {
        agent_one_id: ConsoleCaseAssigneeOption(
            agent_id=agent_one_id,
            agent_name="Manager",
            role="manager",
            open_case_count=0,
        ),
        agent_two_id: ConsoleCaseAssigneeOption(
            agent_id=agent_two_id,
            agent_name="Manager",
            role="admin",
            open_case_count=0,
        ),
    }

    load_map = console_router._map_case_assignee_loads(
        options,
        [(None, "Manager", 4)],
    )

    assert load_map[agent_one_id] == 0
    assert load_map[agent_two_id] == 0


def test_build_case_routing_decision_prefers_lowest_load() -> None:
    current_agent_id = uuid4()
    recommended_agent_id = uuid4()
    decision, target_option = console_router._build_case_routing_decision(
        assignee_options=[
            ConsoleCaseAssigneeOption(
                agent_id=current_agent_id,
                agent_name="Manager",
                role="manager",
                is_current=True,
                open_case_count=3,
            ),
            ConsoleCaseAssigneeOption(
                agent_id=recommended_agent_id,
                agent_name="Manager Two",
                role="manager",
                is_current=False,
                open_case_count=1,
            ),
        ],
        current_assignee_id=str(current_agent_id),
        policy="least_open_cases",
    )

    assert target_option is not None
    assert decision is not None
    assert target_option.agent_id == recommended_agent_id
    assert decision.recommended_agent_id == recommended_agent_id
    assert decision.current_agent_id == current_agent_id
    assert decision.will_reassign is True
    assert decision.reason_code == "least_open_cases"


def test_build_case_routing_decision_keeps_current_owner_on_tie() -> None:
    current_agent_id = uuid4()
    other_agent_id = uuid4()
    decision, target_option = console_router._build_case_routing_decision(
        assignee_options=[
            ConsoleCaseAssigneeOption(
                agent_id=current_agent_id,
                agent_name="Manager",
                role="manager",
                is_current=True,
                open_case_count=2,
            ),
            ConsoleCaseAssigneeOption(
                agent_id=other_agent_id,
                agent_name="Manager Two",
                role="manager",
                is_current=False,
                open_case_count=2,
            ),
        ],
        current_assignee_id=str(current_agent_id),
        policy="least_open_cases",
    )

    assert target_option is not None
    assert decision is not None
    assert target_option.agent_id == current_agent_id
    assert decision.will_reassign is False
    assert decision.reason_code == "current_owner_kept"


def test_build_case_routing_decision_prefers_follow_up_owner_when_no_show_is_overdue() -> None:
    current_agent_id = uuid4()
    follow_up_owner_id = uuid4()

    decision, target_option = console_router._build_case_routing_decision(
        assignee_options=[
            ConsoleCaseAssigneeOption(
                agent_id=current_agent_id,
                agent_name="Current Manager",
                role="manager",
                is_current=True,
                open_case_count=1,
            ),
            ConsoleCaseAssigneeOption(
                agent_id=follow_up_owner_id,
                agent_name="Follow-up Manager",
                role="manager",
                is_current=False,
                open_case_count=5,
            ),
        ],
        current_assignee_id=str(current_agent_id),
        policy="follow_up_sla_balance",
        booking_context=CaseRoutingBookingContext(
            appointment_id=uuid4(),
            follow_up_owner_id=follow_up_owner_id,
            follow_up_due_at=datetime.now(timezone.utc) - timedelta(hours=2),
            follow_up_overdue=True,
        ),
        signal_context=CaseRoutingSignalContext(
            sla_status="warning",
            sla_action_state="reply_due",
            sla_overdue_minutes=None,
        ),
    )

    assert target_option is not None
    assert decision is not None
    assert target_option.agent_id == follow_up_owner_id
    assert decision.recommended_agent_id == follow_up_owner_id
    assert decision.reason_code == "follow_up_owner_overdue"
    assert decision.current_score is not None
    assert decision.recommended_score > decision.current_score
    assert any(item.code == "follow_up_owner" for item in decision.score_breakdown)
    assert any(item.code == "follow_up_overdue" for item in decision.score_breakdown)


def test_annotate_case_assignee_options_blocks_paused_and_at_capacity_agents() -> None:
    paused_agent_id = uuid4()
    capped_agent_id = uuid4()
    options = [
        ConsoleCaseAssigneeOption(
            agent_id=paused_agent_id,
            agent_name="Paused Manager",
            role="manager",
            open_case_count=0,
            routing_status="paused",
        ),
        ConsoleCaseAssigneeOption(
            agent_id=capped_agent_id,
            agent_name="Busy Manager",
            role="manager",
            open_case_count=4,
            routing_status="available",
            max_open_case_count=4,
        ),
    ]

    annotate_case_assignee_options(
        options,
        current_assignee_id=None,
        booking_context=None,
    )

    assert options[0].assignment_eligible is False
    assert options[0].assignment_block_reason_code == "paused"
    assert options[1].assignment_eligible is False
    assert options[1].assignment_block_reason_code == "at_capacity"
    assert options[1].at_capacity is True


def test_annotate_case_assignee_options_allows_follow_up_only_owner_for_matching_follow_up() -> None:
    follow_up_owner_id = uuid4()
    option = ConsoleCaseAssigneeOption(
        agent_id=follow_up_owner_id,
        agent_name="Follow-up Manager",
        role="manager",
        open_case_count=1,
        routing_status="follow_up_only",
    )

    annotate_case_assignee_options(
        [option],
        current_assignee_id=None,
        booking_context=CaseRoutingBookingContext(
            appointment_id=uuid4(),
            follow_up_owner_id=follow_up_owner_id,
            follow_up_due_at=datetime.now(timezone.utc),
            follow_up_overdue=False,
        ),
    )

    assert option.assignment_eligible is True
    assert option.assignment_block_reason_code is None


def test_build_case_routing_decision_skips_paused_candidate_even_with_lower_load() -> None:
    current_agent_id = uuid4()
    paused_agent_id = uuid4()
    decision, target_option = console_router._build_case_routing_decision(
        assignee_options=[
            ConsoleCaseAssigneeOption(
                agent_id=current_agent_id,
                agent_name="Current Manager",
                role="manager",
                is_current=True,
                open_case_count=3,
                routing_status="available",
            ),
            ConsoleCaseAssigneeOption(
                agent_id=paused_agent_id,
                agent_name="Paused Manager",
                role="manager",
                is_current=False,
                open_case_count=0,
                routing_status="paused",
            ),
        ],
        current_assignee_id=str(current_agent_id),
        policy="least_open_cases",
    )

    assert target_option is not None
    assert decision is not None
    assert target_option.agent_id == current_agent_id
    assert decision.reason_code == "current_owner_kept"


def test_adjust_case_routing_loads_rebalances_counts() -> None:
    current_agent_id = uuid4()
    next_agent_id = uuid4()
    load_map = {
        current_agent_id: 3,
        next_agent_id: 1,
    }

    console_router._adjust_case_routing_loads(
        load_map,
        previous_assignee_id=str(current_agent_id),
        next_assignee_id=str(next_agent_id),
    )

    assert load_map[current_agent_id] == 2
    assert load_map[next_agent_id] == 2


def test_normalize_case_routing_policy_accepts_follow_up_sla_balance() -> None:
    assert console_router._normalize_case_routing_policy("follow_up_sla_balance") == "follow_up_sla_balance"


def test_normalize_case_routing_policy_rejects_unknown_value() -> None:
    with pytest.raises(ConsoleAPIError):
        console_router._normalize_case_routing_policy("skills_presence")


@pytest.mark.parametrize(
    ("assigned_to_me", "assignee_id", "unassigned"),
    [
        (True, str(uuid4()), False),
        (True, None, True),
        (False, str(uuid4()), True),
    ],
)
def test_parse_case_owner_filters_rejects_conflicts(
    assigned_to_me: bool,
    assignee_id: str | None,
    unassigned: bool,
):
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._parse_case_owner_filters(
            assigned_to_me=assigned_to_me,
            assignee_id=assignee_id,
            unassigned=unassigned,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_PARAM"


def test_normalize_search_query():
    assert console_router._normalize_search_query("q", None) is None
    assert console_router._normalize_search_query("q", "   ") is None
    assert console_router._normalize_search_query("q", "  Alice  ") == "Alice"


def test_normalize_search_query_rejects_invalid():
    with pytest.raises(ConsoleAPIError):
        console_router._normalize_search_query("q", "a" * 129)
    with pytest.raises(ConsoleAPIError):
        console_router._normalize_search_query("q", "bad\x00value")
    with pytest.raises(ConsoleAPIError):
        console_router._normalize_search_query("q", "line\nbreak")


def test_resolve_case_sort_cursor():
    created_at = datetime.now(timezone.utc)
    last_activity = created_at - timedelta(minutes=5)

    assert console_router._resolve_case_sort_cursor(
        sort_by="last_activity",
        last_activity_at=last_activity,
        created_at=created_at,
    ) == last_activity
    assert console_router._resolve_case_sort_cursor(
        sort_by="last_activity",
        last_activity_at=None,
        created_at=created_at,
    ) == created_at
    assert console_router._resolve_case_sort_cursor(
        sort_by="created_at",
        last_activity_at=last_activity,
        created_at=created_at,
    ) == created_at
    assert console_router._resolve_case_sort_cursor(
        sort_by="sla",
        last_activity_at=last_activity,
        created_at=created_at,
    ) == created_at
    resolved_at = created_at + timedelta(minutes=10)
    assert console_router._resolve_case_sort_cursor(
        sort_by="resolved_at",
        last_activity_at=last_activity,
        created_at=created_at,
        resolved_at=resolved_at,
    ) == resolved_at
    assert console_router._resolve_case_sort_cursor(
        sort_by="resolved_at",
        last_activity_at=last_activity,
        created_at=created_at,
        resolved_at=None,
    ) == created_at


def test_format_case_metrics():
    first_response_at = datetime.now(timezone.utc)
    resolved_at = first_response_at + timedelta(minutes=12)
    handover = SimpleNamespace(
        first_response_at=first_response_at,
        resolved_at=resolved_at,
        resolution_time_seconds=720,
    )

    metrics = console_router._format_case_metrics(handover)

    assert metrics["first_response_at"] == first_response_at.isoformat()
    assert metrics["resolved_at"] == resolved_at.isoformat()
    assert metrics["resolution_time_seconds"] == 720


def test_build_case_queue_signals_marks_reply_due_before_deadline():
    now = datetime(2026, 3, 6, 10, 0, tzinfo=timezone.utc)
    created_at = now - timedelta(minutes=45)

    signals = console_router._build_case_queue_signals(
        created_at=created_at,
        status="active",
        needs_reply=True,
        has_delivery_error=False,
        has_pending_outbox=False,
        human_lock_active=False,
        now_utc=now,
    )

    assert signals["sla_status"] == "warning"
    assert signals["sla_action_state"] == "reply_due"
    assert signals["sla_overdue_minutes"] is None
    assert signals["priority_tier"] == "high"
    assert signals["attention_reason"] == "Клиент ожидает ответ"
    assert signals["target_response_at"] == (created_at + timedelta(minutes=60)).isoformat()


def test_build_case_queue_signals_marks_overdue_after_deadline():
    now = datetime(2026, 3, 6, 10, 0, tzinfo=timezone.utc)
    created_at = now - timedelta(minutes=83)

    signals = console_router._build_case_queue_signals(
        created_at=created_at,
        status="active",
        needs_reply=True,
        has_delivery_error=False,
        has_pending_outbox=False,
        human_lock_active=False,
        now_utc=now,
    )

    assert signals["sla_status"] == "breached"
    assert signals["sla_action_state"] == "overdue"
    assert signals["sla_overdue_minutes"] == 23
    assert signals["priority_tier"] == "urgent"
    assert signals["attention_reason"] == "Клиент ожидает ответ"


def test_build_case_queue_signals_marks_waiting_client_when_manager_already_replied():
    now = datetime(2026, 3, 6, 10, 0, tzinfo=timezone.utc)
    created_at = now - timedelta(minutes=20)
    last_inbound_at = now - timedelta(minutes=18)
    last_outbound_at = now - timedelta(minutes=5)

    signals = console_router._build_case_queue_signals(
        created_at=created_at,
        status="active",
        needs_reply=False,
        has_delivery_error=False,
        has_pending_outbox=False,
        human_lock_active=False,
        last_inbound_at=last_inbound_at,
        last_outbound_at=last_outbound_at,
        first_response_at=last_outbound_at,
        now_utc=now,
    )

    assert signals["sla_status"] == "ok"
    assert signals["sla_action_state"] == "waiting_client"
    assert signals["sla_overdue_minutes"] is None
    assert signals["priority_tier"] == "normal"
    assert signals["attention_reason"] == "Ожидаем ответ клиента"


def test_build_case_queue_signals_prioritizes_delivery_issue():
    now = datetime(2026, 3, 6, 10, 0, tzinfo=timezone.utc)
    created_at = now - timedelta(minutes=5)

    signals = console_router._build_case_queue_signals(
        created_at=created_at,
        status="active",
        needs_reply=True,
        has_delivery_error=True,
        has_pending_outbox=False,
        human_lock_active=False,
        now_utc=now,
    )

    assert signals["sla_status"] == "ok"
    assert signals["sla_action_state"] == "delivery_issue"
    assert signals["priority_tier"] == "urgent"
    assert signals["attention_reason"] == "Ошибка доставки: проверьте отправку"


def test_resolve_case_snooze_state_marks_active_snooze_without_new_inbound():
    now = datetime(2026, 3, 6, 10, 0, tzinfo=timezone.utc)
    snoozed_until = now + timedelta(minutes=45)
    snoozed_at = now - timedelta(minutes=5)

    state = console_router._resolve_case_snooze_state(
        handover_meta={
            "snoozed_until": snoozed_until.isoformat(),
            "snoozed_at": snoozed_at.isoformat(),
            "snooze_reason": "follow_up_later",
            "snoozed_by_name": "Manager",
        },
        last_inbound_at=now - timedelta(minutes=10),
        now_utc=now,
    )

    assert state["active"] is True
    assert state["snoozed_until"] == snoozed_until.isoformat()
    assert state["snoozed_reason"] == "follow_up_later"
    assert state["snoozed_by"] == "Manager"


def test_resolve_case_snooze_state_clears_when_new_inbound_arrives():
    now = datetime(2026, 3, 6, 10, 0, tzinfo=timezone.utc)
    snoozed_until = now + timedelta(minutes=45)
    snoozed_at = now - timedelta(minutes=10)

    state = console_router._resolve_case_snooze_state(
        handover_meta={
            "snoozed_until": snoozed_until.isoformat(),
            "snoozed_at": snoozed_at.isoformat(),
            "snooze_reason": "follow_up_later",
            "snoozed_by_name": "Manager",
        },
        last_inbound_at=now - timedelta(minutes=2),
        now_utc=now,
    )

    assert state["active"] is False
    assert state["snoozed_until"] is None
    assert state["snoozed_reason"] is None
    assert state["snoozed_by"] is None


def test_build_case_queue_signals_marks_snoozed_before_reply_due():
    now = datetime(2026, 3, 6, 10, 0, tzinfo=timezone.utc)
    created_at = now - timedelta(minutes=20)
    snoozed_until = now + timedelta(minutes=40)

    signals = console_router._build_case_queue_signals(
        created_at=created_at,
        status="active",
        needs_reply=True,
        has_delivery_error=False,
        has_pending_outbox=False,
        human_lock_active=False,
        handover_meta={
            "snoozed_until": snoozed_until.isoformat(),
            "snoozed_at": (now - timedelta(minutes=1)).isoformat(),
            "snooze_reason": "follow_up_later",
            "snoozed_by_name": "Manager",
        },
        now_utc=now,
    )

    assert signals["sla_action_state"] == "snoozed"
    assert signals["priority_tier"] == "low"
    assert signals["attention_reason"] == "Диалог отложен менеджером"
    assert signals["snoozed_until"] == snoozed_until.isoformat()


def test_build_case_business_status_marks_unassigned_before_reply_due() -> None:
    business_status = console_router._build_case_business_status(
        status="pending",
        assigned_to_id=None,
        assigned_to_name=None,
        queue_signals={"sla_action_state": "reply_due"},
    )

    assert business_status["business_status_code"] == "unassigned"
    assert business_status["business_status_label"] == "Без владельца"


def test_build_case_business_status_marks_waiting_client() -> None:
    business_status = console_router._build_case_business_status(
        status="active",
        assigned_to_id=uuid4(),
        assigned_to_name="Manager",
        queue_signals={"sla_action_state": "waiting_client"},
    )

    assert business_status["business_status_code"] == "waiting_client"
    assert business_status["business_status_label"] == "Ждем клиента"


def test_build_case_business_status_marks_bot_handling() -> None:
    business_status = console_router._build_case_business_status(
        status="bot_handling",
        assigned_to_id=None,
        assigned_to_name=None,
        queue_signals={"sla_action_state": None},
    )

    assert business_status["business_status_code"] == "bot_handling"
    assert business_status["business_status_label"] == "Бот ведет"


def test_normalize_case_bulk_ids_dedupes_and_preserves_order():
    case_1 = uuid4()
    case_2 = uuid4()

    result = console_router._normalize_case_bulk_ids([case_1, case_2, case_1])

    assert result == [case_1, case_2]


def test_normalize_case_bulk_ids_rejects_empty():
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._normalize_case_bulk_ids([])
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_PARAM"


def test_normalize_case_bulk_ids_rejects_oversized_payload():
    case_ids = [uuid4() for _ in range(51)]

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._normalize_case_bulk_ids(case_ids)

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_PARAM"


def test_require_branch_access_allows_matching_branch():
    branch_id = uuid4()
    context = SimpleNamespace(
        role="manager",
        branches=[SimpleNamespace(id=branch_id)],
    )
    console_router._require_branch_access(context, branch_id, message="Access denied")


def test_require_branch_access_allows_admin():
    branch_id = uuid4()
    context = SimpleNamespace(
        role="platform_admin",
        branches=[],
    )
    console_router._require_branch_access(context, branch_id, message="Access denied")


def test_require_branch_access_denies_other_branch():
    branch_id = uuid4()
    context = SimpleNamespace(
        role="manager",
        branches=[SimpleNamespace(id=uuid4())],
    )
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._require_branch_access(context, branch_id, message="Access denied")
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


def test_require_branch_access_denies_branch_scoped_admin_outside_allowed_branch():
    branch_id = uuid4()
    context = SimpleNamespace(
        role="admin",
        branch_restricted=True,
        branches=[SimpleNamespace(id=uuid4())],
    )
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._require_branch_access(context, branch_id, message="Access denied")
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


def test_resolve_outreach_auto_case_bucket_minutes_bounds(monkeypatch):
    monkeypatch.delenv("OUTREACH_AUTO_CASE_BUCKET_MINUTES", raising=False)
    assert console_router._resolve_outreach_auto_case_bucket_minutes() == 30

    monkeypatch.setenv("OUTREACH_AUTO_CASE_BUCKET_MINUTES", "0")
    assert console_router._resolve_outreach_auto_case_bucket_minutes() == 1

    monkeypatch.setenv("OUTREACH_AUTO_CASE_BUCKET_MINUTES", "999")
    assert console_router._resolve_outreach_auto_case_bucket_minutes() == 240

    monkeypatch.setenv("OUTREACH_AUTO_CASE_BUCKET_MINUTES", "bad")
    assert console_router._resolve_outreach_auto_case_bucket_minutes() == 30


def test_build_outreach_auto_case_dedupe_key_is_deterministic():
    client_id = uuid4()
    branch_id = uuid4()
    now = datetime(2026, 2, 22, 12, 14, 55, tzinfo=timezone.utc)
    bucket_start = console_router._resolve_outreach_auto_case_bucket_start(
        now_utc=now,
        bucket_minutes=30,
    )
    key_1 = console_router._build_outreach_auto_case_dedupe_key(
        client_id=client_id,
        branch_id=branch_id,
        remote_jid="77771234567@s.whatsapp.net",
        bucket_started_at=bucket_start,
    )
    key_2 = console_router._build_outreach_auto_case_dedupe_key(
        client_id=client_id,
        branch_id=branch_id,
        remote_jid="77771234567@s.whatsapp.net",
        bucket_started_at=bucket_start,
    )
    assert key_1 == key_2
    assert key_1.startswith("outreach-no-case:")


def test_record_outreach_auto_case_trace_trims_to_limit():
    conversation = SimpleNamespace(
        context={
            "decision_trace": [
                {"stage": f"legacy_{idx}", "decision": "noop"}
                for idx in range(console_router._OUTREACH_AUTO_CASE_TRACE_MAX + 2)
            ]
        }
    )
    case_id = uuid4()

    console_router._record_outreach_auto_case_trace(
        conversation=conversation,
        case_id=case_id,
        decision="case_created",
        reason="new_case_created",
        dedupe_key="outreach-no-case:test",
        bucket_started_at=datetime.now(timezone.utc),
        bucket_minutes=30,
    )

    trace = conversation.context["decision_trace"]
    assert len(trace) == console_router._OUTREACH_AUTO_CASE_TRACE_MAX
    assert trace[-1]["stage"] == "outreach_auto_case_bootstrap"
    assert trace[-1]["case_id"] == str(case_id)


@pytest.mark.asyncio
async def test_reopen_case_skips_external_sync_side_effects(monkeypatch):
    branch_id = uuid4()
    agent_id = uuid4()
    case = SimpleNamespace(
        id=uuid4(),
        status="resolved",
        assigned_to=None,
        assigned_to_name=None,
        conversation_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        trigger_type="bot_request",
        first_response_at=None,
        resolved_at=None,
        resolution_time_seconds=None,
        meta=None,
    )
    conversation = SimpleNamespace(id=case.conversation_id, branch_id=branch_id)
    context = SimpleNamespace(
        agent=SimpleNamespace(id=agent_id, name="Agent"),
        role="manager",
        client=SimpleNamespace(id=uuid4()),
        branches=[SimpleNamespace(id=branch_id)],
    )
    db = Mock()
    audit_events: list[str] = []
    telegram_sync = Mock(side_effect=AssertionError("reopen must not edit telegram markup"))
    client_notify = Mock(side_effect=AssertionError("reopen must not notify client as new handoff"))

    def fake_reopen(*_args, **_kwargs):
        case.status = "active"
        case.assigned_to = agent_id
        case.assigned_to_name = "Agent"
        return SimpleNamespace(ok=True, error=None)

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "start_idempotency", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        console_router,
        "_resolve_case_action_context",
        lambda *_args, **_kwargs: (case, conversation),
    )
    monkeypatch.setattr(console_router, "state_manager_reopen", fake_reopen)
    monkeypatch.setattr(console_router, "_sync_telegram_after_take", telegram_sync)
    monkeypatch.setattr(console_router, "_notify_client_status", client_notify)
    monkeypatch.setattr(
        console_router,
        "record_audit_event",
        lambda *args, **kwargs: audit_events.append(kwargs["event_type"]),
    )

    response = await console_router.reopen_case(case.id, request=Mock(), db=db)

    assert response.success is True
    assert response.case.status == "active"
    assert response.sync is not None
    assert response.sync.telegram.status == "skipped"
    assert response.sync.telegram.detail == "reopen_internal_only"
    assert response.sync.telegram.operator_message is None
    assert response.sync.client_notify.status == "skipped"
    assert response.sync.client_notify.detail == "reopen_internal_only"
    assert response.sync.client_notify.operator_message is None
    telegram_sync.assert_not_called()
    client_notify.assert_not_called()
    assert "case_reopened" in audit_events
    assert "case_reopen_sync" in audit_events


@pytest.mark.asyncio
@pytest.mark.parametrize("policy", ["least_open_cases", "follow_up_sla_balance"])
async def test_reassign_case_policy_uses_server_routing(monkeypatch, policy):
    branch_id = uuid4()
    actor_id = uuid4()
    current_agent_id = uuid4()
    recommended_agent_id = uuid4()
    case = SimpleNamespace(
        id=uuid4(),
        status="active",
        assigned_to=current_agent_id,
        assigned_to_name="Manager",
        conversation_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        trigger_type="message",
        first_response_at=None,
        resolved_at=None,
        resolution_time_seconds=None,
        meta=None,
    )
    conversation = SimpleNamespace(id=case.conversation_id, branch_id=branch_id)
    context = SimpleNamespace(
        agent=SimpleNamespace(id=actor_id, name="Supervisor"),
        role="admin",
        client=SimpleNamespace(id=uuid4()),
        branches=[SimpleNamespace(id=branch_id)],
    )
    db = Mock()
    audit_events: list[str] = []
    options = [
        ConsoleCaseAssigneeOption(
            agent_id=current_agent_id,
            agent_name="Manager",
            role="manager",
            branch_id=branch_id,
            is_current=True,
            open_case_count=4,
        ),
        ConsoleCaseAssigneeOption(
            agent_id=recommended_agent_id,
            agent_name="Manager Two",
            role="manager",
            branch_id=branch_id,
            is_current=False,
            open_case_count=1,
        ),
    ]

    def fake_reassign(*_args, **kwargs):
        case.assigned_to = kwargs["manager_id"]
        case.assigned_to_name = kwargs["manager_name"]
        return SimpleNamespace(ok=True, error=None)

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "start_idempotency", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        console_router,
        "_resolve_case_action_context",
        lambda *_args, **_kwargs: (case, conversation),
    )
    monkeypatch.setattr(console_router, "_require_case_operator_access", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_list_case_assignee_options", lambda *args, **kwargs: options)
    monkeypatch.setattr(
        console_router,
        "_load_single_case_routing_signal_context",
        lambda *args, **kwargs: CaseRoutingSignalContext(),
    )
    monkeypatch.setattr(
        console_router,
        "_load_case_booking_routing_contexts",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(console_router, "state_manager_reassign", fake_reassign)
    monkeypatch.setattr(
        console_router,
        "record_audit_event",
        lambda *args, **kwargs: audit_events.append(kwargs["event_type"]),
    )

    response = await console_router.reassign_case(
        case.id,
        SimpleNamespace(agent_id=None, mode="policy", policy=policy),
        request=Mock(),
        db=db,
    )

    assert response.success is True
    assert response.case.assigned_to_id == str(recommended_agent_id)
    assert response.case.assigned_to_name == "Manager Two"
    assert response.routing is not None
    assert response.routing.policy == policy
    assert response.routing.recommended_agent_id == recommended_agent_id
    if policy == "least_open_cases":
        assert response.routing.reason_code == "least_open_cases"
    else:
        assert response.routing.reason_code == "follow_up_sla_balance"
    assert "case_routed_policy" in audit_events
