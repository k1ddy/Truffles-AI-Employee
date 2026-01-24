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

logger = get_logger(__name__)


class AppointmentConflictError(Exception):
    """Raised when an appointment slot is already taken."""


class AppointmentNotFoundError(Exception):
    """Raised when an appointment is not found."""


class SpecialistNotFoundError(Exception):
    """Raised when a specialist is not found."""


class BranchNotFoundError(Exception):
    """Raised when a branch is not found."""


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

    def __init__(self, db: Session):
        self.db = db

    def _get_branch(self, branch_id: UUID) -> Optional[Branch]:
        return self.db.query(Branch).filter(Branch.id == branch_id).first()

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
        status: str = "CONFIRMED",
        source: str = "console",
        confirmation_policy: Optional[str] = None,
        audit: Optional[Dict[str, Any]] = None,
        commit: bool = True,
    ) -> Appointment:
        specialist = None
        if specialist_id:
            specialist = self.db.query(Specialist).filter(
                Specialist.id == specialist_id,
                Specialist.is_active == True,
            ).first()

            if not specialist:
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
            self.db.rollback()
            logger.warning("Appointment conflict", extra={"error": str(exc)})
            raise AppointmentConflictError("Slot already booked") from exc

        logger.info("Created appointment", extra={"appointment_id": str(appointment.id)})
        return appointment

    def cancel_appointment(self, appointment_id: UUID, client_id: UUID, reason: Optional[str] = None) -> Appointment:
        appointment = self.db.query(Appointment).filter(
            Appointment.id == appointment_id,
            Appointment.client_id == client_id,
        ).first()

        if not appointment:
            raise AppointmentNotFoundError(f"Appointment {appointment_id} not found")

        appointment.status = "CANCELLED"
        if reason:
            appointment.notes = f"{appointment.notes or ''}\nCancel: {reason}".strip()
        appointment.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return appointment

    def get_appointments(
        self,
        client_id: UUID,
        specialist_id: Optional[UUID] = None,
        branch_ids: Optional[List[UUID]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Appointment]:
        query = self.db.query(Appointment).filter(Appointment.client_id == client_id)

        if specialist_id:
            query = query.filter(Appointment.specialist_id == specialist_id)
        if branch_ids:
            query = query.filter(Appointment.branch_id.in_(branch_ids))
        if date_from:
            query = query.filter(Appointment.start_at >= date_from)
        if date_to:
            query = query.filter(Appointment.start_at <= date_to)
        if status:
            query = query.filter(Appointment.status == status)

        return query.order_by(Appointment.start_at.desc()).limit(limit).all()

    @staticmethod
    def _times_overlap(start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
        return start1 < end2 and end1 > start2
