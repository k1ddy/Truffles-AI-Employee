from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import calendar as calendar_router
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
        "google_event_id": None,
        "created_at": "2026-02-18T09:00:00+00:00",
    }


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
        "_build_booking_response",
        lambda _db, _booking: _booking_response_payload(str(booking_id)),
    )

    response = await calendar_router.register_booking_no_show_followup(
        request=SimpleNamespace(),
        booking_id=str(booking_id),
        data=calendar_router.BookingNoShowFollowUpRequest(note="Позвонить и предложить новый слот"),
        db=db,
    )

    assert response.success is True
    assert response.booking.status == "NO_SHOW"
    assert response.booking.no_show_followup_done is True

    audit_row = db.add.call_args.args[0]
    assert audit_row.action == "no_show_followup"
    assert audit_row.prev_status == "NO_SHOW"
    assert audit_row.new_status == "NO_SHOW"
    assert audit_row.payload.get("action") == "contact_rebook"
    assert audit_row.payload.get("result") == "contacted"
    assert audit_row.payload.get("follow_up_closed_by") == str(agent_id)
    assert audit_row.payload.get("follow_up_closed_at")
    assert audit_row.payload.get("note") == "Позвонить и предложить новый слот"
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
        "_build_booking_response",
        lambda _db, _booking: _booking_response_payload(str(booking_id)),
    )

    response = await calendar_router.register_booking_no_show_followup(
        request=SimpleNamespace(),
        booking_id=str(booking_id),
        data=calendar_router.BookingNoShowFollowUpRequest(),
        db=db,
    )

    assert response.success is True
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_booking_no_show_followup_allows_rebooked_without_link(monkeypatch):
    booking_id = uuid4()
    context = SimpleNamespace(
        client=SimpleNamespace(id=uuid4()),
        agent=SimpleNamespace(id=uuid4(), name="Manager"),
    )
    booking = SimpleNamespace(id=booking_id, status="NO_SHOW", version=1)
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
        "_build_booking_response",
        lambda _db, _booking: _booking_response_payload(str(booking_id)),
    )

    response = await calendar_router.register_booking_no_show_followup(
        request=SimpleNamespace(),
        booking_id=str(booking_id),
        data=calendar_router.BookingNoShowFollowUpRequest(result="rebooked"),
        db=db,
    )

    assert response.success is True
    audit_row = db.add.call_args.args[0]
    assert audit_row.payload.get("result") == "rebooked"
    assert audit_row.payload.get("rebooked_appointment_id") is None
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
            ),
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_PARAM"
    db.add.assert_not_called()


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
    rebook_query.first.return_value = SimpleNamespace(id=rebooked_id, client_id=context.client.id)

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
        "_build_booking_response",
        lambda _db, _booking: _booking_response_payload(str(booking_id)),
    )

    response = await calendar_router.register_booking_no_show_followup(
        request=SimpleNamespace(),
        booking_id=str(booking_id),
        data=calendar_router.BookingNoShowFollowUpRequest(
            result="rebooked",
            rebooked_appointment_id=str(rebooked_id),
        ),
        db=db,
    )

    assert response.success is True
    audit_row = db.add.call_args.args[0]
    assert audit_row.payload.get("result") == "rebooked"
    assert audit_row.payload.get("rebooked_appointment_id") == str(rebooked_id)
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
            data=calendar_router.BookingNoShowFollowUpRequest(),
            db=db,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "BOOKING_STATUS_REQUIRED"
    db.add.assert_not_called()
    db.commit.assert_not_called()
