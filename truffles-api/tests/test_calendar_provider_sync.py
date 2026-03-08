from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from app.models.appointment import Appointment
from app.models.appointment_sync_state import AppointmentSyncState
from app.models.branch import Branch
from app.models.calendar_block import CalendarBlock
from app.models.calendar_connection import CalendarConnection
from app.models.calendar_sync_cursor import CalendarSyncCursor
from app.models.google_calendar_token import GoogleCalendarToken
from app.services import calendar_sync_service


def _make_query(first=None, all_rows=None):
    query = Mock()
    query.filter.return_value.first.return_value = first
    query.filter.return_value.all.return_value = all_rows if all_rows is not None else []
    return query


def test_get_provider_health_sync_stale(monkeypatch):
    now = datetime(2026, 2, 3, 9, 0, tzinfo=timezone.utc)
    connection = SimpleNamespace(id=uuid4())
    token = Mock()
    token.is_expired.return_value = False
    cursor = SimpleNamespace(last_synced_at=now - timedelta(minutes=5))

    db = Mock()
    token_query = _make_query(first=token)
    cursor_query = _make_query(first=cursor)

    def _query(model):
        if model is GoogleCalendarToken:
            return token_query
        if model is CalendarSyncCursor:
            return cursor_query
        return Mock()

    db.query.side_effect = _query
    monkeypatch.setenv("CALENDAR_SYNC_STALE_SECONDS", "60")

    with patch(
        "app.services.calendar_sync_service.get_calendar_connection",
        return_value=connection,
    ), patch(
        "app.services.calendar_sync_service._now",
        return_value=now,
    ):
        health = calendar_sync_service.get_provider_health(
            db,
            client_id=uuid4(),
            branch_id=uuid4(),
        )

    assert health.ready is False
    assert health.reason == "sync_stale"
    assert health.connection_id == connection.id


def test_process_outbound_sync_event_create_updates_state():
    appointment_id = uuid4()
    appointment = SimpleNamespace(
        id=appointment_id,
        client_id=uuid4(),
        branch_id=uuid4(),
        conversation_id=None,
        specialist_id=None,
        start_at=datetime(2026, 2, 10, 10, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 2, 10, 11, 0, tzinfo=timezone.utc),
        customer_name="Test",
        customer_phone="+77001234567",
        notes=None,
        version=1,
    )
    sync_state = SimpleNamespace(
        appointment_id=appointment_id,
        provider="google_calendar",
        state="PENDING",
        external_id=None,
        external_etag=None,
        last_error=None,
        last_synced_at=None,
        updated_at=None,
    )
    connection = SimpleNamespace(id=uuid4(), calendar_id="primary")

    db = Mock()
    appointment_query = _make_query(first=appointment)
    db.query.side_effect = lambda model: appointment_query if model is Appointment else Mock()

    google = Mock()
    google.available = True
    google.create_event.return_value = {"id": "evt-1", "etag": "etag-1"}

    payload = {
        "provider": "google_calendar",
        "payload": {
            "appointment_id": str(appointment_id),
            "action": "create",
            "calendar_id": "primary",
        },
    }

    with patch(
        "app.services.calendar_sync_service.get_calendar_connection",
        return_value=connection,
    ), patch(
        "app.services.calendar_sync_service.GoogleCalendarService",
        return_value=google,
    ), patch(
        "app.services.calendar_sync_service._get_or_create_sync_state",
        return_value=sync_state,
    ), patch(
        "app.services.calendar_sync_service._resolve_service_name",
        return_value=None,
    ), patch(
        "app.services.calendar_sync_service._resolve_specialist_name",
        return_value=None,
    ):
        ok, error = calendar_sync_service.process_outbound_sync_event(
            db=db,
            payload_json=payload,
        )

    assert ok is True
    assert error is None
    assert sync_state.state == calendar_sync_service.SYNC_STATE_OK
    assert sync_state.external_id == "evt-1"
    db.commit.assert_called()


def test_process_inbound_sync_event_creates_block():
    now = datetime(2026, 2, 3, 12, 0, tzinfo=timezone.utc)
    branch_id = uuid4()
    branch = SimpleNamespace(id=branch_id, client_id=uuid4())
    connection = SimpleNamespace(id=uuid4(), calendar_id="primary")
    cursor = SimpleNamespace(cursor=None, last_synced_at=None, updated_at=None)

    event = {
        "id": "evt-42",
        "status": "confirmed",
        "summary": "Busy",
        "start": {"dateTime": now.isoformat()},
        "end": {"dateTime": (now + timedelta(hours=1)).isoformat()},
    }

    db = Mock()
    branch_query = _make_query(first=branch)
    sync_query = _make_query(all_rows=[])
    block_query = _make_query(first=None)

    def _query(model):
        if model is Branch:
            return branch_query
        if model is AppointmentSyncState:
            return sync_query
        if model is CalendarBlock:
            return block_query
        return Mock()

    db.query.side_effect = _query

    google = Mock()
    google.available = True
    google.list_events.return_value = ([event], "cursor-1", None)

    with patch(
        "app.services.calendar_sync_service.get_calendar_connection",
        return_value=connection,
    ), patch(
        "app.services.calendar_sync_service._get_or_create_cursor",
        return_value=cursor,
    ), patch(
        "app.services.calendar_sync_service._update_block_from_event",
        return_value=SimpleNamespace(),
    ) as update_block, patch(
        "app.services.calendar_sync_service.GoogleCalendarService",
        return_value=google,
    ):
        ok, error = calendar_sync_service.process_inbound_sync_event(
            db=db,
            payload_json={"provider": "google_calendar", "payload": {"branch_id": str(branch_id)}},
        )

    assert ok is True
    assert error is None
    assert cursor.cursor == "cursor-1"
    update_block.assert_called()


def test_process_inbound_sync_event_conflict_sets_reschedule():
    now = datetime(2026, 2, 3, 12, 0, tzinfo=timezone.utc)
    branch_id = uuid4()
    branch = SimpleNamespace(id=branch_id, client_id=uuid4())
    connection = SimpleNamespace(id=uuid4(), calendar_id="primary")
    cursor = SimpleNamespace(cursor=None, last_synced_at=None, updated_at=None)

    appointment_id = uuid4()
    appointment = SimpleNamespace(
        id=appointment_id,
        status="CONFIRMED",
        start_at=now,
        end_at=now + timedelta(hours=1),
        conversation_id=None,
        version=1,
    )
    sync_state = SimpleNamespace(
        appointment_id=appointment_id,
        provider="google_calendar",
        state="OK",
        external_id="evt-99",
        last_error=None,
        updated_at=None,
    )

    event = {
        "id": "evt-99",
        "status": "cancelled",
        "start": {"dateTime": now.isoformat()},
        "end": {"dateTime": (now + timedelta(hours=1)).isoformat()},
    }

    db = Mock()
    branch_query = _make_query(first=branch)
    sync_query = _make_query(all_rows=[sync_state])
    appointment_query = _make_query(first=appointment)
    block_query = _make_query(first=None)

    def _query(model):
        if model is Branch:
            return branch_query
        if model is AppointmentSyncState:
            return sync_query
        if model is Appointment:
            return appointment_query
        if model is CalendarBlock:
            return block_query
        return Mock()

    db.query.side_effect = _query

    google = Mock()
    google.available = True
    google.list_events.return_value = ([event], "cursor-2", None)

    def _fake_conflict(db, appointment, reason, trace_id=None):
        appointment.status = "RESCHEDULE_REQUESTED"

    with patch(
        "app.services.calendar_sync_service.get_calendar_connection",
        return_value=connection,
    ), patch(
        "app.services.calendar_sync_service._get_or_create_cursor",
        return_value=cursor,
    ), patch(
        "app.services.calendar_sync_service._update_block_from_event",
        return_value=SimpleNamespace(),
    ), patch(
        "app.services.calendar_sync_service._apply_external_conflict",
        side_effect=_fake_conflict,
    ), patch(
        "app.services.calendar_sync_service.GoogleCalendarService",
        return_value=google,
    ):
        ok, error = calendar_sync_service.process_inbound_sync_event(
            db=db,
            payload_json={"provider": "google_calendar", "payload": {"branch_id": str(branch_id)}},
        )

    assert ok is True
    assert error is None
    assert appointment.status == "RESCHEDULE_REQUESTED"
    assert sync_state.state == calendar_sync_service.SYNC_STATE_CONFLICT


def test_schedule_inbound_syncs_enqueues_when_stale(monkeypatch):
    now = datetime(2026, 2, 3, 12, 0, tzinfo=timezone.utc)
    connection = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        branch_id=uuid4(),
        provider="google_calendar",
        status="ACTIVE",
        calendar_id="primary",
    )
    branch = SimpleNamespace(
        id=connection.branch_id,
        is_active=True,
        booking_settings={"availability_provider": "google_calendar"},
    )
    token = Mock()
    token.is_expired.return_value = False
    cursor = SimpleNamespace(last_synced_at=now - timedelta(minutes=30))

    db = Mock()
    conn_query = _make_query(all_rows=[connection])
    branch_query = _make_query(first=branch)
    token_query = _make_query(first=token)
    cursor_query = _make_query(first=cursor)

    def _query(model):
        if model is CalendarConnection:
            return conn_query
        if model is Branch:
            return branch_query
        if model is GoogleCalendarToken:
            return token_query
        if model is CalendarSyncCursor:
            return cursor_query
        return Mock()

    db.query.side_effect = _query
    monkeypatch.setenv("CALENDAR_SYNC_INBOUND_ENABLED", "1")
    monkeypatch.setenv("CALENDAR_SYNC_STALE_SECONDS", "600")
    monkeypatch.setenv("CALENDAR_SYNC_INBOUND_INTERVAL_SECONDS", "300")

    with patch(
        "app.services.calendar_sync_service.enqueue_inbound_sync",
        return_value=(True, None),
    ) as enqueue:
        results = calendar_sync_service.schedule_inbound_syncs(db, now=now)

    assert results["scheduled"] == 1
    assert results["errors"] == 0
    enqueue.assert_called_once()


def test_enqueue_appointment_sync_uses_contract_valid_tenant_source():
    appointment = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        branch_id=uuid4(),
        conversation_id=uuid4(),
        version=3,
    )
    connection = SimpleNamespace(id=uuid4(), calendar_id="primary")
    sync_state = SimpleNamespace(state=None, last_error=None, updated_at=None)
    client = SimpleNamespace(name="demo_salon")

    db = Mock()
    client_query = _make_query(first=client)
    db.query.side_effect = lambda model: client_query if model.__name__ == "Client" else Mock()

    with patch(
        "app.services.calendar_sync_service.get_calendar_connection",
        return_value=connection,
    ), patch(
        "app.services.calendar_sync_service._get_or_create_sync_state",
        return_value=sync_state,
    ), patch(
        "app.services.calendar_sync_service.enqueue_outbox_message",
        return_value=True,
    ) as enqueue:
        ok, error = calendar_sync_service.enqueue_appointment_sync(
            db,
            appointment=appointment,
            action="create",
            commit=False,
        )

    assert ok is True
    assert error is None
    payload_json = enqueue.call_args.kwargs["payload_json"]
    assert payload_json["tenant_context"]["source"] == "system"
    assert payload_json["tenant_context"]["producer"] == "calendar_sync"


def test_enqueue_inbound_sync_uses_contract_valid_tenant_source():
    client_id = uuid4()
    branch_id = uuid4()
    connection = SimpleNamespace(id=uuid4(), calendar_id="primary")

    db = Mock()

    with patch(
        "app.services.calendar_sync_service.get_calendar_connection",
        return_value=connection,
    ), patch(
        "app.services.calendar_sync_service.enqueue_outbox_message",
        return_value=True,
    ) as enqueue:
        ok, error = calendar_sync_service.enqueue_inbound_sync(
            db,
            client_id=client_id,
            branch_id=branch_id,
            commit=False,
        )

    assert ok is True
    assert error is None
    payload_json = enqueue.call_args.kwargs["payload_json"]
    assert payload_json["tenant_context"]["source"] == "system"
    assert payload_json["tenant_context"]["producer"] == "calendar_sync"
