from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models.appointment import Appointment
from app.models.appointment_audit import AppointmentAudit
from app.models.appointment_service import AppointmentService as AppointmentServiceModel
from app.models.appointment_sync_state import AppointmentSyncState
from app.models.branch import Branch
from app.models.calendar_block import CalendarBlock
from app.models.calendar_connection import CalendarConnection
from app.models.calendar_sync_cursor import CalendarSyncCursor
from app.models.client import Client
from app.models.conversation import Conversation
from app.models.google_calendar_token import GoogleCalendarToken
from app.models.specialist import Specialist
from app.services.google_calendar_service import GoogleCalendarService
from app.services.outbox_service import enqueue_outbox_message
from app.services.handover_owner_service import escalate_to_pending
from app.services.state_machine import ConversationState

logger = get_logger(__name__)

PROVIDER_GOOGLE = "google_calendar"

OUTBOX_EVENT_CALENDAR_SYNC_OUTBOUND = "calendar.sync_outbound"
OUTBOX_EVENT_CALENDAR_SYNC_INBOUND = "calendar.sync_inbound"

SYNC_STATE_PENDING = "PENDING"
SYNC_STATE_OK = "OK"
SYNC_STATE_FAILED = "FAILED"
SYNC_STATE_CONFLICT = "CONFLICT"
SYNC_STATE_DISABLED = "DISABLED"


@dataclass(frozen=True)
class ProviderHealth:
    ready: bool
    reason: str | None
    last_synced_at: datetime | None
    connection_id: UUID | None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_env_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _is_inbound_sync_enabled() -> bool:
    return _is_env_enabled(os.environ.get("CALENDAR_SYNC_INBOUND_ENABLED"), default=True)


def _get_stale_seconds() -> int:
    try:
        raw = int(float(os.environ.get("CALENDAR_SYNC_STALE_SECONDS", "900")))
    except (TypeError, ValueError):
        return 900
    return max(raw, 0)


def _get_inbound_interval_seconds() -> int:
    stale_seconds = _get_stale_seconds()
    try:
        raw = int(float(os.environ.get("CALENDAR_SYNC_INBOUND_INTERVAL_SECONDS", "0")))
    except (TypeError, ValueError):
        raw = 0
    if raw <= 0:
        if stale_seconds:
            raw = max(60, stale_seconds // 2)
        else:
            raw = 300
    return max(raw, 60)


def _get_sync_window_days() -> tuple[int, int]:
    try:
        lookback = int(float(os.environ.get("CALENDAR_SYNC_LOOKBACK_DAYS", "14")))
    except (TypeError, ValueError):
        lookback = 14
    try:
        lookahead = int(float(os.environ.get("CALENDAR_SYNC_LOOKAHEAD_DAYS", "60")))
    except (TypeError, ValueError):
        lookahead = 60
    return max(lookback, 1), max(lookahead, 1)


def get_calendar_connection(
    db: Session,
    *,
    branch_id: UUID,
    provider: str = PROVIDER_GOOGLE,
) -> CalendarConnection | None:
    return (
        db.query(CalendarConnection)
        .filter(
            CalendarConnection.branch_id == branch_id,
            CalendarConnection.provider == provider,
            CalendarConnection.status == "ACTIVE",
        )
        .first()
    )


def ensure_calendar_connection(
    db: Session,
    *,
    client_id: UUID,
    branch_id: UUID,
    provider: str = PROVIDER_GOOGLE,
    calendar_id: str | None = None,
    created_by: UUID | None = None,
) -> CalendarConnection:
    connection = (
        db.query(CalendarConnection)
        .filter(
            CalendarConnection.client_id == client_id,
            CalendarConnection.branch_id == branch_id,
            CalendarConnection.provider == provider,
        )
        .first()
    )
    if connection:
        if calendar_id and calendar_id != connection.calendar_id:
            connection.calendar_id = calendar_id
            connection.updated_at = _now()
        if connection.status != "ACTIVE":
            connection.status = "ACTIVE"
        return connection

    connection = CalendarConnection(
        client_id=client_id,
        branch_id=branch_id,
        provider=provider,
        calendar_id=calendar_id,
        status="ACTIVE",
        created_by=created_by,
    )
    db.add(connection)
    db.flush()
    return connection


def _get_or_create_cursor(db: Session, connection_id: UUID) -> CalendarSyncCursor:
    cursor = (
        db.query(CalendarSyncCursor)
        .filter(CalendarSyncCursor.connection_id == connection_id)
        .first()
    )
    if cursor:
        return cursor
    cursor = CalendarSyncCursor(connection_id=connection_id)
    db.add(cursor)
    db.flush()
    return cursor


def get_provider_health(
    db: Session,
    *,
    client_id: UUID,
    branch_id: UUID,
    provider: str = PROVIDER_GOOGLE,
) -> ProviderHealth:
    connection = get_calendar_connection(db, branch_id=branch_id, provider=provider)
    if not connection:
        return ProviderHealth(False, "connection_missing", None, None)

    token = (
        db.query(GoogleCalendarToken)
        .filter(
            GoogleCalendarToken.client_id == client_id,
            GoogleCalendarToken.branch_id == branch_id,
        )
        .first()
    )
    if not token:
        return ProviderHealth(False, "token_missing", None, connection.id)
    if token.is_expired():
        return ProviderHealth(False, "token_expired", None, connection.id)

    cursor = (
        db.query(CalendarSyncCursor)
        .filter(CalendarSyncCursor.connection_id == connection.id)
        .first()
    )
    last_synced_at = cursor.last_synced_at if cursor else None
    if not last_synced_at:
        return ProviderHealth(False, "sync_missing", None, connection.id)

    stale_seconds = _get_stale_seconds()
    if stale_seconds and (_now() - last_synced_at) > timedelta(seconds=stale_seconds):
        return ProviderHealth(False, "sync_stale", last_synced_at, connection.id)

    return ProviderHealth(True, None, last_synced_at, connection.id)


def _get_or_create_sync_state(
    db: Session,
    *,
    appointment_id: UUID,
    provider: str,
) -> AppointmentSyncState:
    state = (
        db.query(AppointmentSyncState)
        .filter(
            AppointmentSyncState.appointment_id == appointment_id,
            AppointmentSyncState.provider == provider,
        )
        .first()
    )
    if state:
        return state
    state = AppointmentSyncState(
        appointment_id=appointment_id,
        provider=provider,
        state=SYNC_STATE_PENDING,
    )
    db.add(state)
    db.flush()
    return state


def enqueue_appointment_sync(
    db: Session,
    *,
    appointment: Appointment,
    action: str,
    provider: str = PROVIDER_GOOGLE,
    idempotency_key: str | None = None,
    commit: bool = False,
) -> tuple[bool, str | None]:
    connection = get_calendar_connection(db, branch_id=appointment.branch_id, provider=provider)
    if not connection:
        return False, "connection_missing"

    sync_state = _get_or_create_sync_state(
        db, appointment_id=appointment.id, provider=provider
    )
    sync_state.state = SYNC_STATE_PENDING
    sync_state.last_error = None
    sync_state.updated_at = _now()

    client = db.query(Client).filter(Client.id == appointment.client_id).first()
    client_slug = client.name if client else None
    calendar_id = connection.calendar_id or "primary"
    idempotency_key = idempotency_key or f"calendar:{appointment.id}:{appointment.version}:{action}"
    payload_json: dict[str, Any] = {
        "schema_version": "outbox.v1",
        "event_type": OUTBOX_EVENT_CALENDAR_SYNC_OUTBOUND,
        "provider": provider,
        "action": action,
        "idempotency_key": idempotency_key,
        "client_id": str(appointment.client_id),
        "branch_id": str(appointment.branch_id),
        "conversation_id": str(appointment.conversation_id) if appointment.conversation_id else None,
        "tenant_context": {
            "client_id": str(appointment.client_id),
            "branch_id": str(appointment.branch_id),
            "client_slug": client_slug,
            "source": "system",
            "producer": "calendar_sync",
        },
        "payload": {
            "appointment_id": str(appointment.id),
            "action": action,
            "calendar_id": calendar_id,
        },
    }

    enqueued = enqueue_outbox_message(
        db,
        client_id=appointment.client_id,
        conversation_id=appointment.conversation_id,
        inbound_message_id=idempotency_key,
        payload_json=payload_json,
        branch_id=appointment.branch_id,
    )
    if commit:
        db.commit()
    else:
        db.flush()
    return enqueued, None if enqueued else "duplicate"


def enqueue_inbound_sync(
    db: Session,
    *,
    client_id: UUID,
    branch_id: UUID,
    provider: str = PROVIDER_GOOGLE,
    calendar_id: str | None = None,
    connection: CalendarConnection | None = None,
    idempotency_key: str | None = None,
    commit: bool = False,
) -> tuple[bool, str | None]:
    connection = connection or get_calendar_connection(db, branch_id=branch_id, provider=provider)
    if not connection:
        return False, "connection_missing"
    calendar_id = calendar_id or connection.calendar_id or "primary"
    idempotency_key = idempotency_key or f"calendar:sync:{provider}:{branch_id}:{_now().date().isoformat()}"
    payload_json: dict[str, Any] = {
        "schema_version": "outbox.v1",
        "event_type": OUTBOX_EVENT_CALENDAR_SYNC_INBOUND,
        "provider": provider,
        "idempotency_key": idempotency_key,
        "client_id": str(client_id),
        "branch_id": str(branch_id),
        "tenant_context": {
            "client_id": str(client_id),
            "branch_id": str(branch_id),
            "source": "system",
            "producer": "calendar_sync",
        },
        "payload": {
            "branch_id": str(branch_id),
            "calendar_id": calendar_id,
        },
    }
    enqueued = enqueue_outbox_message(
        db,
        client_id=client_id,
        conversation_id=None,
        inbound_message_id=idempotency_key,
        payload_json=payload_json,
        branch_id=branch_id,
    )
    if commit:
        db.commit()
    else:
        db.flush()
    return enqueued, None if enqueued else "duplicate"


def schedule_inbound_syncs(
    db: Session,
    *,
    now: datetime | None = None,
    provider: str = PROVIDER_GOOGLE,
) -> dict[str, Any]:
    if not _is_inbound_sync_enabled():
        return {"enabled": False, "scheduled": 0, "skipped": 0, "errors": 0}

    now = now or _now()
    interval_seconds = _get_inbound_interval_seconds()
    connections = (
        db.query(CalendarConnection)
        .filter(
            CalendarConnection.provider == provider,
            CalendarConnection.status == "ACTIVE",
        )
        .all()
    )
    if not connections:
        return {
            "enabled": True,
            "interval_seconds": interval_seconds,
            "scheduled": 0,
            "skipped": 0,
            "errors": 0,
        }

    scheduled = 0
    skipped = 0
    errors = 0
    reasons: dict[str, int] = {}

    def _bump(reason: str) -> None:
        reasons[reason] = reasons.get(reason, 0) + 1

    for connection in connections:
        try:
            branch = (
                db.query(Branch)
                .filter(Branch.id == connection.branch_id)
                .first()
            )
            if not branch or not branch.is_active:
                skipped += 1
                _bump("branch_inactive")
                continue
            availability_provider = None
            if isinstance(branch.booking_settings, dict):
                availability_provider = branch.booking_settings.get("availability_provider")
            if availability_provider and availability_provider != provider:
                skipped += 1
                _bump("availability_disabled")
                continue

            token = (
                db.query(GoogleCalendarToken)
                .filter(
                    GoogleCalendarToken.client_id == connection.client_id,
                    GoogleCalendarToken.branch_id == connection.branch_id,
                )
                .first()
            )
            if not token:
                skipped += 1
                _bump("token_missing")
                continue
            if token.is_expired():
                skipped += 1
                _bump("token_expired")
                continue

            cursor = (
                db.query(CalendarSyncCursor)
                .filter(CalendarSyncCursor.connection_id == connection.id)
                .first()
            )
            last_synced_at = cursor.last_synced_at if cursor else None
            if last_synced_at:
                age_seconds = (now - last_synced_at).total_seconds()
                if age_seconds < interval_seconds:
                    skipped += 1
                    _bump("recent_sync")
                    continue

            bucket = int(now.timestamp() // interval_seconds)
            idempotency_key = f"calendar:sync:{provider}:{connection.branch_id}:{bucket}"
            enqueued, error = enqueue_inbound_sync(
                db,
                client_id=connection.client_id,
                branch_id=connection.branch_id,
                provider=provider,
                calendar_id=connection.calendar_id,
                connection=connection,
                idempotency_key=idempotency_key,
                commit=False,
            )
            if not enqueued:
                skipped += 1
                _bump(error or "duplicate")
                continue
            scheduled += 1
        except Exception as exc:
            errors += 1
            logger.warning(
                "Inbound calendar sync scheduling failed",
                extra={
                    "context": {
                        "branch_id": str(connection.branch_id),
                        "provider": provider,
                        "error": str(exc)[:200],
                    }
                },
            )

    return {
        "enabled": True,
        "interval_seconds": interval_seconds,
        "scheduled": scheduled,
        "skipped": skipped,
        "errors": errors,
        "reasons": reasons,
    }


def _resolve_service_name(db: Session, appointment_id: UUID) -> str | None:
    row = (
        db.query(AppointmentServiceModel)
        .filter(AppointmentServiceModel.appointment_id == appointment_id)
        .first()
    )
    if not row:
        return None
    return row.service_name


def _resolve_specialist_name(db: Session, specialist_id: UUID | None) -> str | None:
    if not specialist_id:
        return None
    specialist = db.query(Specialist).filter(Specialist.id == specialist_id).first()
    if not specialist:
        return None
    return specialist.name


def process_outbound_sync_event(
    db: Session,
    *,
    payload_json: dict[str, Any],
) -> tuple[bool, str | None]:
    provider = payload_json.get("provider") or PROVIDER_GOOGLE
    payload = payload_json.get("payload") if isinstance(payload_json.get("payload"), dict) else {}
    appointment_id = payload.get("appointment_id") or payload_json.get("appointment_id")
    action = payload.get("action") or payload_json.get("action")
    calendar_id = payload.get("calendar_id")

    if not appointment_id or not action:
        return False, "missing_fields"

    try:
        appointment_uuid = UUID(str(appointment_id))
    except ValueError:
        return False, "invalid_appointment_id"

    appointment = (
        db.query(Appointment)
        .filter(Appointment.id == appointment_uuid)
        .first()
    )
    if not appointment:
        return False, "appointment_not_found"

    connection = get_calendar_connection(db, branch_id=appointment.branch_id, provider=provider)
    if not connection:
        sync_state = _get_or_create_sync_state(
            db, appointment_id=appointment.id, provider=provider
        )
        sync_state.state = SYNC_STATE_FAILED
        sync_state.last_error = "connection_missing"
        sync_state.updated_at = _now()
        db.commit()
        return False, "connection_missing"

    calendar_id = calendar_id or connection.calendar_id or "primary"
    sync_state = _get_or_create_sync_state(
        db, appointment_id=appointment.id, provider=provider
    )
    service_name = _resolve_service_name(db, appointment.id)
    specialist_name = _resolve_specialist_name(db, appointment.specialist_id)

    google = GoogleCalendarService(db)
    if not google.available:
        sync_state.state = SYNC_STATE_FAILED
        sync_state.last_error = "provider_unavailable"
        sync_state.updated_at = _now()
        db.commit()
        return False, "provider_unavailable"

    event_id = sync_state.external_id
    event_etag = sync_state.external_etag

    try:
        if action == "create" and event_id and sync_state.state != SYNC_STATE_DISABLED:
            sync_state.state = SYNC_STATE_OK
            sync_state.last_error = None
            sync_state.last_synced_at = _now()
            sync_state.updated_at = _now()
            db.commit()
            return True, None
        if action == "create":
            result = google.create_event(
                calendar_id=calendar_id,
                client_id=appointment.client_id,
                branch_id=appointment.branch_id,
                appointment=appointment,
                specialist_name=specialist_name,
                service_name=service_name,
            )
            if not result:
                raise RuntimeError("create_failed")
            event_id = result.get("id")
            event_etag = result.get("etag")
        elif action == "update":
            if not event_id:
                result = google.create_event(
                    calendar_id=calendar_id,
                    client_id=appointment.client_id,
                    branch_id=appointment.branch_id,
                    appointment=appointment,
                    specialist_name=specialist_name,
                    service_name=service_name,
                )
                if not result:
                    raise RuntimeError("create_failed")
                event_id = result.get("id")
                event_etag = result.get("etag")
            else:
                result = google.update_event(
                    calendar_id=calendar_id,
                    client_id=appointment.client_id,
                    branch_id=appointment.branch_id,
                    event_id=event_id,
                    appointment=appointment,
                    specialist_name=specialist_name,
                    service_name=service_name,
                )
                if not result:
                    raise RuntimeError("update_failed")
                event_etag = result.get("etag")
        elif action == "cancel":
            if event_id:
                ok = google.delete_event(
                    calendar_id=calendar_id,
                    client_id=appointment.client_id,
                    branch_id=appointment.branch_id,
                    event_id=event_id,
                )
                if not ok:
                    raise RuntimeError("cancel_failed")
            sync_state.state = SYNC_STATE_DISABLED
        else:
            return False, "unsupported_action"
    except Exception as exc:
        sync_state.state = SYNC_STATE_FAILED
        sync_state.last_error = str(exc)
        sync_state.updated_at = _now()
        db.commit()
        return False, "provider_error"

    if sync_state.state != SYNC_STATE_DISABLED:
        sync_state.state = SYNC_STATE_OK
    sync_state.external_id = event_id
    sync_state.external_etag = event_etag
    sync_state.last_error = None
    sync_state.last_synced_at = _now()
    sync_state.updated_at = _now()
    db.commit()
    return True, None


def _parse_event_time(value: dict[str, Any] | None) -> datetime | None:
    if not isinstance(value, dict):
        return None
    raw = value.get("dateTime") or value.get("date")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        normalized = raw.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _update_block_from_event(
    db: Session,
    *,
    client_id: UUID,
    branch_id: UUID,
    event: dict[str, Any],
    existing: CalendarBlock | None,
) -> CalendarBlock | None:
    start_at = _parse_event_time(event.get("start"))
    end_at = _parse_event_time(event.get("end"))
    if not start_at or not end_at:
        return None
    status = "ACTIVE"
    if str(event.get("status") or "").lower() == "cancelled":
        status = "CANCELLED"
    metadata = {
        "summary": event.get("summary"),
        "etag": event.get("etag"),
        "status": event.get("status"),
    }
    if existing:
        existing.start_at = start_at
        existing.end_at = end_at
        existing.status = status
        existing.block_metadata = metadata
        existing.updated_at = _now()
        return existing
    block = CalendarBlock(
        client_id=client_id,
        branch_id=branch_id,
        specialist_id=None,
        start_at=start_at,
        end_at=end_at,
        source="google_import",
        provider=PROVIDER_GOOGLE,
        external_id=event.get("id"),
        status=status,
        block_metadata=metadata,
    )
    db.add(block)
    return block


def _apply_external_conflict(
    db: Session,
    *,
    appointment: Appointment,
    reason: str,
    trace_id: str | None = None,
) -> None:
    from app.services.appointment_reminder_service import mark_pending_reminders_failed

    prev_status = appointment.status
    appointment.status = "RESCHEDULE_REQUESTED"
    appointment.updated_at = _now()
    appointment.version = int(appointment.version or 0) + 1
    db.add(
        AppointmentAudit(
            appointment_id=appointment.id,
            actor_type="system",
            actor_id=None,
            channel="calendar_sync",
            action="external_conflict",
            prev_status=prev_status,
            new_status=appointment.status,
            prev_version=appointment.version - 1,
            new_version=appointment.version,
            payload={"reason": reason},
            trace_id=trace_id,
            correlation_id=str(appointment.conversation_id) if appointment.conversation_id else None,
        )
    )
    mark_pending_reminders_failed(
        db,
        appointment_id=appointment.id,
        reason=reason,
        commit=False,
    )
    if appointment.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == appointment.conversation_id)
            .first()
        )
        if conversation and conversation.state == ConversationState.BOT_ACTIVE.value:
            result = escalate_to_pending(
                db=db,
                conversation=conversation,
                user_message="Внешний календарь изменил запись. Нужен перенос.",
                trigger_type="calendar_conflict",
                trigger_value=reason,
            )
            if not result.ok:
                logger.warning("Calendar conflict handoff failed: %s", result.error)


def process_inbound_sync_event(
    db: Session,
    *,
    payload_json: dict[str, Any],
) -> tuple[bool, str | None]:
    provider = payload_json.get("provider") or PROVIDER_GOOGLE
    payload = payload_json.get("payload") if isinstance(payload_json.get("payload"), dict) else {}
    branch_id = payload.get("branch_id") or payload_json.get("branch_id")
    calendar_id = payload.get("calendar_id")
    if not branch_id:
        return False, "missing_branch_id"

    try:
        branch_uuid = UUID(str(branch_id))
    except ValueError:
        return False, "invalid_branch_id"

    branch = db.query(Branch).filter(Branch.id == branch_uuid).first()
    if not branch:
        return False, "branch_not_found"

    connection = get_calendar_connection(db, branch_id=branch_uuid, provider=provider)
    if not connection:
        return False, "connection_missing"
    calendar_id = calendar_id or connection.calendar_id or "primary"

    google = GoogleCalendarService(db)
    if not google.available:
        return False, "provider_unavailable"

    cursor = _get_or_create_cursor(db, connection.id)
    sync_token = cursor.cursor
    lookback_days, lookahead_days = _get_sync_window_days()
    time_min = _now() - timedelta(days=lookback_days)
    time_max = _now() + timedelta(days=lookahead_days)

    events, next_token, error = google.list_events(
        calendar_id=calendar_id,
        client_id=branch.client_id,
        branch_id=branch_uuid,
        sync_token=sync_token,
        time_min=time_min,
        time_max=time_max,
    )
    if error == "sync_token_invalid":
        events, next_token, error = google.list_events(
            calendar_id=calendar_id,
            client_id=branch.client_id,
            branch_id=branch_uuid,
            sync_token=None,
            time_min=time_min,
            time_max=time_max,
        )
    if error:
        return False, error

    event_ids = [event.get("id") for event in events if event.get("id")]
    sync_states = {}
    if event_ids:
        rows = (
            db.query(AppointmentSyncState)
            .filter(
                AppointmentSyncState.provider == provider,
                AppointmentSyncState.external_id.in_(event_ids),
            )
            .all()
        )
        sync_states = {row.external_id: row for row in rows if row.external_id}

    for event in events:
        event_id = event.get("id")
        if not event_id:
            continue
        existing_block = (
            db.query(CalendarBlock)
            .filter(
                CalendarBlock.branch_id == branch_uuid,
                CalendarBlock.provider == provider,
                CalendarBlock.external_id == event_id,
            )
            .first()
        )
        _update_block_from_event(
            db,
            client_id=branch.client_id,
            branch_id=branch_uuid,
            event=event,
            existing=existing_block,
        )
        sync_state = sync_states.get(event_id)
        if not sync_state:
            continue
        appointment = (
            db.query(Appointment)
            .filter(Appointment.id == sync_state.appointment_id)
            .first()
        )
        if not appointment:
            continue
        if sync_state.state == SYNC_STATE_DISABLED or appointment.status == "CANCELLED":
            sync_state.updated_at = _now()
            continue
        event_status = str(event.get("status") or "").lower()
        event_start = _parse_event_time(event.get("start"))
        event_end = _parse_event_time(event.get("end"))
        if event_status == "cancelled":
            sync_state.state = SYNC_STATE_CONFLICT
            sync_state.last_error = "external_cancelled"
            _apply_external_conflict(
                db,
                appointment=appointment,
                reason="external_cancelled",
            )
        elif event_start and event_end and (
            appointment.start_at != event_start or appointment.end_at != event_end
        ):
            sync_state.state = SYNC_STATE_CONFLICT
            sync_state.last_error = "external_rescheduled"
            _apply_external_conflict(
                db,
                appointment=appointment,
                reason="external_rescheduled",
            )
        sync_state.updated_at = _now()

    cursor.cursor = next_token
    cursor.last_synced_at = _now()
    cursor.updated_at = _now()
    db.commit()
    return True, None
