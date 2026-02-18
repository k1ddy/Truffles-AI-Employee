from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import calendar as calendar_router
from app.services.console_errors import ConsoleAPIError


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

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: booking)
    monkeypatch.setattr(
        calendar_router,
        "_build_booking_response",
        lambda _db, _booking: {
            "id": str(booking_id),
            "specialist_id": str(uuid4()),
            "specialist_name": "Spec",
            "start_at": "2026-02-18T10:00:00+00:00",
            "end_at": "2026-02-18T11:00:00+00:00",
            "customer_name": "Test",
            "customer_phone": "+77000000000",
            "service_type": "Маникюр",
            "status": "NO_SHOW",
            "google_event_id": None,
            "created_at": "2026-02-18T09:00:00+00:00",
        },
    )

    response = await calendar_router.register_booking_no_show_followup(
        request=SimpleNamespace(),
        booking_id=str(booking_id),
        data=calendar_router.BookingNoShowFollowUpRequest(note="Позвонить и предложить новый слот"),
        db=db,
    )

    assert response.success is True
    assert response.booking.status == "NO_SHOW"

    audit_row = db.add.call_args.args[0]
    assert audit_row.action == "no_show_followup"
    assert audit_row.prev_status == "NO_SHOW"
    assert audit_row.new_status == "NO_SHOW"
    assert audit_row.payload.get("action") == "contact_rebook"
    assert audit_row.payload.get("note") == "Позвонить и предложить новый слот"
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
