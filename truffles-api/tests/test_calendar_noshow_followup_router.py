from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import calendar as calendar_router
from app.services.audit_service import AuditEvent
from app.services.console_errors import ConsoleAPIError


def _booking_response_payload(booking_id: str) -> dict:
    return {
        "id": booking_id,
        "specialist_id": str(uuid4()),
        "specialist_name": "Spec",
        "start_at": "2026-02-18T10:00:00+00:00",
        "end_at": "2026-02-18T11:00:00+00:00",
        "customer_name": "Test",
        "customer_phone": "+77000000000",
        "service_type": "Маникюр",
        "status": "NO_SHOW",
        "no_show_followup_done": True,
        "no_show_followup_result": "contacted",
        "no_show_followup_closed_at": "2026-02-18T12:00:00+00:00",
        "no_show_followup_closed_by": str(uuid4()),
        "no_show_followup_rebooked_appointment_id": None,
        "follow_up_owner_id": None,
        "follow_up_owner_name": None,
        "follow_up_due_at": None,
        "follow_up_overdue": False,
        "google_event_id": None,
        "created_at": "2026-02-18T09:00:00+00:00",
    }


def _added_rows(db, row_type):
    return [
        call.args[0]
        for call in getattr(db.add, "call_args_list", [])
        if call.args and isinstance(call.args[0], row_type)
    ]


@pytest.mark.asyncio
async def test_register_booking_no_show_followup_records_audit(monkeypatch):
    booking_id = uuid4()
    agent_id = uuid4()
    client_id = uuid4()
    booking = SimpleNamespace(
        id=booking_id,
        status="NO_SHOW",
        version=3,
    )
    context = SimpleNamespace(
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=agent_id, name="Manager"),
    )

    db = Mock()
    audit_query = Mock()
    audit_query.filter.return_value = audit_query
    audit_query.order_by.return_value = audit_query
    audit_query.first.return_value = None
    db.query.side_effect = lambda model: audit_query if model is calendar_router.AppointmentAudit else Mock()

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: booking)
    monkeypatch.setattr(
        calendar_router,
        "_build_booking_response_for_context",
        lambda **_kwargs: _booking_response_payload(str(booking_id)),
    )

    response = await calendar_router.register_booking_no_show_followup(
        request=SimpleNamespace(),
        booking_id=str(booking_id),
        data=calendar_router.BookingNoShowFollowUpRequest(note="Позвонить и предложить новый слот", version=3),
        db=db,
    )

    assert response.success is True
    assert response.booking.status == "NO_SHOW"
    assert response.booking.no_show_followup_done is True

    audit_rows = _added_rows(db, calendar_router.AppointmentAudit)
    assert len(audit_rows) == 1
    audit_row = audit_rows[0]
    assert audit_row.action == "no_show_followup"
    assert audit_row.prev_status == "NO_SHOW"
    assert audit_row.new_status == "NO_SHOW"
    assert audit_row.payload.get("action") == "contact_rebook"
    assert audit_row.payload.get("result") == "contacted"
    assert audit_row.payload.get("follow_up_closed_by") == str(agent_id)
    assert audit_row.payload.get("follow_up_closed_at")
    assert audit_row.payload.get("note") == "Позвонить и предложить новый слот"
    observation_rows = _added_rows(db, AuditEvent)
    assert any(row.event_type == "calendar_booking_action_applied" for row in observation_rows)
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_register_booking_no_show_followup_is_idempotent_when_already_closed(monkeypatch):
    booking_id = uuid4()
    booking = SimpleNamespace(id=booking_id, status="NO_SHOW", version=3)
    existing = SimpleNamespace(
        payload={
            "action": "contact_rebook",
            "source": "calendar_console",
            "result": "contacted",
            "follow_up_closed_at": "2026-02-18T12:00:00+00:00",
            "follow_up_closed_by": str(uuid4()),
        },
        created_at=datetime.now(timezone.utc),
        actor_id=uuid4(),
    )
    context = SimpleNamespace(
        client=SimpleNamespace(id=uuid4()),
        agent=SimpleNamespace(id=uuid4(), name="Manager"),
    )

    db = Mock()
    audit_query = Mock()
    audit_query.filter.return_value = audit_query
    audit_query.order_by.return_value = audit_query
    audit_query.first.return_value = existing
    db.query.side_effect = lambda model: audit_query if model is calendar_router.AppointmentAudit else Mock()

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: booking)
    monkeypatch.setattr(
        calendar_router,
        "_build_booking_response_for_context",
        lambda **_kwargs: _booking_response_payload(str(booking_id)),
    )

    response = await calendar_router.register_booking_no_show_followup(
        request=SimpleNamespace(),
        booking_id=str(booking_id),
        data=calendar_router.BookingNoShowFollowUpRequest(version=3),
        db=db,
    )

    assert response.success is True
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_booking_no_show_followup_rejects_stale_version(monkeypatch):
    booking_id = uuid4()
    context = SimpleNamespace(
        client=SimpleNamespace(id=uuid4()),
        agent=SimpleNamespace(id=uuid4(), name="Manager"),
    )
    booking = SimpleNamespace(id=booking_id, status="NO_SHOW", version=4)
    db = Mock()

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: booking)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.register_booking_no_show_followup(
            request=SimpleNamespace(),
            booking_id=str(booking_id),
            data=calendar_router.BookingNoShowFollowUpRequest(version=3),
            db=db,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "BOOKING_VERSION_CONFLICT"
    observation_rows = _added_rows(db, AuditEvent)
    assert len(observation_rows) == 1
    assert observation_rows[0].event_type == "calendar_booking_action_version_conflict"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_register_booking_no_show_followup_requires_rebook_link(monkeypatch):
    booking_id = uuid4()
    context = SimpleNamespace(
        client=SimpleNamespace(id=uuid4()),
        agent=SimpleNamespace(id=uuid4(), name="Manager"),
    )
    booking = SimpleNamespace(id=booking_id, status="NO_SHOW", version=1)
    db = Mock()
    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: booking)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.register_booking_no_show_followup(
            request=SimpleNamespace(),
            booking_id=str(booking_id),
            data=calendar_router.BookingNoShowFollowUpRequest(result="rebooked", version=1),
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_PARAM"
    observation_rows = _added_rows(db, AuditEvent)
    assert len(observation_rows) == 1
    assert observation_rows[0].event_type == "calendar_booking_action_invalid"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_register_booking_no_show_followup_rejects_rebook_link_for_contacted(monkeypatch):
    booking_id = uuid4()
    context = SimpleNamespace(
        client=SimpleNamespace(id=uuid4()),
        agent=SimpleNamespace(id=uuid4(), name="Manager"),
    )
    booking = SimpleNamespace(id=booking_id, status="NO_SHOW", version=1)
    db = Mock()

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: booking)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.register_booking_no_show_followup(
            request=SimpleNamespace(),
            booking_id=str(booking_id),
            data=calendar_router.BookingNoShowFollowUpRequest(
                result="contacted",
                rebooked_appointment_id=str(uuid4()),
                version=1,
            ),
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_PARAM"
    observation_rows = _added_rows(db, AuditEvent)
    assert len(observation_rows) == 1
    assert observation_rows[0].event_type == "calendar_booking_action_invalid"


@pytest.mark.asyncio
async def test_register_booking_no_show_followup_records_rebooked_link(monkeypatch):
    booking_id = uuid4()
    rebooked_id = uuid4()
    booking = SimpleNamespace(id=booking_id, status="NO_SHOW", version=3)
    context = SimpleNamespace(
        client=SimpleNamespace(id=uuid4()),
        agent=SimpleNamespace(id=uuid4(), name="Manager"),
    )

    db = Mock()
    audit_query = Mock()
    audit_query.filter.return_value = audit_query
    audit_query.order_by.return_value = audit_query
    audit_query.first.return_value = None

    rebook_query = Mock()
    rebook_query.filter.return_value = rebook_query
    rebook_query.first.return_value = SimpleNamespace(
        id=rebooked_id,
        client_id=context.client.id,
        version=2,
        case_id=None,
        conversation_id=None,
        branch_id=uuid4(),
    )

    def _query_side_effect(model):
        if model is calendar_router.AppointmentAudit:
            return audit_query
        if model is calendar_router.Appointment:
            return rebook_query
        return Mock()

    db.query.side_effect = _query_side_effect

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: booking)
    monkeypatch.setattr(
        calendar_router,
        "_build_booking_response_for_context",
        lambda **_kwargs: _booking_response_payload(str(booking_id)),
    )

    response = await calendar_router.register_booking_no_show_followup(
        request=SimpleNamespace(),
        booking_id=str(booking_id),
        data=calendar_router.BookingNoShowFollowUpRequest(
            result="rebooked",
            rebooked_appointment_id=str(rebooked_id),
            version=3,
        ),
        db=db,
    )

    assert response.success is True
    audit_rows = _added_rows(db, calendar_router.AppointmentAudit)
    assert len(audit_rows) == 1
    audit_row = audit_rows[0]
    assert audit_row.payload.get("result") == "rebooked"
    assert audit_row.payload.get("rebooked_appointment_id") == str(rebooked_id)
    observation_rows = _added_rows(db, AuditEvent)
    assert any(row.event_type == "calendar_booking_action_applied" for row in observation_rows)
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_register_booking_no_show_followup_rejects_non_no_show(monkeypatch):
    booking_id = uuid4()
    context = SimpleNamespace(
        client=SimpleNamespace(id=uuid4()),
        agent=SimpleNamespace(id=uuid4(), name="Manager"),
    )
    booking = SimpleNamespace(
        id=booking_id,
        status="CONFIRMED",
        version=1,
    )
    db = Mock()

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: booking)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.register_booking_no_show_followup(
            request=SimpleNamespace(),
            booking_id=str(booking_id),
            data=calendar_router.BookingNoShowFollowUpRequest(version=1),
            db=db,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "BOOKING_STATUS_REQUIRED"
    observation_rows = _added_rows(db, AuditEvent)
    assert len(observation_rows) == 1
    assert observation_rows[0].event_type == "calendar_booking_action_invalid"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_booking_status_reopens_resolved_linked_case_on_no_show(monkeypatch):
    booking_id = uuid4()
    case_id = uuid4()
    conversation_id = uuid4()
    client_id = uuid4()
    agent_id = uuid4()

    booking = SimpleNamespace(
        id=booking_id,
        client_id=client_id,
        case_id=case_id,
        status="NO_SHOW",
        follow_up_owner_id=None,
        follow_up_due_at=None,
    )
    handover = SimpleNamespace(
        id=case_id,
        client_id=client_id,
        conversation_id=conversation_id,
        status="resolved",
        meta={},
    )
    conversation = SimpleNamespace(
        id=conversation_id,
        branch_id=uuid4(),
        state="bot_active",
    )
    context = SimpleNamespace(
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=agent_id, name="Manager"),
    )

    case_query = Mock()
    case_query.filter.return_value = case_query
    case_query.with_for_update.return_value = case_query
    case_query.first.return_value = handover

    conversation_query = Mock()
    conversation_query.filter.return_value = conversation_query
    conversation_query.with_for_update.return_value = conversation_query
    conversation_query.first.return_value = conversation

    def _query_side_effect(model):
        if model is calendar_router.Handover:
            return case_query
        if model is calendar_router.Conversation:
            return conversation_query
        return Mock()

    db = Mock()
    db.query.side_effect = _query_side_effect

    class _SchedulingServiceStub:
        def __init__(self, _db):
            pass

        def update_appointment_status(self, **kwargs):
            assert kwargs["commit"] is False
            return booking

    def _reopen_stub(_db, _conversation, _handover, *, manager_id, manager_name):
        assert manager_id == str(agent_id)
        assert manager_name == "Manager"
        _handover.status = "active"
        return SimpleNamespace(ok=True, error=None)

    monkeypatch.setattr(calendar_router, "SchedulingService", _SchedulingServiceStub)
    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: booking)
    monkeypatch.setattr(calendar_router, "state_manager_reopen", _reopen_stub)
    monkeypatch.setattr(calendar_router, "record_audit_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        calendar_router,
        "_build_booking_response_for_context",
        lambda **_kwargs: {
            **_booking_response_payload(str(booking_id)),
            "status": "NO_SHOW",
            "case_id": str(case_id),
            "conversation_id": str(conversation_id),
        },
    )

    response = await calendar_router.update_booking_status(
        request=SimpleNamespace(),
        booking_id=str(booking_id),
        data=calendar_router.BookingStatusUpdateRequest(status="NO_SHOW", version=2),
        db=db,
    )

    assert response.success is True
    assert response.case_effects[0].action == "reopened_for_booking_attention"
    assert response.case_effects[0].case_id == str(case_id)
    assert handover.status == "active"
    assert booking.follow_up_owner_id == agent_id
    assert booking.follow_up_due_at is not None
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(booking)


@pytest.mark.asyncio
async def test_update_booking_status_sets_follow_up_defaults_on_no_show_without_case(monkeypatch):
    booking_id = uuid4()
    agent_id = uuid4()
    context = SimpleNamespace(
        client=SimpleNamespace(id=uuid4()),
        agent=SimpleNamespace(id=agent_id, name="Manager"),
    )
    booking = SimpleNamespace(
        id=booking_id,
        status="NO_SHOW",
        case_id=None,
        conversation_id=None,
        follow_up_owner_id=None,
        follow_up_due_at=None,
    )
    db = Mock()

    class _SchedulingServiceStub:
        def __init__(self, _db):
            pass

        def update_appointment_status(self, **kwargs):
            assert kwargs["commit"] is False
            return booking

    monkeypatch.setattr(calendar_router, "SchedulingService", _SchedulingServiceStub)
    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: booking)
    monkeypatch.setattr(calendar_router, "record_audit_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        calendar_router,
        "_build_booking_response_for_context",
        lambda **_kwargs: _booking_response_payload(str(booking_id)),
    )

    response = await calendar_router.update_booking_status(
        request=SimpleNamespace(),
        booking_id=str(booking_id),
        data=calendar_router.BookingStatusUpdateRequest(status="NO_SHOW", version=1),
        db=db,
    )

    assert response.success is True
    assert response.case_effects == []
    assert booking.follow_up_owner_id == agent_id
    assert booking.follow_up_due_at is not None
    assert booking.follow_up_due_at > datetime.now(timezone.utc)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(booking)


@pytest.mark.asyncio
async def test_register_booking_no_show_followup_links_rebooked_booking_to_same_case(monkeypatch):
    booking_id = uuid4()
    rebooked_id = uuid4()
    case_id = uuid4()
    conversation_id = uuid4()
    client_id = uuid4()
    context = SimpleNamespace(
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=uuid4(), name="Manager"),
    )
    booking = SimpleNamespace(
        id=booking_id,
        status="NO_SHOW",
        version=1,
        case_id=case_id,
        conversation_id=conversation_id,
    )
    rebooked = SimpleNamespace(
        id=rebooked_id,
        client_id=client_id,
        version=2,
        status="CONFIRMED",
        case_id=None,
        conversation_id=None,
        branch_id=uuid4(),
    )
    db = Mock()
    audit_query = Mock()
    audit_query.filter.return_value = audit_query
    audit_query.order_by.return_value = audit_query
    audit_query.first.return_value = None

    rebook_query = Mock()
    rebook_query.filter.return_value = rebook_query
    rebook_query.first.return_value = rebooked

    def _query_side_effect(model):
        if model is calendar_router.AppointmentAudit:
            return audit_query
        if model is calendar_router.Appointment:
            return rebook_query
        return Mock()

    db.query.side_effect = _query_side_effect

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: booking)
    monkeypatch.setattr(calendar_router, "record_audit_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        calendar_router,
        "_build_booking_response_for_context",
        lambda **_kwargs: {
            **_booking_response_payload(str(booking_id)),
            "case_id": str(case_id),
            "conversation_id": str(conversation_id),
        },
    )

    response = await calendar_router.register_booking_no_show_followup(
        request=SimpleNamespace(),
        booking_id=str(booking_id),
        data=calendar_router.BookingNoShowFollowUpRequest(
            result="rebooked",
            rebooked_appointment_id=str(rebooked_id),
            version=1,
        ),
        db=db,
    )

    assert response.success is True
    assert response.case_effects[0].action == "linked_rebooked_booking"
    assert rebooked.case_id == case_id
    assert rebooked.conversation_id == conversation_id
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_register_booking_no_show_followup_rejects_rebooked_booking_case_conflict(monkeypatch):
    booking_id = uuid4()
    rebooked_id = uuid4()
    client_id = uuid4()
    context = SimpleNamespace(
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=uuid4(), name="Manager"),
    )
    booking = SimpleNamespace(
        id=booking_id,
        status="NO_SHOW",
        version=1,
        case_id=uuid4(),
        conversation_id=uuid4(),
    )
    rebooked = SimpleNamespace(
        id=rebooked_id,
        client_id=client_id,
        version=2,
        case_id=uuid4(),
        conversation_id=booking.conversation_id,
        branch_id=uuid4(),
    )
    db = Mock()
    audit_query = Mock()
    audit_query.filter.return_value = audit_query
    audit_query.order_by.return_value = audit_query
    audit_query.first.return_value = None

    rebook_query = Mock()
    rebook_query.filter.return_value = rebook_query
    rebook_query.first.return_value = rebooked

    def _query_side_effect(model):
        if model is calendar_router.AppointmentAudit:
            return audit_query
        if model is calendar_router.Appointment:
            return rebook_query
        return Mock()

    db.query.side_effect = _query_side_effect

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: booking)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.register_booking_no_show_followup(
            request=SimpleNamespace(),
            booking_id=str(booking_id),
            data=calendar_router.BookingNoShowFollowUpRequest(
                result="rebooked",
                rebooked_appointment_id=str(rebooked_id),
                version=1,
            ),
            db=db,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "REBOOKED_BOOKING_CASE_CONFLICT"


@pytest.mark.asyncio
async def test_update_booking_follow_up_governance_updates_owner_and_due(monkeypatch):
    booking_id = uuid4()
    owner_agent_id = uuid4()
    due_at = datetime.now(timezone.utc) - timedelta(days=29)
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(id=uuid4()),
        agent=SimpleNamespace(id=uuid4(), name="Owner"),
        allowed_branch_ids={uuid4()},
    )
    booking = SimpleNamespace(
        id=booking_id,
        status="NO_SHOW",
        version=2,
        follow_up_owner_id=None,
        follow_up_due_at=None,
    )

    audit_query = Mock()
    audit_query.filter.return_value = audit_query
    audit_query.order_by.return_value = audit_query
    audit_query.first.return_value = None

    db = Mock()
    db.query.side_effect = lambda model: audit_query if model is calendar_router.AppointmentAudit else Mock()

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: booking)
    monkeypatch.setattr(
        calendar_router,
        "_resolve_follow_up_owner_agent",
        lambda **kwargs: SimpleNamespace(id=owner_agent_id),
    )
    monkeypatch.setattr(
        calendar_router,
        "_build_booking_response_for_context",
        lambda **kwargs: {
            **_booking_response_payload(str(booking_id)),
            "follow_up_owner_id": str(kwargs["booking"].follow_up_owner_id) if kwargs["booking"].follow_up_owner_id else None,
            "follow_up_due_at": kwargs["booking"].follow_up_due_at.isoformat() if kwargs["booking"].follow_up_due_at else None,
        },
    )

    response = await calendar_router.update_booking_follow_up_governance(
        request=SimpleNamespace(),
        booking_id=str(booking_id),
        data=calendar_router.BookingFollowUpGovernanceRequest(
            owner_agent_id=str(owner_agent_id),
            due_at=due_at,
            version=2,
        ),
        db=db,
    )

    assert response.success is True
    assert booking.follow_up_owner_id == owner_agent_id
    assert booking.follow_up_due_at == due_at
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(booking)


@pytest.mark.asyncio
async def test_update_booking_follow_up_governance_rejects_stale_version(monkeypatch):
    booking_id = uuid4()
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(id=uuid4()),
        agent=SimpleNamespace(id=uuid4(), name="Owner"),
        allowed_branch_ids={uuid4()},
    )
    booking = SimpleNamespace(
        id=booking_id,
        status="NO_SHOW",
        version=5,
        follow_up_owner_id=None,
        follow_up_due_at=None,
    )
    db = Mock()

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: booking)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.update_booking_follow_up_governance(
            request=SimpleNamespace(),
            booking_id=str(booking_id),
            data=calendar_router.BookingFollowUpGovernanceRequest(owner_agent_id=str(uuid4()), version=4),
            db=db,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "BOOKING_VERSION_CONFLICT"
    observation_rows = _added_rows(db, AuditEvent)
    assert len(observation_rows) == 1
    assert observation_rows[0].event_type == "calendar_booking_action_version_conflict"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_booking_follow_up_governance_rejects_non_privileged_role(monkeypatch):
    booking_id = uuid4()
    context = SimpleNamespace(
        role="manager",
        client=SimpleNamespace(id=uuid4()),
        agent=SimpleNamespace(id=uuid4(), name="Manager"),
        allowed_branch_ids={uuid4()},
    )
    booking = SimpleNamespace(
        id=booking_id,
        status="NO_SHOW",
        version=1,
        follow_up_owner_id=None,
        follow_up_due_at=None,
    )
    db = Mock()

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: booking)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.update_booking_follow_up_governance(
            request=SimpleNamespace(),
            booking_id=str(booking_id),
            data=calendar_router.BookingFollowUpGovernanceRequest(owner_agent_id=str(uuid4()), version=1),
            db=db,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_update_booking_follow_up_governance_rejects_closed_follow_up(monkeypatch):
    booking_id = uuid4()
    context = SimpleNamespace(
        role="owner",
        client=SimpleNamespace(id=uuid4()),
        agent=SimpleNamespace(id=uuid4(), name="Owner"),
        allowed_branch_ids={uuid4()},
    )
    booking = SimpleNamespace(
        id=booking_id,
        status="NO_SHOW",
        version=1,
        follow_up_owner_id=None,
        follow_up_due_at=None,
    )
    existing = SimpleNamespace(
        payload={
            "result": "contacted",
            "follow_up_closed_at": "2026-02-18T12:00:00+00:00",
            "follow_up_closed_by": str(uuid4()),
        },
        created_at=datetime.now(timezone.utc),
        actor_id=uuid4(),
    )

    audit_query = Mock()
    audit_query.filter.return_value = audit_query
    audit_query.order_by.return_value = audit_query
    audit_query.first.return_value = existing

    db = Mock()
    db.query.side_effect = lambda model: audit_query if model is calendar_router.AppointmentAudit else Mock()

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: booking)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.update_booking_follow_up_governance(
            request=SimpleNamespace(),
            booking_id=str(booking_id),
            data=calendar_router.BookingFollowUpGovernanceRequest(due_at=datetime.now(timezone.utc), version=1),
            db=db,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "FOLLOW_UP_ALREADY_CLOSED"
