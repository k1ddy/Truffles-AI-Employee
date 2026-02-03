from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models.appointment import Appointment
from app.models.client_settings import ClientSettings
from app.models.reminder_job import ReminderJob
from app.models.user import User
from app.services.outbox_service import enqueue_outbox_message

logger = get_logger(__name__)

DEFAULT_REMINDER_OFFSETS_MIN = [1440, 120]
DEFAULT_FOLLOWUP_OFFSET_MIN = 120


def _parse_offsets(raw: str | None, *, default: list[int]) -> list[int]:
    if not raw:
        return default
    offsets: list[int] = []
    for item in raw.split(","):
        try:
            minutes = int(item.strip())
        except ValueError:
            continue
        if minutes > 0:
            offsets.append(minutes)
    return offsets or default


def _reminder_offsets() -> list[int]:
    return _parse_offsets(
        os.environ.get("APPOINTMENT_REMINDER_OFFSETS_MIN"),
        default=DEFAULT_REMINDER_OFFSETS_MIN,
    )


def _followup_offset() -> int:
    raw = os.environ.get("APPOINTMENT_FOLLOWUP_OFFSET_MIN")
    try:
        value = int(raw) if raw else DEFAULT_FOLLOWUP_OFFSET_MIN
    except ValueError:
        return DEFAULT_FOLLOWUP_OFFSET_MIN
    return max(value, 0)


def _consent_allows_reminders(settings: ClientSettings | None) -> bool:
    if settings and settings.enable_reminders is False:
        return False
    if settings and settings.learning_consent_status not in {None, "", "granted"}:
        return False
    return True


def _build_dedupe_key(appointment_id: UUID, template: str, run_at: datetime) -> str:
    return f"{appointment_id}:{template}:{run_at.isoformat()}"


def _resolve_remote_jid(user: User | None, appointment: Appointment) -> str | None:
    if user and user.remote_jid:
        return user.remote_jid
    phone = appointment.customer_phone
    if not phone:
        return None
    digits = "".join(char for char in phone if char.isdigit())
    if not digits:
        return None
    return f"{digits}@s.whatsapp.net"


def schedule_default_reminders(
    db: Session,
    *,
    appointment: Appointment,
    commit: bool = False,
) -> list[ReminderJob]:
    if not appointment.start_at:
        return []
    settings = (
        db.query(ClientSettings)
        .filter(ClientSettings.client_id == appointment.client_id)
        .first()
    )
    if not _consent_allows_reminders(settings):
        return []

    now = datetime.now(timezone.utc)
    jobs: list[ReminderJob] = []
    for minutes in _reminder_offsets():
        run_at = appointment.start_at - timedelta(minutes=minutes)
        if run_at <= now:
            continue
        template = "appointment_reminder"
        dedupe_key = _build_dedupe_key(appointment.id, template, run_at)
        jobs.append(
            ReminderJob(
                appointment_id=appointment.id,
                client_id=appointment.client_id,
                branch_id=appointment.branch_id,
                channel="whatsapp",
                template=template,
                run_at=run_at,
                dedupe_key=dedupe_key,
            )
        )

    followup_minutes = _followup_offset()
    if appointment.end_at and followup_minutes > 0:
        run_at = appointment.end_at + timedelta(minutes=followup_minutes)
        if run_at > now:
            template = "post_visit_followup"
            dedupe_key = _build_dedupe_key(appointment.id, template, run_at)
            jobs.append(
                ReminderJob(
                    appointment_id=appointment.id,
                    client_id=appointment.client_id,
                    branch_id=appointment.branch_id,
                    channel="whatsapp",
                    template=template,
                    run_at=run_at,
                    dedupe_key=dedupe_key,
                )
            )

    for job in jobs:
        db.add(job)
    if commit:
        db.commit()
    else:
        db.flush()
    return jobs


def mark_pending_reminders_failed(
    db: Session,
    *,
    appointment_id: UUID,
    reason: str,
    commit: bool = False,
) -> list[ReminderJob]:
    jobs = (
        db.query(ReminderJob)
        .filter(
            ReminderJob.appointment_id == appointment_id,
            ReminderJob.status == "PENDING",
        )
        .all()
    )
    for job in jobs:
        job.status = "FAILED"
        job.last_error = reason
        job.next_attempt_at = None
    if commit:
        db.commit()
    else:
        db.flush()
    return jobs


def _render_template(appointment: Appointment, template: str) -> str:
    date_text = appointment.start_at.strftime("%d.%m")
    time_text = appointment.start_at.strftime("%H:%M")
    if template == "appointment_reminder":
        return f"Напоминаем о записи {date_text} в {time_text}."
    if template == "post_visit_followup":
        return "Спасибо за визит! Будем рады вашему отзыву."
    return "Напоминаем о вашей записи."


def process_reminder_jobs(db: Session) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    jobs = (
        db.query(ReminderJob)
        .filter(
            ReminderJob.status == "PENDING",
            ReminderJob.run_at <= now,
            (ReminderJob.next_attempt_at.is_(None) | (ReminderJob.next_attempt_at <= now)),
        )
        .order_by(ReminderJob.run_at.asc())
        .all()
    )
    results = {"total": len(jobs), "sent": 0, "failed": 0}
    for job in jobs:
        appointment = (
            db.query(Appointment)
            .filter(Appointment.id == job.appointment_id)
            .first()
        )
        if not appointment:
            job.status = "FAILED"
            job.last_error = "appointment_missing"
            results["failed"] += 1
            continue
        settings = (
            db.query(ClientSettings)
            .filter(ClientSettings.client_id == appointment.client_id)
            .first()
        )
        if not _consent_allows_reminders(settings):
            job.status = "FAILED"
            job.last_error = "consent_blocked"
            results["failed"] += 1
            continue
        user = None
        if appointment.user_id:
            user = db.query(User).filter(User.id == appointment.user_id).first()
        remote_jid = _resolve_remote_jid(user, appointment)
        if not remote_jid:
            job.status = "FAILED"
            job.last_error = "remote_jid_missing"
            results["failed"] += 1
            continue
        instance_id = appointment.branch.instance_id if appointment.branch else None
        if not instance_id:
            job.status = "FAILED"
            job.last_error = "instance_id_missing"
            results["failed"] += 1
            continue
        message_text = _render_template(appointment, job.template)
        payload_json = {
            "schema_version": "outbox.v1",
            "event_type": "whatsapp.send_text",
            "idempotency_key": job.dedupe_key,
            "client_id": str(appointment.client_id),
            "branch_id": str(appointment.branch_id),
            "tenant_context": {
                "client_id": str(appointment.client_id),
                "branch_id": str(appointment.branch_id),
                "client_slug": None,
                "instance_id": instance_id,
                "source": "reminder_jobs",
            },
            "conversation_id": str(appointment.conversation_id) if appointment.conversation_id else None,
            "channel": "whatsapp",
            "payload": {
                "remote_jid": remote_jid,
                "text": message_text,
                "instance_id": instance_id,
                "idempotency_key": job.dedupe_key,
            },
        }
        enqueued = enqueue_outbox_message(
            db,
            client_id=appointment.client_id,
            conversation_id=appointment.conversation_id,
            inbound_message_id=job.dedupe_key,
            payload_json=payload_json,
            branch_id=appointment.branch_id,
        )
        if enqueued:
            job.status = "SENT"
            job.last_error = None
            results["sent"] += 1
        else:
            job.status = "FAILED"
            job.last_error = "outbox_duplicate"
            results["failed"] += 1
    db.commit()
    return results
