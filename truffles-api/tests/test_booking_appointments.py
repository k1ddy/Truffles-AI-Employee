from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.models.appointment import Appointment
from app.models.branch import Branch
from app.models.service import Service
from app.services import tool_registry_service

pytest.importorskip("dateparser")
from app.routers.webhook import _legacy as legacy
from app.routers.webhook import booking as booking_router


def _make_query(result):
    query = Mock()
    query.filter.return_value.first.return_value = result
    return query


def test_create_booking_appointment_collect_preferences(monkeypatch):
    monkeypatch.setenv("TZ", "Asia/Almaty")
    now = datetime(2026, 1, 30, 9, 0, tzinfo=timezone.utc)
    branch_id = uuid4()
    client_id = uuid4()
    conversation = SimpleNamespace(id=uuid4(), client_id=client_id, branch_id=branch_id)
    user = SimpleNamespace(
        id=uuid4(),
        phone="+77001234567",
        remote_jid="77001234567@s.whatsapp.net",
        name="Алия",
    )
    booking_state = {
        "service": "маникюр",
        "datetime": "2026-02-02 10:00",
        "name": "Алия",
    }
    branch = SimpleNamespace(
        id=branch_id,
        timezone="Asia/Almaty",
        booking_settings={
            "booking_mode": "collect_preferences",
            "availability_provider": "none",
            "default_duration_min": 45,
        },
    )
    service = SimpleNamespace(duration_min=30)

    db = Mock()
    appointment_query = _make_query(None)
    branch_query = _make_query(branch)
    service_query = _make_query(service)

    def _query(model):
        if model is Branch:
            return branch_query
        if model is Appointment:
            return appointment_query
        if model is Service:
            return service_query
        return Mock()

    db.query.side_effect = _query

    appointment = SimpleNamespace(
        id=uuid4(),
        status="PENDING_CONFIRMATION",
        client_id=client_id,
        branch_id=branch_id,
        start_at=now + timedelta(days=1),
        end_at=now + timedelta(days=1, hours=1),
    )
    with patch("app.routers.webhook.booking.SchedulingService") as scheduling_cls:
        scheduling_cls.return_value.create_appointment.return_value = appointment

        created, meta = booking_router._create_booking_appointment(
            db=db,
            conversation=conversation,
            user=user,
            booking_state=booking_state,
            now=now,
            saved_message=None,
        )

    assert created == appointment
    assert meta["appointment_id"] == str(appointment.id)
    assert meta["booking_mode"] == "collect_preferences"
    assert meta["effective_booking_mode"] == "collect_preferences"

    _, kwargs = scheduling_cls.return_value.create_appointment.call_args
    assert kwargs["status"] == "PENDING_CONFIRMATION"
    assert kwargs["source"] == "bot"
    assert kwargs["service_type"] == "маникюр"
    assert kwargs["specialist_id"] is None
    assert kwargs["commit"] is False


def test_parse_booking_datetime_handles_dateparser_timezone_conflict():
    now = datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc)

    with patch(
        "app.routers.webhook.booking.dateparser.parse",
        side_effect=Exception("Multiple conflicting time zone configurations found"),
    ):
        parsed = booking_router._parse_booking_datetime(
            "на выходных",
            tz_name="Asia/Almaty",
            now=now,
        )

    assert parsed is None


def test_create_booking_appointment_reuses_existing():
    now = datetime(2026, 1, 30, 9, 0, tzinfo=timezone.utc)
    branch_id = uuid4()
    client_id = uuid4()
    conversation = SimpleNamespace(id=uuid4(), client_id=client_id, branch_id=branch_id)
    user = SimpleNamespace(
        id=uuid4(),
        phone="+77001234567",
        remote_jid="77001234567@s.whatsapp.net",
        name="Алия",
    )
    booking_state = {
        "service": "маникюр",
        "datetime": "2026-02-02 10:00",
        "name": "Алия",
    }
    branch = SimpleNamespace(
        id=branch_id,
        timezone="Asia/Almaty",
        booking_settings={"booking_mode": "collect_preferences", "availability_provider": "none"},
    )
    existing = SimpleNamespace(id=uuid4(), status="CONFIRMED")

    db = Mock()
    appointment_query = _make_query(existing)
    branch_query = _make_query(branch)
    service_query = _make_query(None)

    def _query(model):
        if model is Branch:
            return branch_query
        if model is Appointment:
            return appointment_query
        if model is Service:
            return service_query
        return Mock()

    db.query.side_effect = _query

    with patch("app.routers.webhook.booking.SchedulingService") as scheduling_cls:
        created, meta = booking_router._create_booking_appointment(
            db=db,
            conversation=conversation,
            user=user,
            booking_state=booking_state,
            now=now,
            saved_message=None,
        )

    assert created == existing
    assert meta["appointment_id"] == str(existing.id)
    assert meta["appointment_reused"] is True
    assert meta["appointment_status"] == "CONFIRMED"
    scheduling_cls.assert_not_called()


def test_create_booking_appointment_missing_branch_skips():
    conversation = SimpleNamespace(id=uuid4(), client_id=uuid4(), branch_id=None)
    db = Mock()

    with patch("app.routers.webhook.booking.SchedulingService") as scheduling_cls:
        created, meta = booking_router._create_booking_appointment(
            db=db,
            conversation=conversation,
            user=None,
            booking_state={},
            now=datetime.now(timezone.utc),
            saved_message=None,
        )

    assert created is None
    assert meta["appointment_skip_reason"] == "missing_branch"
    scheduling_cls.assert_not_called()


def test_select_last_non_booking_message_ignores_booking_intake():
    messages = ["Здравствуйте! Я хочу записаться на стрижку."]

    selected = booking_router._select_last_non_booking_message(
        messages,
        client_slug="demo_salon",
    )

    assert selected is None


def test_select_booking_interrupt_text_prefers_current_info_message():
    selected = booking_router._select_booking_interrupt_text(
        message_text="Где находится ваш салон?",
        batch_non_booking_message="Сколько стоит маникюр?",
        client_slug="demo_salon",
    )

    assert selected == "Где находится ваш салон?"


def test_select_booking_interrupt_text_falls_back_for_booking_intake():
    selected = booking_router._select_booking_interrupt_text(
        message_text="Я хочу записаться на стрижку.",
        batch_non_booking_message="Сколько стоит маникюр?",
        client_slug="demo_salon",
    )

    assert selected == "Сколько стоит маникюр?"


def test_select_booking_interrupt_text_uses_batch_when_message_missing():
    selected = booking_router._select_booking_interrupt_text(
        message_text=None,
        batch_non_booking_message="Сколько стоит маникюр?",
        client_slug="demo_salon",
    )

    assert selected == "Сколько стоит маникюр?"


def test_resolve_booking_info_intents_prefers_info_class_over_intent_decomp():
    resolved = booking_router._resolve_booking_info_intents(
        intent_decomp_used=True,
        intent_decomp_set={"pricing", "duration"},
        info_class_intents={"location", "pricing"},
        expected_reply_type=legacy.EXPECTED_REPLY_TIME,
        booking_time_service_candidate=False,
        expected_reply_shortcircuit=False,
        booking_interrupt_text=None,
        client_slug="demo_salon",
    )

    assert resolved == ["location", "pricing"]


@pytest.mark.parametrize(
    "tool_action",
    ["calendar.get_booking", "calendar.reschedule", "calendar.cancel"],
)
def test_tool_registry_invalid_appointment_id_does_not_raise(tool_action):
    db = Mock()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "none"},
        timezone="Asia/Almaty",
    )

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service, "_get_booking", return_value=(None, "booking_not_found")
    ):
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action=tool_action,
            tool_args={"appointment_id": "15:30"},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query=None,
        )

    assert result.handled is True
    assert result.ok is False
    assert result.error_code == "booking_not_found"


def test_tool_registry_get_booking_reports_time_mismatch():
    db = Mock()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "none"},
        timezone="Asia/Almaty",
    )
    appointment = SimpleNamespace(
        id=uuid4(),
        start_at=datetime(2026, 2, 14, 9, 0, tzinfo=timezone.utc),
        specialist_id=None,
    )

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service, "_get_booking", return_value=(appointment, None)
    ), patch.object(
        tool_registry_service, "_format_booking_summary", return_value="dummy-summary"
    ):
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.get_booking",
            tool_args={"appointment_id": ""},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query=None,
            message_text="Можете подтвердить мою запись на 15:30?",
        )

    assert result.handled is True
    assert result.ok is False
    assert result.error_code == "booking_time_mismatch"
    assert result.decision_meta["tool_decision"] == "time_mismatch"
    assert result.decision_meta["requested_time"] == "15:30"
    assert result.decision_meta["appointment_time"] == "09:00"


def test_tool_registry_book_slot_allows_missing_specialist_when_not_explicit():
    db = Mock()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "google_calendar"},
        timezone="Asia/Almaty",
    )
    appointment = SimpleNamespace(id=uuid4(), specialist_id=None)

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service,
        "get_provider_health",
        return_value=SimpleNamespace(ready=True, reason=None),
    ), patch.object(
        tool_registry_service,
        "_resolve_specialist_for_booking",
        return_value=(None, None, "specialist_not_found"),
    ), patch.object(
        tool_registry_service,
        "_book_slot",
        return_value=(appointment, None),
    ) as book_slot_mock, patch.object(
        tool_registry_service, "enqueue_appointment_sync", return_value=None
    ), patch.object(
        tool_registry_service, "schedule_default_reminders", return_value=[]
    ):
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.book_slot",
            tool_args={"start_at": "2026-02-12T13:00:00", "service_query": "Маникюр"},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query="Маникюр",
            user_name="Лена",
            user_phone="+77011112233",
        )

    assert result.handled is True
    assert result.ok is True
    assert result.decision_meta.get("tool_decision") == "ok"
    assert result.decision_meta.get("appointment_id") == str(appointment.id)
    assert result.decision_meta.get("specialist_selection") == "none_available"
    _, kwargs = book_slot_mock.call_args
    assert kwargs["specialist_id"] is None
