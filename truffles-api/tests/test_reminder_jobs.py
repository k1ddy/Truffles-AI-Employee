from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from app.models.appointment import Appointment
from app.models.client_settings import ClientSettings
from app.models.reminder_job import ReminderJob
from app.services.appointment_reminder_service import (
    process_reminder_jobs,
    schedule_default_reminders,
)


def _make_query(first=None):
    query = Mock()
    query.filter.return_value.first.return_value = first
    return query


def test_schedule_default_reminders_respects_consent():
    appointment = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        branch_id=uuid4(),
        start_at=datetime.now(timezone.utc) + timedelta(days=2),
        end_at=datetime.now(timezone.utc) + timedelta(days=2, hours=1),
    )
    settings = SimpleNamespace(enable_reminders=False, learning_consent_status="denied")

    db = Mock()
    settings_query = _make_query(first=settings)
    db.query.side_effect = lambda model: settings_query if model is ClientSettings else Mock()

    jobs = schedule_default_reminders(db, appointment=appointment, commit=False)

    assert jobs == []
    db.add.assert_not_called()


def test_schedule_default_reminders_creates_jobs():
    now = datetime.now(timezone.utc)
    appointment = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        branch_id=uuid4(),
        start_at=now + timedelta(days=3),
        end_at=now + timedelta(days=3, hours=1),
    )
    settings = SimpleNamespace(enable_reminders=True, learning_consent_status=None)

    db = Mock()
    settings_query = _make_query(first=settings)
    db.query.side_effect = lambda model: settings_query if model is ClientSettings else Mock()

    jobs = schedule_default_reminders(db, appointment=appointment, commit=False)

    assert len(jobs) == 3
    assert any(job.template == "post_visit_followup" for job in jobs)
    assert db.add.call_count == len(jobs)
    db.flush.assert_called_once()


def test_process_reminder_jobs_enqueues_outbox():
    appointment_id = uuid4()
    now = datetime.now(timezone.utc)
    job = SimpleNamespace(
        appointment_id=appointment_id,
        client_id=uuid4(),
        branch_id=uuid4(),
        channel="whatsapp",
        template="appointment_reminder",
        run_at=now - timedelta(minutes=5),
        status="PENDING",
        next_attempt_at=None,
        dedupe_key="job-1",
        last_error=None,
    )
    appointment = SimpleNamespace(
        id=appointment_id,
        client_id=job.client_id,
        branch_id=job.branch_id,
        conversation_id=uuid4(),
        customer_phone="+77001234567",
        start_at=now + timedelta(days=1),
        end_at=now + timedelta(days=1, hours=1),
        user_id=None,
        branch=SimpleNamespace(instance_id="demo-instance"),
    )
    settings = SimpleNamespace(enable_reminders=True, learning_consent_status=None)

    db = Mock()
    reminder_query = Mock()
    reminder_query.filter.return_value.order_by.return_value.all.return_value = [job]
    appointment_query = _make_query(first=appointment)
    settings_query = _make_query(first=settings)

    def _query(model):
        if model is ReminderJob:
            return reminder_query
        if model is Appointment:
            return appointment_query
        if model is ClientSettings:
            return settings_query
        return Mock()

    db.query.side_effect = _query

    with patch(
        "app.services.appointment_reminder_service.enqueue_outbox_message",
        return_value=True,
    ):
        results = process_reminder_jobs(db)

    assert results["sent"] == 1
    assert job.status == "SENT"
    db.commit.assert_called_once()
