from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.models.appointment import Appointment
from app.models.branch import Branch
from app.models.service import Service

pytest.importorskip("dateparser")
from app.routers.webhook import booking as booking_router
from app.routers.webhook import _legacy as legacy


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
