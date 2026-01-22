"""
Calendar and Booking API Router.
Provides endpoints for slots, bookings, and Google Calendar OAuth.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.models.booking import Booking
from app.models.specialist import Specialist
from app.services.booking_service import (
    BookingConflictError,
    BookingNotFoundError,
    BookingService,
    SpecialistNotFoundError,
)
from app.services.console_auth import ConsoleAuthContext, get_console_context
from app.services.console_errors import ConsoleAPIError
from app.services.google_calendar_service import GoogleCalendarService

logger = get_logger(__name__)

router = APIRouter(prefix="/calendar", tags=["Calendar"])


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
    services: List[dict] = []
    is_active: bool


class SpecialistsResponse(BaseModel):
    items: List[SpecialistResponse]


class BookingCreate(BaseModel):
    specialist_id: str
    start_at: datetime
    end_at: datetime
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    service_type: Optional[str] = None
    notes: Optional[str] = None
    conversation_id: Optional[str] = None


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

@router.get("/specialists", response_model=SpecialistsResponse)
async def list_specialists(
    request: Request,
    branch_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all specialists for the client."""
    context = get_console_context(request, db)
    
    query = db.query(Specialist).filter(
        Specialist.client_id == context.client.id,
        Specialist.is_active == True
    )
    
    allowed_branch_ids = context.allowed_branch_ids

    if branch_id:
        requested_branch = UUID(branch_id)
        if requested_branch not in allowed_branch_ids:
            raise ConsoleAPIError(403, "ACCESS_DENIED", "Access to this branch denied")
        query = query.filter(Specialist.branch_id == requested_branch)
    elif context.branch_restricted:
        query = query.filter(Specialist.branch_id.in_(allowed_branch_ids))
    
    specialists = query.order_by(Specialist.name).all()
    
    return SpecialistsResponse(
        items=[
            SpecialistResponse(
                id=str(s.id),
                name=s.name,
                branch_id=str(s.branch_id) if s.branch_id else None,
                branch_name=s.branch.name if s.branch else None,
                services=s.services or [],
                is_active=s.is_active
            )
            for s in specialists
        ]
    )


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
    
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d").replace(
            tzinfo=timezone(timedelta(hours=5))
        )
    except ValueError:
        raise ConsoleAPIError(400, "INVALID_DATE", "Date format must be YYYY-MM-DD")
    
    specialist = db.query(Specialist).filter(
        Specialist.id == UUID(specialist_id),
        Specialist.client_id == context.client.id
    ).first()
    
    if not specialist:
        raise ConsoleAPIError(404, "SPECIALIST_NOT_FOUND", "Specialist not found")
    
    service = BookingService(db)
    
    try:
        slots = service.get_available_slots(
            specialist_id=UUID(specialist_id),
            date=parsed_date,
            duration_minutes=duration,
            client_id=context.client.id
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
    
    # Verify specialist belongs to client
    specialist = db.query(Specialist).filter(
        Specialist.id == UUID(data.specialist_id),
        Specialist.client_id == context.client.id
    ).first()
    
    if not specialist:
        raise ConsoleAPIError(404, "SPECIALIST_NOT_FOUND", "Specialist not found")
    
    service = BookingService(db)
    
    try:
        booking = service.create_booking(
            client_id=context.client.id,
            specialist_id=UUID(data.specialist_id),
            start_at=data.start_at,
            end_at=data.end_at,
            customer_name=data.customer_name,
            customer_phone=data.customer_phone,
            service_type=data.service_type,
            notes=data.notes,
            created_by=context.agent.id,
            branch_id=specialist.branch_id,
            conversation_id=UUID(data.conversation_id) if data.conversation_id else None
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
                service_type=booking.service_type,
                status=booking.status,
                google_event_id=booking.google_event_id,
                created_at=booking.created_at.isoformat()
            )
        )
        
    except BookingConflictError as e:
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
    
    service = BookingService(db)
    
    # Parse dates
    parsed_from = None
    parsed_to = None
    if date_from:
        parsed_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if date_to:
        parsed_to = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    
    bookings = service.get_bookings(
        client_id=context.client.id,
        specialist_id=UUID(specialist_id) if specialist_id else None,
        branch_ids=list(context.allowed_branch_ids) if context.branch_restricted else None,
        date_from=parsed_from,
        date_to=parsed_to,
        status=status,
        limit=limit
    )
    
    # Get specialist names
    specialist_ids = {b.specialist_id for b in bookings}
    specialists_map = {
        s.id: s.name
        for s in db.query(Specialist).filter(Specialist.id.in_(specialist_ids)).all()
    }
    
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
                service_type=b.service_type,
                status=b.status,
                google_event_id=b.google_event_id,
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
    
    service = BookingService(db)
    
    try:
        booking = service.cancel_booking(
            booking_id=UUID(booking_id),
            client_id=context.client.id,
            reason=reason
        )
        
        specialist = db.query(Specialist).filter(
            Specialist.id == booking.specialist_id
        ).first()
        
        logger.info(
            f"Booking cancelled: {booking_id}",
            extra={"context": {"agent": context.agent.name, "reason": reason}}
        )
        
        return BookingActionResponse(
            success=True,
            booking=BookingResponse(
                id=str(booking.id),
                specialist_id=str(booking.specialist_id),
                specialist_name=specialist.name if specialist else "Unknown",
                start_at=booking.start_at.isoformat(),
                end_at=booking.end_at.isoformat(),
                customer_name=booking.customer_name,
                customer_phone=booking.customer_phone,
                service_type=booking.service_type,
                status=booking.status,
                google_event_id=booking.google_event_id,
                created_at=booking.created_at.isoformat()
            )
        )
        
    except BookingNotFoundError:
        raise ConsoleAPIError(404, "BOOKING_NOT_FOUND", "Booking not found")


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
    
    # Only owner/admin can connect calendar
    if context.role not in ("owner", "admin"):
        raise ConsoleAPIError(403, "FORBIDDEN", "Only admin can connect Google Calendar")

    if context.branch_restricted and not context.effective_branch_id:
        raise ConsoleAPIError(403, "FORBIDDEN", "Branch selection required for Google Calendar")
    
    service = GoogleCalendarService(db)
    auth_url = service.get_auth_url(
        client_id=context.client.id,
        branch_id=context.effective_branch_id
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
    
    from app.models.google_calendar_token import GoogleCalendarToken
    
    token = db.query(GoogleCalendarToken).filter(
        GoogleCalendarToken.client_id == context.client.id
    ).first()
    
    return {
        "connected": token is not None,
        "expires_at": token.expires_at.isoformat() if token else None,
        "is_expired": token.is_expired() if token else True
    }
