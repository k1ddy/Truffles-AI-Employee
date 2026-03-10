"""
Appointment scheduling service (local provider).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from datetime import time as dt_time
from typing import Any, Dict, List, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models.appointment import Appointment
from app.models.appointment_audit import AppointmentAudit
from app.models.appointment_service import AppointmentService as AppointmentServiceModel
from app.models.branch import Branch
from app.models.calendar_block import CalendarBlock
from app.models.service import Service
from app.models.specialist import Specialist
from app.models.specialist_service import SpecialistService
from app.models.visit import Visit
from app.services.appointment_reminder_service import mark_pending_reminders_failed

logger = get_logger(__name__)


class AppointmentConflictError(Exception):
    """Raised when an appointment slot is already taken."""


class AppointmentNotFoundError(Exception):
    """Raised when an appointment is not found."""


class SpecialistNotFoundError(Exception):
    """Raised when a specialist is not found."""


class BranchNotFoundError(Exception):
    """Raised when a branch is not found."""


class AppointmentStatusValidationError(Exception):
    """Raised when requested appointment status is invalid for visit transitions."""

    def __init__(self, status: str):
        super().__init__(f"Invalid appointment status: {status}")
        self.status = status


class InvalidAppointmentTransitionError(Exception):
    """Raised when status transition is not allowed by booking state machine."""

    def __init__(self, current_status: str, target_status: str):
        super().__init__(f"Invalid transition: {current_status} -> {target_status}")
        self.current_status = current_status
        self.target_status = target_status


class AppointmentLifecycleActionDeniedError(Exception):
    """Raised when edit/cancel is attempted for a booking outside the active lifecycle."""

    def __init__(self, action: str, current_status: str):
        super().__init__(f"{action} is not allowed for status {current_status}")
        self.action = action
        self.current_status = current_status


class AppointmentVersionConflictError(Exception):
    """Raised when a lifecycle mutation uses a stale booking version."""

    def __init__(self, expected_version: int, current_version: int):
        super().__init__(f"Version conflict: expected {expected_version}, current {current_version}")
        self.expected_version = expected_version
        self.current_version = current_version


@dataclass
class TimeSlot:
    start: datetime
    end: datetime
    available: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "start_time": self.start.strftime("%H:%M"),
            "end_time": self.end.strftime("%H:%M"),
            "available": self.available,
        }


class SchedulingService:
    """
    Local scheduling service (no external provider calls).
    """

    DEFAULT_SLOT_DURATION = 60

    ACTIVE_STATUSES = {
        "HOLD",
        "PENDING_CONFIRMATION",
        "CONFIRMED",
        "RESCHEDULE_REQUESTED",
        "CHECKED_IN",
    }
    VISIT_STATUSES = {"COMPLETED", "NO_SHOW"}
    VISIT_TRANSITIONS = {
        "HOLD": {"COMPLETED", "NO_SHOW"},
        "PENDING_CONFIRMATION": {"COMPLETED", "NO_SHOW"},
        "CONFIRMED": {"COMPLETED", "NO_SHOW"},
        "RESCHEDULE_REQUESTED": {"COMPLETED", "NO_SHOW"},
        "CHECKED_IN": {"COMPLETED", "NO_SHOW"},
    }

    def __init__(self, db: Session):
        self.db = db

    def _get_branch(self, branch_id: UUID) -> Optional[Branch]:
        return self.db.query(Branch).filter(Branch.id == branch_id).first()

    def _get_specialist(self, specialist_id: Optional[UUID]) -> Optional[Specialist]:
        if not specialist_id:
            return None
        return self.db.query(Specialist).filter(
            Specialist.id == specialist_id,
            Specialist.is_active == True,
        ).first()

    def _get_appointment(self, appointment_id: UUID, client_id: UUID, *, for_update: bool = False) -> Appointment:
        query = self.db.query(Appointment).filter(
            Appointment.id == appointment_id,
            Appointment.client_id == client_id,
        )
        if for_update and hasattr(query, "with_for_update"):
            query = query.with_for_update()
        appointment = query.first()
        if not appointment:
            raise AppointmentNotFoundError(f"Appointment {appointment_id} not found")
        return appointment

    def _assert_expected_version(self, *, appointment: Appointment, expected_version: int) -> int:
        current_version = int(appointment.version or 0)
        if expected_version != current_version:
            raise AppointmentVersionConflictError(expected_version, current_version)
        return current_version

    def _assert_lifecycle_action_allowed(self, *, appointment: Appointment, action: str) -> str:
        normalized_status = self.normalize_visit_status(appointment.status)
        if normalized_status not in self.ACTIVE_STATUSES:
            raise AppointmentLifecycleActionDeniedError(action, normalized_status)
        return normalized_status

    def _assert_slot_available(
        self,
        *,
        appointment_id: UUID,
        specialist_id: UUID,
        start_at: datetime,
        end_at: datetime,
    ) -> None:
        overlapping_appointment = self.db.query(Appointment).filter(
            Appointment.id != appointment_id,
            Appointment.specialist_id == specialist_id,
            Appointment.status != "CANCELLED",
            Appointment.start_at < end_at,
            Appointment.end_at > start_at,
        ).first()
        if overlapping_appointment:
            raise AppointmentConflictError("Slot already booked")

        overlapping_block = self.db.query(CalendarBlock).filter(
            CalendarBlock.specialist_id == specialist_id,
            CalendarBlock.start_at < end_at,
            CalendarBlock.end_at > start_at,
        ).first()
        if overlapping_block:
            raise AppointmentConflictError("Slot blocked")

    def _upsert_service_snapshot(
        self,
        *,
        appointment_id: UUID,
        client_id: UUID,
        branch_id: UUID,
        service_type: str,
        start_at: datetime,
        end_at: datetime,
    ) -> None:
        duration_min = int((end_at - start_at).total_seconds() / 60)
        service_match = self.db.query(Service).filter(
            Service.client_id == client_id,
            Service.branch_id == branch_id,
            Service.name == service_type,
        ).first()
        snapshot = self.db.query(AppointmentServiceModel).filter(
            AppointmentServiceModel.appointment_id == appointment_id,
        ).first()
        if not snapshot:
            snapshot = AppointmentServiceModel(appointment_id=appointment_id, service_name=service_type, duration_min=duration_min)
            self.db.add(snapshot)
        snapshot.service_id = service_match.id if service_match else None
        snapshot.service_name = service_type
        snapshot.duration_min = duration_min
        snapshot.price = service_match.price if service_match else None
        snapshot.buffer_before_min = service_match.buffer_before_min if service_match else 0
        snapshot.buffer_after_min = service_match.buffer_after_min if service_match else 0

    def _get_timezone(self, branch: Optional[Branch]) -> ZoneInfo:
        tz_name = (branch.timezone if branch and branch.timezone else "Asia/Almaty")
        try:
            return ZoneInfo(tz_name)
        except Exception:
            return ZoneInfo("Asia/Almaty")

    def _resolve_working_hours(self, specialist: Specialist, branch: Optional[Branch]) -> Dict[str, Any]:
        if specialist.working_hours:
            return specialist.working_hours
        if branch and branch.working_hours:
            return branch.working_hours
        return {}

    def get_available_slots(
        self,
        specialist_id: UUID,
        date: datetime,
        duration_minutes: int = DEFAULT_SLOT_DURATION,
        client_id: Optional[UUID] = None,
    ) -> List[TimeSlot]:
        specialist = self.db.query(Specialist).filter(
            Specialist.id == specialist_id,
            Specialist.is_active == True,
        ).first()

        if not specialist:
            raise SpecialistNotFoundError(f"Specialist {specialist_id} not found")

        branch = self._get_branch(specialist.branch_id) if specialist.branch_id else None
        tz = self._get_timezone(branch)
        working_hours = self._resolve_working_hours(specialist, branch)

        day_name = date.astimezone(tz).strftime("%a").lower()
        day_hours = working_hours.get(day_name)
        if not day_hours:
            return []

        work_start = datetime.combine(
            date.astimezone(tz).date(),
            dt_time.fromisoformat(day_hours["start"]),
            tzinfo=tz,
        )
        work_end = datetime.combine(
            date.astimezone(tz).date(),
            dt_time.fromisoformat(day_hours["end"]),
            tzinfo=tz,
        )

        day_start = datetime.combine(date.astimezone(tz).date(), dt_time.min, tzinfo=tz)
        day_end = day_start + timedelta(days=1)

        appointments_query = self.db.query(Appointment).filter(
            Appointment.specialist_id == specialist_id,
            Appointment.status.in_(self.ACTIVE_STATUSES),
            Appointment.start_at >= day_start,
            Appointment.start_at < day_end,
        )
        if client_id:
            appointments_query = appointments_query.filter(Appointment.client_id == client_id)
        appointments = appointments_query.all()

        blocks_query = self.db.query(CalendarBlock).filter(
            CalendarBlock.branch_id == specialist.branch_id,
            CalendarBlock.status == "ACTIVE",
            CalendarBlock.start_at < day_end,
            CalendarBlock.end_at > day_start,
        )
        if client_id:
            blocks_query = blocks_query.filter(CalendarBlock.client_id == client_id)
        blocks = blocks_query.all()

        slots: List[TimeSlot] = []
        current = work_start

        while current + timedelta(minutes=duration_minutes) <= work_end:
            slot_end = current + timedelta(minutes=duration_minutes)
            available = True

            for appointment in appointments:
                if self._times_overlap(current, slot_end, appointment.start_at, appointment.end_at):
                    available = False
                    break

            if available:
                for block in blocks:
                    if block.specialist_id and block.specialist_id != specialist_id:
                        continue
                    if self._times_overlap(current, slot_end, block.start_at, block.end_at):
                        available = False
                        break

            slots.append(TimeSlot(start=current, end=slot_end, available=available))
            current = slot_end

        return slots

    def get_specialist_services(self, specialist: Specialist) -> List[Dict[str, Any]]:
        services = (
            self.db.query(SpecialistService, Service)
            .join(Service, SpecialistService.service_id == Service.id)
            .filter(SpecialistService.specialist_id == specialist.id)
            .all()
        )

        if services:
            return [
                {
                    "name": svc.name,
                    "duration_min": link.duration_min or svc.duration_min,
                    "price": link.price or svc.price,
                }
                for link, svc in services
            ]

        return specialist.services or []

    def create_appointment(
        self,
        client_id: UUID,
        branch_id: UUID,
        specialist_id: Optional[UUID],
        start_at: datetime,
        end_at: datetime,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        service_type: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[UUID] = None,
        conversation_id: Optional[UUID] = None,
        case_id: Optional[UUID] = None,
        status: str = "CONFIRMED",
        source: str = "console",
        confirmation_policy: Optional[str] = None,
        audit: Optional[Dict[str, Any]] = None,
        commit: bool = True,
    ) -> Appointment:
        specialist = self._get_specialist(specialist_id)
        if specialist_id and not specialist:
            raise SpecialistNotFoundError(f"Specialist {specialist_id} not found")

        branch = self._get_branch(branch_id)
        if not branch:
            raise BranchNotFoundError(f"Branch {branch_id} not found")
        resolved_confirmation = confirmation_policy or "manager"
        if isinstance(branch.booking_settings, dict):
            resolved_confirmation = branch.booking_settings.get("confirmation_policy", resolved_confirmation)

        appointment = Appointment(
            client_id=client_id,
            branch_id=branch_id,
            specialist_id=specialist_id,
            conversation_id=conversation_id,
            case_id=case_id,
            status=status,
            source=source,
            confirmation_policy=resolved_confirmation,
            start_at=start_at,
            end_at=end_at,
            customer_name=customer_name,
            customer_phone=customer_phone,
            notes=notes,
            created_by=created_by,
        )

        try:
            self.db.add(appointment)
            if service_type:
                service_match = self.db.query(Service).filter(
                    Service.client_id == client_id,
                    Service.branch_id == branch_id,
                    Service.name == service_type,
                ).first()
                duration_min = int((end_at - start_at).total_seconds() / 60)
                appointment_service = AppointmentServiceModel(
                    appointment=appointment,
                    service_id=service_match.id if service_match else None,
                    service_name=service_type,
                    duration_min=duration_min,
                    price=service_match.price if service_match else None,
                    buffer_before_min=service_match.buffer_before_min if service_match else 0,
                    buffer_after_min=service_match.buffer_after_min if service_match else 0,
                )
                self.db.add(appointment_service)
            if audit:
                audit_entry = AppointmentAudit(
                    appointment=appointment,
                    actor_type=audit.get("actor_type", "system"),
                    actor_id=audit.get("actor_id"),
                    channel=audit.get("channel", "system"),
                    action=audit.get("action", "create"),
                    prev_status=audit.get("prev_status"),
                    new_status=appointment.status,
                    prev_version=audit.get("prev_version"),
                    new_version=appointment.version,
                    payload=audit.get("payload", {}),
                    trace_id=audit.get("trace_id"),
                    correlation_id=audit.get("correlation_id"),
                )
                self.db.add(audit_entry)
            if commit:
                self.db.commit()
            else:
                self.db.flush()
            self.db.refresh(appointment)
        except IntegrityError as exc:
            if commit:
                self.db.rollback()
            logger.warning("Appointment conflict", extra={"error": str(exc)})
            raise AppointmentConflictError("Slot already booked") from exc

        logger.info("Created appointment", extra={"appointment_id": str(appointment.id)})
        return appointment

    def cancel_appointment(
        self,
        appointment_id: UUID,
        client_id: UUID,
        expected_version: int,
        reason: Optional[str] = None,
        *,
        actor_id: Optional[UUID] = None,
        actor_type: str = "agent",
        channel: str = "console",
        commit: bool = True,
    ) -> Appointment:
        appointment = self._get_appointment(appointment_id, client_id, for_update=True)
        self._assert_expected_version(appointment=appointment, expected_version=expected_version)
        self._assert_lifecycle_action_allowed(appointment=appointment, action="cancel")

        prev_status = appointment.status
        prev_version = int(appointment.version or 0)
        appointment.status = "CANCELLED"
        appointment.version = prev_version + 1
        if reason:
            appointment.notes = f"{appointment.notes or ''}\nCancel: {reason}".strip()
        appointment.updated_at = datetime.now(timezone.utc)
        self.db.add(
            AppointmentAudit(
                appointment_id=appointment.id,
                actor_type=actor_type,
                actor_id=actor_id,
                channel=channel,
                action="cancel",
                prev_status=prev_status,
                new_status=appointment.status,
                prev_version=prev_version,
                new_version=appointment.version,
                payload={"reason": reason} if reason else {},
                correlation_id=str(appointment.conversation_id) if appointment.conversation_id else None,
            )
        )
        mark_pending_reminders_failed(
            self.db,
            appointment_id=appointment.id,
            reason="cancelled",
            commit=False,
        )
        if commit:
            self.db.commit()
        else:
            self.db.flush()

        return appointment

    def update_appointment(
        self,
        *,
        appointment_id: UUID,
        client_id: UUID,
        specialist_id: UUID,
        start_at: datetime,
        end_at: datetime,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        service_type: Optional[str] = None,
        notes: Optional[str] = None,
        expected_version: int,
        actor_id: Optional[UUID] = None,
        actor_type: str = "agent",
        channel: str = "console",
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        commit: bool = True,
    ) -> Appointment:
        appointment = self._get_appointment(appointment_id, client_id, for_update=True)
        self._assert_expected_version(appointment=appointment, expected_version=expected_version)
        normalized_current = self._assert_lifecycle_action_allowed(appointment=appointment, action="update")
        specialist = self._get_specialist(specialist_id)
        if not specialist:
            raise SpecialistNotFoundError(f"Specialist {specialist_id} not found")
        if specialist.branch_id is None:
            raise BranchNotFoundError(f"Specialist {specialist_id} branch is required")

        self._assert_slot_available(
            appointment_id=appointment.id,
            specialist_id=specialist_id,
            start_at=start_at,
            end_at=end_at,
        )

        current_service_snapshot = self.db.query(AppointmentServiceModel).filter(
            AppointmentServiceModel.appointment_id == appointment.id,
        ).first()
        previous_service_name = current_service_snapshot.service_name if current_service_snapshot else None
        previous_version = int(appointment.version or 0)
        previous_status = appointment.status
        schedule_changed = (
            appointment.specialist_id != specialist_id
            or appointment.start_at != start_at
            or appointment.end_at != end_at
            or previous_service_name != service_type
        )

        appointment.branch_id = specialist.branch_id
        appointment.specialist_id = specialist_id
        appointment.start_at = start_at
        appointment.end_at = end_at
        appointment.customer_name = customer_name
        appointment.customer_phone = customer_phone
        appointment.notes = notes
        if schedule_changed and normalized_current in self.ACTIVE_STATUSES:
            appointment.status = "PENDING_CONFIRMATION"
        appointment.version = previous_version + 1
        appointment.updated_at = datetime.now(timezone.utc)
        if service_type:
            self._upsert_service_snapshot(
                appointment_id=appointment.id,
                client_id=client_id,
                branch_id=specialist.branch_id,
                service_type=service_type,
                start_at=start_at,
                end_at=end_at,
            )

        self.db.add(
            AppointmentAudit(
                appointment_id=appointment.id,
                actor_type=actor_type,
                actor_id=actor_id,
                channel=channel,
                action="update",
                prev_status=previous_status,
                new_status=appointment.status,
                prev_version=previous_version,
                new_version=appointment.version,
                payload={
                    "schedule_changed": schedule_changed,
                    "service_type": service_type,
                },
                trace_id=trace_id,
                correlation_id=correlation_id,
            )
        )

        if commit:
            self.db.commit()
        else:
            self.db.flush()
        return appointment

    @classmethod
    def normalize_visit_status(cls, status: str) -> str:
        return (status or "").strip().upper()

    @classmethod
    def can_transition_to_visit_status(cls, current_status: str, target_status: str) -> bool:
        normalized_current = cls.normalize_visit_status(current_status)
        normalized_target = cls.normalize_visit_status(target_status)
        if normalized_target not in cls.VISIT_STATUSES:
            return False
        if normalized_current == normalized_target:
            return True
        return normalized_target in cls.VISIT_TRANSITIONS.get(normalized_current, set())

    def _upsert_visit_fact(
        self,
        *,
        appointment: Appointment,
        target_status: str,
        actor_id: Optional[UUID],
        now: datetime,
        reason: Optional[str],
    ) -> Visit:
        visit = self.db.query(Visit).filter(Visit.appointment_id == appointment.id).first()
        if not visit:
            visit = Visit(
                appointment_id=appointment.id,
                client_id=appointment.client_id,
                branch_id=appointment.branch_id,
                specialist_id=appointment.specialist_id,
                user_id=appointment.user_id,
                status=target_status,
                created_by=actor_id,
                visit_metadata={},
            )
            self.db.add(visit)

        metadata = visit.visit_metadata if isinstance(visit.visit_metadata, dict) else {}
        metadata = dict(metadata)
        metadata["source"] = "calendar_console"
        metadata["last_transition"] = target_status
        metadata["updated_at"] = now.isoformat()
        if reason:
            metadata["reason"] = reason

        visit.status = target_status
        visit.specialist_id = appointment.specialist_id
        visit.user_id = appointment.user_id
        visit.visit_metadata = metadata

        if target_status == "CHECKED_IN":
            visit.arrived_at = visit.arrived_at or now
            visit.completed_at = None
        elif target_status == "COMPLETED":
            visit.arrived_at = visit.arrived_at or now
            visit.completed_at = now
        elif target_status == "NO_SHOW":
            visit.arrived_at = None
            visit.completed_at = None

        return visit

    def update_appointment_status(
        self,
        *,
        appointment_id: UUID,
        client_id: UUID,
        target_status: str,
        expected_version: int,
        actor_id: Optional[UUID] = None,
        actor_type: str = "agent",
        channel: str = "console",
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        reason: Optional[str] = None,
        commit: bool = True,
    ) -> Appointment:
        normalized_target = self.normalize_visit_status(target_status)
        if normalized_target not in self.VISIT_STATUSES:
            raise AppointmentStatusValidationError(target_status)

        appointment = self._get_appointment(appointment_id, client_id, for_update=True)
        self._assert_expected_version(appointment=appointment, expected_version=expected_version)

        normalized_current = self.normalize_visit_status(appointment.status)
        if not self.can_transition_to_visit_status(normalized_current, normalized_target):
            raise InvalidAppointmentTransitionError(normalized_current, normalized_target)

        now = datetime.now(timezone.utc)
        previous_version = int(appointment.version or 0)
        is_idempotent = normalized_current == normalized_target

        if not is_idempotent:
            appointment.status = normalized_target
            appointment.version = previous_version + 1
            appointment.updated_at = now
            if reason:
                appointment.notes = f"{appointment.notes or ''}\nStatus note: {reason}".strip()
            if normalized_target in {"COMPLETED", "NO_SHOW"}:
                mark_pending_reminders_failed(
                    self.db,
                    appointment_id=appointment.id,
                    reason=normalized_target.lower(),
                    commit=False,
                )

        visit = self._upsert_visit_fact(
            appointment=appointment,
            target_status=normalized_target,
            actor_id=actor_id,
            now=now,
            reason=reason,
        )

        audit_entry = AppointmentAudit(
            appointment=appointment,
            actor_type=actor_type,
            actor_id=actor_id,
            channel=channel,
            action="status_update_idempotent" if is_idempotent else "status_update",
            prev_status=normalized_current,
            new_status=normalized_target,
            prev_version=previous_version,
            new_version=appointment.version,
            payload={
                "reason": reason,
                "visit_id": str(visit.id),
                "idempotent": is_idempotent,
            },
            trace_id=trace_id,
            correlation_id=correlation_id,
        )
        self.db.add(audit_entry)

        if commit:
            self.db.commit()
        else:
            self.db.flush()
        self.db.refresh(appointment)
        return appointment

    def get_appointments(
        self,
        client_id: UUID,
        specialist_id: Optional[UUID] = None,
        branch_ids: Optional[List[UUID]] = None,
        conversation_id: Optional[UUID] = None,
        case_id: Optional[UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        status: Optional[str] = None,
        status_filters: Optional[List[str]] = None,
        lane: Optional[str] = None,
        needs_action: Optional[bool] = None,
        follow_up_owner_id: Optional[UUID] = None,
        follow_up_overdue: Optional[bool] = None,
        cursor_start_at: Optional[datetime] = None,
        cursor_id: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[Appointment]:
        query = self.db.query(Appointment).filter(Appointment.client_id == client_id)

        if specialist_id:
            query = query.filter(Appointment.specialist_id == specialist_id)
        if branch_ids:
            query = query.filter(Appointment.branch_id.in_(branch_ids))
        if conversation_id:
            query = query.filter(Appointment.conversation_id == conversation_id)
        if case_id:
            query = query.filter(Appointment.case_id == case_id)
        if date_from:
            query = query.filter(Appointment.start_at >= date_from)
        if date_to:
            query = query.filter(Appointment.start_at <= date_to)
        if status_filters:
            query = query.filter(Appointment.status.in_(status_filters))
        if status:
            query = query.filter(Appointment.status == status)
        if lane not in (None, "all", "attention"):
            raise ValueError(f"Unsupported lane: {lane}")

        followup_exists = self.db.query(AppointmentAudit.id).filter(
            AppointmentAudit.appointment_id == Appointment.id,
            AppointmentAudit.action == "no_show_followup",
        ).exists()
        pending_no_show_followup_expr = and_(
            Appointment.status == "NO_SHOW",
            ~followup_exists,
        )
        needs_action_expr = or_(
            Appointment.status.in_(["PENDING_CONFIRMATION", "RESCHEDULE_REQUESTED", "HOLD"]),
            pending_no_show_followup_expr,
        )

        if lane == "attention":
            query = query.filter(needs_action_expr)

        if needs_action is True:
            query = query.filter(needs_action_expr)
        elif needs_action is False:
            query = query.filter(~needs_action_expr)

        if follow_up_owner_id:
            query = query.filter(
                pending_no_show_followup_expr,
                Appointment.follow_up_owner_id == follow_up_owner_id,
            )

        if follow_up_overdue is not None:
            now = datetime.now(timezone.utc)
            overdue_expr = and_(
                pending_no_show_followup_expr,
                Appointment.follow_up_due_at.is_not(None),
                Appointment.follow_up_due_at < now,
            )
            if follow_up_overdue:
                query = query.filter(overdue_expr)
            else:
                query = query.filter(
                    pending_no_show_followup_expr,
                    or_(
                        Appointment.follow_up_due_at.is_(None),
                        Appointment.follow_up_due_at >= now,
                    ),
                )

        if cursor_start_at:
            if cursor_id:
                query = query.filter(
                    or_(
                        Appointment.start_at < cursor_start_at,
                        and_(
                            Appointment.start_at == cursor_start_at,
                            Appointment.id < cursor_id,
                        ),
                    )
                )
            else:
                query = query.filter(Appointment.start_at < cursor_start_at)

        return query.order_by(Appointment.start_at.desc(), Appointment.id.desc()).limit(limit).all()

    @staticmethod
    def _times_overlap(start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
        return start1 < end2 and end1 > start2
