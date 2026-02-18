"""
Calendar and Booking API Router.
Provides endpoints for slots, bookings, and Google Calendar OAuth.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.models.appointment import Appointment
from app.models.appointment_service import AppointmentService as AppointmentServiceModel
from app.models.appointment_sync_state import AppointmentSyncState
from app.models.branch import Branch
from app.models.specialist import Specialist
from app.services.appointment_reminder_service import schedule_default_reminders
from app.services.appointment_service import (
    AppointmentConflictError,
    AppointmentNotFoundError,
    AppointmentStatusValidationError,
    InvalidAppointmentTransitionError,
    SchedulingService,
    SpecialistNotFoundError,
)
from app.services.calendar_sync_service import enqueue_appointment_sync
from app.services.console_auth import ConsoleAuthContext, get_console_context, require_console_permission
from app.services.console_errors import ConsoleAPIError
from app.services.google_calendar_service import GoogleCalendarService
from app.services.onboarding_state import OnboardingStep, ensure_onboarding_step

logger = get_logger(__name__)

router = APIRouter(prefix="/calendar", tags=["Calendar"])

def _resolve_calendar_branch(context: ConsoleAuthContext) -> UUID:
    if context.effective_branch_id:
        return context.effective_branch_id
    if len(context.branches) == 1:
        return context.branches[0].id
    raise ConsoleAPIError(400, "BRANCH_SELECTION_REQUIRED", "Branch selection required")


# ==================== Schemas ====================

class SlotResponse(BaseModel):
    start: str
    end: str
    start_time: str
    end_time: str
    available: bool


class SlotsResponse(BaseModel):
    date: str
    specialist_id: str
    specialist_name: str
    duration_minutes: int
    slots: List[SlotResponse]


class SpecialistResponse(BaseModel):
    id: str
    name: str
    branch_id: Optional[str] = None
    branch_name: Optional[str] = None
    services: List[dict] = Field(default_factory=list)
    is_active: bool


class SpecialistsResponse(BaseModel):
    items: List[SpecialistResponse]


class SpecialistServicePayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    duration_min: Optional[int] = Field(default=None, ge=5, le=480)
    price: Optional[int] = Field(default=None, ge=0)


class SpecialistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    branch_id: Optional[str] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=255)
    google_calendar_id: Optional[str] = Field(default=None, max_length=255)
    services: List[SpecialistServicePayload] = Field(default_factory=list)
    working_hours: Optional[dict[str, dict[str, str]]] = None
    is_active: bool = True


class SpecialistUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    branch_id: Optional[str] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=255)
    google_calendar_id: Optional[str] = Field(default=None, max_length=255)
    services: Optional[List[SpecialistServicePayload]] = None
    working_hours: Optional[dict[str, dict[str, str]]] = None
    is_active: Optional[bool] = None


class BookingCreate(BaseModel):
    specialist_id: str
    start_at: datetime
    end_at: datetime
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    service_type: Optional[str] = None
    notes: Optional[str] = None
    conversation_id: Optional[str] = None


class BookingStatusUpdateRequest(BaseModel):
    status: str = Field(min_length=3, max_length=32)
    reason: Optional[str] = Field(default=None, max_length=500)


class BookingResponse(BaseModel):
    id: str
    specialist_id: str
    specialist_name: str
    start_at: str
    end_at: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    service_type: Optional[str] = None
    status: str
    google_event_id: Optional[str] = None
    created_at: str


class BookingsListResponse(BaseModel):
    items: List[BookingResponse]


class BookingActionResponse(BaseModel):
    success: bool
    booking: BookingResponse


# ==================== Specialists ====================

def _parse_uuid(raw_value: str, *, field_name: str) -> UUID:
    try:
        return UUID(raw_value)
    except ValueError as exc:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} is invalid") from exc


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_required_text(value: str, *, field_name: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} is required")
    return cleaned


def _normalize_services_payload(
    services: Optional[List[SpecialistServicePayload]],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for service in services or []:
        service_name = _normalize_required_text(service.name, field_name="services.name")
        item: dict[str, Any] = {"name": service_name}
        if service.duration_min is not None:
            item["duration_min"] = int(service.duration_min)
        if service.price is not None:
            item["price"] = int(service.price)
        normalized.append(item)
    return normalized


def _serialize_specialist(specialist: Specialist, service: SchedulingService) -> SpecialistResponse:
    return SpecialistResponse(
        id=str(specialist.id),
        name=specialist.name,
        branch_id=str(specialist.branch_id) if specialist.branch_id else None,
        branch_name=specialist.branch.name if specialist.branch else None,
        services=service.get_specialist_services(specialist),
        is_active=specialist.is_active,
    )


def _resolve_specialist_branch(
    context: ConsoleAuthContext,
    db: Session,
    branch_id: Optional[str],
) -> Branch:
    target_branch_id = _resolve_calendar_branch(context) if branch_id is None else _parse_uuid(
        branch_id,
        field_name="branch_id",
    )
    if context.branch_restricted and target_branch_id not in context.allowed_branch_ids:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Access to this branch denied")
    branch = db.query(Branch).filter(
        Branch.id == target_branch_id,
        Branch.client_id == context.client.id,
    ).first()
    if not branch:
        raise ConsoleAPIError(404, "BRANCH_NOT_FOUND", "Branch not found")
    return branch


def _resolve_specialist(
    context: ConsoleAuthContext,
    db: Session,
    specialist_id: str,
) -> Specialist:
    specialist_uuid = _parse_uuid(specialist_id, field_name="specialist_id")
    specialist = db.query(Specialist).filter(
        Specialist.id == specialist_uuid,
        Specialist.client_id == context.client.id,
    ).first()
    if not specialist:
        raise ConsoleAPIError(404, "SPECIALIST_NOT_FOUND", "Specialist not found")
    if specialist.branch_id is None:
        raise ConsoleAPIError(400, "BRANCH_REQUIRED", "Specialist branch is required")
    if context.branch_restricted and specialist.branch_id not in context.allowed_branch_ids:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Access to this branch denied")
    return specialist


def _set_specialist_active(*, specialist: Specialist, is_active: bool) -> None:
    specialist.is_active = is_active
    specialist.updated_at = datetime.now(timezone.utc)


def _resolve_booking_for_context(
    context: ConsoleAuthContext,
    db: Session,
    booking_id: UUID,
) -> Appointment:
    booking = db.query(Appointment).filter(
        Appointment.id == booking_id,
        Appointment.client_id == context.client.id,
    ).first()
    if not booking:
        raise ConsoleAPIError(404, "BOOKING_NOT_FOUND", "Booking not found")
    if context.branch_restricted and booking.branch_id not in context.allowed_branch_ids:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Access to this branch denied")
    return booking


def _build_booking_response(db: Session, booking: Appointment) -> BookingResponse:
    specialist = None
    if booking.specialist_id:
        specialist = db.query(Specialist).filter(Specialist.id == booking.specialist_id).first()
    service_name = (
        db.query(AppointmentServiceModel.service_name)
        .filter(AppointmentServiceModel.appointment_id == booking.id)
        .scalar()
    )
    google_event_id = (
        db.query(AppointmentSyncState.external_id)
        .filter(
            AppointmentSyncState.appointment_id == booking.id,
            AppointmentSyncState.provider == "google_calendar",
        )
        .scalar()
    )
    return BookingResponse(
        id=str(booking.id),
        specialist_id=str(booking.specialist_id),
        specialist_name=specialist.name if specialist else "Unknown",
        start_at=booking.start_at.isoformat(),
        end_at=booking.end_at.isoformat(),
        customer_name=booking.customer_name,
        customer_phone=booking.customer_phone,
        service_type=service_name,
        status=booking.status,
        google_event_id=google_event_id,
        created_at=booking.created_at.isoformat(),
    )


@router.get("/specialists", response_model=SpecialistsResponse)
async def list_specialists(
    request: Request,
    branch_id: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Get all specialists for the client."""
    context = get_console_context(request, db)
    require_console_permission(context, "calendar", "read")

    query = db.query(Specialist).filter(Specialist.client_id == context.client.id)
    if not include_inactive:
        query = query.filter(Specialist.is_active.is_(True))

    if branch_id:
        requested_branch = _parse_uuid(branch_id, field_name="branch_id")
        if requested_branch not in context.allowed_branch_ids:
            raise ConsoleAPIError(403, "ACCESS_DENIED", "Access to this branch denied")
        query = query.filter(Specialist.branch_id == requested_branch)
    elif context.branch_restricted:
        query = query.filter(Specialist.branch_id.in_(context.allowed_branch_ids))

    specialists = query.order_by(Specialist.name).all()
    service = SchedulingService(db)
    return SpecialistsResponse(items=[_serialize_specialist(s, service) for s in specialists])


@router.post("/specialists", response_model=SpecialistResponse)
async def create_specialist(
    request: Request,
    data: SpecialistCreate,
    db: Session = Depends(get_db),
):
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "team",
        "write",
        message="Only owner/admin can manage specialists",
    )
    branch = _resolve_specialist_branch(context, db, data.branch_id)
    ensure_onboarding_step(db, branch, OnboardingStep.BOOKING)

    now = datetime.now(timezone.utc)
    specialist = Specialist(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=branch.id,
        name=_normalize_required_text(data.name, field_name="name"),
        phone=_normalize_optional_text(data.phone),
        email=_normalize_optional_text(data.email),
        google_calendar_id=_normalize_optional_text(data.google_calendar_id),
        services=_normalize_services_payload(data.services),
        working_hours=data.working_hours or {},
        is_active=bool(data.is_active),
        created_at=now,
        updated_at=now,
    )
    db.add(specialist)
    db.commit()
    db.refresh(specialist)
    service = SchedulingService(db)
    return _serialize_specialist(specialist, service)


@router.patch("/specialists/{specialist_id}", response_model=SpecialistResponse)
async def update_specialist(
    specialist_id: str,
    request: Request,
    data: SpecialistUpdate,
    db: Session = Depends(get_db),
):
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "team",
        "write",
        message="Only owner/admin can manage specialists",
    )
    specialist = _resolve_specialist(context, db, specialist_id)

    if "branch_id" in data.model_fields_set:
        if data.branch_id is None:
            raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id is required")
        target_branch = _resolve_specialist_branch(context, db, data.branch_id)
    else:
        target_branch = specialist.branch
        if not target_branch:
            target_branch = db.query(Branch).filter(
                Branch.id == specialist.branch_id,
                Branch.client_id == context.client.id,
            ).first()
        if not target_branch:
            raise ConsoleAPIError(404, "BRANCH_NOT_FOUND", "Branch not found")
    ensure_onboarding_step(db, target_branch, OnboardingStep.BOOKING)

    if "name" in data.model_fields_set:
        if data.name is None:
            raise ConsoleAPIError(400, "INVALID_PARAM", "name is required")
        specialist.name = _normalize_required_text(data.name, field_name="name")
    if "branch_id" in data.model_fields_set:
        specialist.branch_id = target_branch.id
    if "phone" in data.model_fields_set:
        specialist.phone = _normalize_optional_text(data.phone)
    if "email" in data.model_fields_set:
        specialist.email = _normalize_optional_text(data.email)
    if "google_calendar_id" in data.model_fields_set:
        specialist.google_calendar_id = _normalize_optional_text(data.google_calendar_id)
    if "services" in data.model_fields_set:
        specialist.services = _normalize_services_payload(data.services)
    if "working_hours" in data.model_fields_set:
        specialist.working_hours = data.working_hours or {}
    if "is_active" in data.model_fields_set:
        if data.is_active is None:
            raise ConsoleAPIError(400, "INVALID_PARAM", "is_active must be true or false")
        specialist.is_active = data.is_active
    specialist.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(specialist)
    service = SchedulingService(db)
    return _serialize_specialist(specialist, service)


@router.post("/specialists/{specialist_id}/enable", response_model=SpecialistResponse)
async def enable_specialist(
    specialist_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "team",
        "write",
        message="Only owner/admin can manage specialists",
    )
    specialist = _resolve_specialist(context, db, specialist_id)
    branch = specialist.branch or db.query(Branch).filter(Branch.id == specialist.branch_id).first()
    if not branch:
        raise ConsoleAPIError(404, "BRANCH_NOT_FOUND", "Branch not found")
    ensure_onboarding_step(db, branch, OnboardingStep.BOOKING)
    _set_specialist_active(specialist=specialist, is_active=True)
    db.commit()
    db.refresh(specialist)
    service = SchedulingService(db)
    return _serialize_specialist(specialist, service)


@router.post("/specialists/{specialist_id}/disable", response_model=SpecialistResponse)
async def disable_specialist(
    specialist_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "team",
        "write",
        message="Only owner/admin can manage specialists",
    )
    specialist = _resolve_specialist(context, db, specialist_id)
    branch = specialist.branch or db.query(Branch).filter(Branch.id == specialist.branch_id).first()
    if not branch:
        raise ConsoleAPIError(404, "BRANCH_NOT_FOUND", "Branch not found")
    ensure_onboarding_step(db, branch, OnboardingStep.BOOKING)
    _set_specialist_active(specialist=specialist, is_active=False)
    db.commit()
    db.refresh(specialist)
    service = SchedulingService(db)
    return _serialize_specialist(specialist, service)


# ==================== Slots ====================

@router.get("/slots", response_model=SlotsResponse)
async def get_slots(
    request: Request,
    specialist_id: str,
    date: str,  # YYYY-MM-DD
    duration: int = Query(60, ge=15, le=240),
    db: Session = Depends(get_db)
):
    """
    Get available time slots for a specialist on a given date.
    Combines working hours, existing bookings, and Google Calendar.
    """
    context = get_console_context(request, db)
    require_console_permission(context, "calendar", "read")
    
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise ConsoleAPIError(400, "INVALID_DATE", "Date format must be YYYY-MM-DD")
    
    specialist = db.query(Specialist).filter(
        Specialist.id == UUID(specialist_id),
        Specialist.client_id == context.client.id
    ).first()
    
    if not specialist:
        raise ConsoleAPIError(404, "SPECIALIST_NOT_FOUND", "Specialist not found")

    if specialist.branch_id is None:
        raise ConsoleAPIError(400, "BRANCH_REQUIRED", "Specialist branch is required")

    if context.branch_restricted and specialist.branch_id not in context.allowed_branch_ids:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Access to this branch denied")
    
    service = SchedulingService(db)
    
    try:
        branch_tz = specialist.branch.timezone if specialist.branch and specialist.branch.timezone else "Asia/Almaty"
        try:
            tz = ZoneInfo(branch_tz)
        except Exception:
            tz = ZoneInfo("Asia/Almaty")
        parsed_date = parsed_date.replace(tzinfo=tz)
        slots = service.get_available_slots(
            specialist_id=UUID(specialist_id),
            date=parsed_date,
            duration_minutes=duration,
            client_id=context.client.id,
        )
    except SpecialistNotFoundError:
        raise ConsoleAPIError(404, "SPECIALIST_NOT_FOUND", "Specialist not found")
    
    return SlotsResponse(
        date=date,
        specialist_id=specialist_id,
        specialist_name=specialist.name,
        duration_minutes=duration,
        slots=[
            SlotResponse(
                start=slot.start.isoformat(),
                end=slot.end.isoformat(),
                start_time=slot.start.strftime("%H:%M"),
                end_time=slot.end.strftime("%H:%M"),
                available=slot.available
            )
            for slot in slots
        ]
    )


# ==================== Bookings ====================

@router.post("/bookings", response_model=BookingActionResponse)
async def create_booking(
    request: Request,
    data: BookingCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new booking.
    
    Concurrency-safe: uses FOR UPDATE NOWAIT to prevent double-booking.
    """
    context = get_console_context(request, db)
    require_console_permission(context, "calendar", "write")
    
    # Verify specialist belongs to client
    specialist = db.query(Specialist).filter(
        Specialist.id == UUID(data.specialist_id),
        Specialist.client_id == context.client.id
    ).first()
    
    if not specialist:
        raise ConsoleAPIError(404, "SPECIALIST_NOT_FOUND", "Specialist not found")
    
    if specialist.branch_id is None:
        raise ConsoleAPIError(400, "BRANCH_REQUIRED", "Specialist branch is required")

    service = SchedulingService(db)
    
    try:
        booking = service.create_appointment(
            client_id=context.client.id,
            branch_id=specialist.branch_id,
            specialist_id=UUID(data.specialist_id),
            start_at=data.start_at,
            end_at=data.end_at,
            customer_name=data.customer_name,
            customer_phone=data.customer_phone,
            service_type=data.service_type,
            notes=data.notes,
            created_by=context.agent.id,
            conversation_id=UUID(data.conversation_id) if data.conversation_id else None,
        )

        if specialist.branch and isinstance(specialist.branch.booking_settings, dict):
            availability_provider = specialist.branch.booking_settings.get("availability_provider")
            if availability_provider == "google_calendar":
                enqueue_appointment_sync(
                    db,
                    appointment=booking,
                    action="create",
                    commit=True,
                )
        schedule_default_reminders(
            db,
            appointment=booking,
            commit=True,
        )
        
        logger.info(
            f"Booking created: {booking.id}",
            extra={"context": {
                "agent": context.agent.name,
                "specialist": specialist.name,
                "time": f"{data.start_at} - {data.end_at}"
            }}
        )
        
        return BookingActionResponse(
            success=True,
            booking=BookingResponse(
                id=str(booking.id),
                specialist_id=str(booking.specialist_id),
                specialist_name=specialist.name,
                start_at=booking.start_at.isoformat(),
                end_at=booking.end_at.isoformat(),
                customer_name=booking.customer_name,
                customer_phone=booking.customer_phone,
                service_type=data.service_type,
                status=booking.status,
                google_event_id=None,
                created_at=booking.created_at.isoformat()
            )
        )
        
    except AppointmentConflictError as e:
        raise ConsoleAPIError(
            409,
            "BOOKING_CONFLICT",
            "Выбранное время уже занято. Пожалуйста, выберите другой слот.",
            details={"reason": str(e)}
        )
    except SpecialistNotFoundError:
        raise ConsoleAPIError(404, "SPECIALIST_NOT_FOUND", "Specialist not found")


@router.get("/bookings", response_model=BookingsListResponse)
async def list_bookings(
    request: Request,
    specialist_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get bookings with filters."""
    context = get_console_context(request, db)
    require_console_permission(context, "calendar", "read")
    
    service = SchedulingService(db)
    
    # Parse dates
    parsed_from = None
    parsed_to = None
    if date_from:
        parsed_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if date_to:
        parsed_to = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)

    status_filter = None
    if status:
        status_norm = status.lower()
        status_map = {
            "pending": "PENDING_CONFIRMATION",
            "confirmed": "CONFIRMED",
            "cancelled": "CANCELLED",
            "completed": "COMPLETED",
            "no_show": "NO_SHOW",
            "draft": "DRAFT",
            "hold": "HOLD",
            "checked_in": "CHECKED_IN",
            "reschedule_requested": "RESCHEDULE_REQUESTED",
        }
        status_filter = status_map.get(status_norm, status.upper())
    
    bookings = service.get_appointments(
        client_id=context.client.id,
        specialist_id=UUID(specialist_id) if specialist_id else None,
        branch_ids=list(context.allowed_branch_ids) if context.branch_restricted else None,
        date_from=parsed_from,
        date_to=parsed_to,
        status=status_filter,
        limit=limit
    )
    
    appointment_ids = [b.id for b in bookings]
    specialist_ids = {b.specialist_id for b in bookings if b.specialist_id}
    specialists_map = {
        s.id: s.name
        for s in db.query(Specialist).filter(Specialist.id.in_(specialist_ids)).all()
    }

    services_map = {}
    if appointment_ids:
        rows = db.query(AppointmentServiceModel).filter(
            AppointmentServiceModel.appointment_id.in_(appointment_ids)
        ).all()
        for row in rows:
            services_map.setdefault(row.appointment_id, row.service_name)

    sync_map = {}
    if appointment_ids:
        rows = db.query(AppointmentSyncState).filter(
            AppointmentSyncState.appointment_id.in_(appointment_ids),
            AppointmentSyncState.provider == "google_calendar",
        ).all()
        for row in rows:
            sync_map[row.appointment_id] = row.external_id
    
    return BookingsListResponse(
        items=[
            BookingResponse(
                id=str(b.id),
                specialist_id=str(b.specialist_id),
                specialist_name=specialists_map.get(b.specialist_id, "Unknown"),
                start_at=b.start_at.isoformat(),
                end_at=b.end_at.isoformat(),
                customer_name=b.customer_name,
                customer_phone=b.customer_phone,
                service_type=services_map.get(b.id),
                status=b.status,
                google_event_id=sync_map.get(b.id),
                created_at=b.created_at.isoformat()
            )
            for b in bookings
        ]
    )


@router.post("/bookings/{booking_id}/cancel", response_model=BookingActionResponse)
async def cancel_booking(
    request: Request,
    booking_id: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Cancel a booking."""
    context = get_console_context(request, db)
    require_console_permission(context, "calendar", "write")

    service = SchedulingService(db)

    try:
        booking_uuid = _parse_uuid(booking_id, field_name="booking_id")
        _resolve_booking_for_context(context, db, booking_uuid)
        booking = service.cancel_appointment(
            appointment_id=booking_uuid,
            client_id=context.client.id,
            reason=reason
        )

        logger.info(
            f"Booking cancelled: {booking_id}",
            extra={"context": {"agent": context.agent.name, "reason": reason}}
        )

        if booking.branch and isinstance(booking.branch.booking_settings, dict):
            availability_provider = booking.branch.booking_settings.get("availability_provider")
            if availability_provider == "google_calendar":
                enqueue_appointment_sync(
                    db,
                    appointment=booking,
                    action="cancel",
                    commit=True,
                )

        return BookingActionResponse(
            success=True,
            booking=_build_booking_response(db, booking),
        )

    except AppointmentNotFoundError:
        raise ConsoleAPIError(404, "BOOKING_NOT_FOUND", "Booking not found")


@router.post("/bookings/{booking_id}/status", response_model=BookingActionResponse)
async def update_booking_status(
    request: Request,
    booking_id: str,
    data: BookingStatusUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update booking visit status (completed/no_show)."""
    context = get_console_context(request, db)
    require_console_permission(context, "calendar", "write")

    service = SchedulingService(db)

    booking_uuid = _parse_uuid(booking_id, field_name="booking_id")
    _resolve_booking_for_context(context, db, booking_uuid)
    reason = _normalize_optional_text(data.reason)

    try:
        booking = service.update_appointment_status(
            appointment_id=booking_uuid,
            client_id=context.client.id,
            target_status=data.status,
            actor_id=context.agent.id,
            actor_type="agent",
            channel="console",
            reason=reason,
        )
    except AppointmentNotFoundError:
        raise ConsoleAPIError(404, "BOOKING_NOT_FOUND", "Booking not found")
    except AppointmentStatusValidationError as exc:
        raise ConsoleAPIError(
            400,
            "INVALID_STATUS",
            "Status must be one of: completed, no_show",
            details={"status": exc.status},
        )
    except InvalidAppointmentTransitionError as exc:
        raise ConsoleAPIError(
            409,
            "BOOKING_STATUS_TRANSITION_DENIED",
            "Booking status transition is not allowed",
            details={
                "from": exc.current_status,
                "to": exc.target_status,
            },
        )

    logger.info(
        "Booking status updated",
        extra={
            "context": {
                "agent": context.agent.name,
                "booking_id": booking_id,
                "target_status": booking.status,
            }
        },
    )
    return BookingActionResponse(success=True, booking=_build_booking_response(db, booking))


# ==================== Google Calendar OAuth ====================

@router.get("/google/connect")
async def google_connect(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Start Google Calendar OAuth flow.
    Redirects to Google consent screen.
    """
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "settings",
        "write",
        message="Only owner/admin can connect Google Calendar",
    )
    branch_id = _resolve_calendar_branch(context)
    service = GoogleCalendarService(db)
    auth_url = service.get_auth_url(
        client_id=context.client.id,
        branch_id=branch_id
    )
    
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth callback.
    Stores tokens and redirects to settings page.
    """
    service = GoogleCalendarService(db)
    
    try:
        token = service.handle_callback(code=code, state=state)
        logger.info(f"Google Calendar connected for client {token.client_id}")
        
        # Redirect to settings with success message
        return RedirectResponse(url="/settings?google_connected=true")
        
    except Exception as e:
        logger.error(f"Google OAuth callback failed: {e}")
        return RedirectResponse(url="/settings?google_error=true")


@router.get("/google/status")
async def google_status(
    request: Request,
    db: Session = Depends(get_db)
):
    """Check if Google Calendar is connected."""
    context = get_console_context(request, db)
    require_console_permission(context, "settings", "read")
    branch_id = _resolve_calendar_branch(context)
    
    from app.models.google_calendar_token import GoogleCalendarToken
    
    token = db.query(GoogleCalendarToken).filter(
        GoogleCalendarToken.client_id == context.client.id,
        GoogleCalendarToken.branch_id == branch_id
    ).first()
    
    return {
        "connected": token is not None,
        "expires_at": token.expires_at.isoformat() if token else None,
        "is_expired": token.is_expired() if token else True
    }
