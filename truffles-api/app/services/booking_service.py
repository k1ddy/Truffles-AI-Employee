"""
Booking Service - handles slot availability and booking creation with concurrency safety.
"""
from datetime import datetime, timedelta, timezone
from datetime import time as dt_time
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models.booking import Booking
from app.models.specialist import Specialist
from app.services.google_calendar_service import GoogleCalendarService

logger = get_logger(__name__)


class BookingConflictError(Exception):
    """Raised when a booking slot is already taken."""
    pass


class BookingNotFoundError(Exception):
    """Raised when a booking is not found."""
    pass


class SpecialistNotFoundError(Exception):
    """Raised when a specialist is not found."""
    pass


class TimeSlot:
    """Represents an available time slot."""
    def __init__(self, start: datetime, end: datetime, available: bool = True):
        self.start = start
        self.end = end
        self.available = available
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "start_time": self.start.strftime("%H:%M"),
            "end_time": self.end.strftime("%H:%M"),
            "available": self.available
        }


class BookingService:
    """
    Service for managing bookings with concurrency safety.
    
    Concurrency Safety Mechanisms:
    1. FOR UPDATE NOWAIT - pessimistic locking when checking conflicts
    2. Version field - optimistic locking for updates
    3. DB exclusion constraint - final safety net (see migration)
    """
    
    # Default working hours if not specified
    DEFAULT_WORKING_HOURS = {
        "mon": {"start": "09:00", "end": "18:00"},
        "tue": {"start": "09:00", "end": "18:00"},
        "wed": {"start": "09:00", "end": "18:00"},
        "thu": {"start": "09:00", "end": "18:00"},
        "fri": {"start": "09:00", "end": "18:00"},
        "sat": {"start": "10:00", "end": "16:00"},
        "sun": None  # Closed
    }
    
    # Slot duration in minutes
    DEFAULT_SLOT_DURATION = 60
    
    def __init__(self, db: Session):
        self.db = db
        self.calendar_service = GoogleCalendarService(db)
    
    # ==================== Slot Availability ====================
    
    def get_available_slots(
        self,
        specialist_id: UUID,
        date: datetime,
        duration_minutes: int = DEFAULT_SLOT_DURATION,
        client_id: Optional[UUID] = None
    ) -> List[TimeSlot]:
        """
        Get available time slots for a specialist on a given date.
        
        Combines:
        1. Working hours from specialist settings
        2. Existing bookings from database
        3. Google Calendar busy times (if connected)
        """
        specialist = self.db.query(Specialist).filter(
            Specialist.id == specialist_id,
            Specialist.is_active == True
        ).first()
        
        if not specialist:
            raise SpecialistNotFoundError(f"Specialist {specialist_id} not found")
        
        # Get working hours for the day
        day_name = date.strftime("%a").lower()
        working_hours = specialist.working_hours or self.DEFAULT_WORKING_HOURS
        day_hours = working_hours.get(day_name)
        
        if not day_hours:
            return []  # Day off
        
        # Parse working hours
        work_start = datetime.combine(
            date.date(),
            dt_time.fromisoformat(day_hours["start"]),
            tzinfo=timezone(timedelta(hours=5))  # Asia/Almaty
        )
        work_end = datetime.combine(
            date.date(),
            dt_time.fromisoformat(day_hours["end"]),
            tzinfo=timezone(timedelta(hours=5))
        )
        
        # Get existing bookings
        day_start = datetime.combine(date.date(), dt_time.min, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        
        bookings = self.db.query(Booking).filter(
            Booking.specialist_id == specialist_id,
            Booking.status.in_(["confirmed", "pending"]),
            Booking.start_at >= day_start,
            Booking.start_at < day_end
        ).all()
        
        # Get Google Calendar busy times
        google_busy = []
        if specialist.google_calendar_id and client_id:
            google_busy = self.calendar_service.get_free_busy(
                calendar_id=specialist.google_calendar_id,
                client_id=client_id,
                branch_id=specialist.branch_id,
                time_min=work_start,
                time_max=work_end
            )
        
        # Generate slots
        slots = []
        current = work_start
        
        while current + timedelta(minutes=duration_minutes) <= work_end:
            slot_end = current + timedelta(minutes=duration_minutes)
            
            # Check if slot is available
            available = True
            
            # Check bookings
            for booking in bookings:
                if self._times_overlap(current, slot_end, booking.start_at, booking.end_at):
                    available = False
                    break
            
            # Check Google Calendar
            if available:
                for busy in google_busy:
                    if self._times_overlap(current, slot_end, busy["start"], busy["end"]):
                        available = False
                        break
            
            slots.append(TimeSlot(start=current, end=slot_end, available=available))
            current = slot_end
        
        return slots
    
    def _times_overlap(
        self,
        start1: datetime,
        end1: datetime,
        start2: datetime,
        end2: datetime
    ) -> bool:
        """Check if two time ranges overlap."""
        return start1 < end2 and end1 > start2
    
    # ==================== Booking CRUD ====================
    
    def create_booking(
        self,
        client_id: UUID,
        specialist_id: UUID,
        start_at: datetime,
        end_at: datetime,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        service_type: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        conversation_id: Optional[UUID] = None
    ) -> Booking:
        """
        Create a new booking with concurrency safety.
        
        Uses FOR UPDATE NOWAIT to prevent race conditions.
        Raises BookingConflictError if slot is taken.
        """
        # Verify specialist exists
        specialist = self.db.query(Specialist).filter(
            Specialist.id == specialist_id,
            Specialist.is_active == True
        ).first()
        
        if not specialist:
            raise SpecialistNotFoundError(f"Specialist {specialist_id} not found")
        
        try:
            # Check for conflicts with pessimistic locking
            # FOR UPDATE NOWAIT will raise OperationalError if row is locked
            conflict = self.db.query(Booking).filter(
                Booking.specialist_id == specialist_id,
                Booking.status.in_(["confirmed", "pending"]),
                Booking.start_at < end_at,
                Booking.end_at > start_at
            ).with_for_update(nowait=True).first()
            
            if conflict:
                raise BookingConflictError(
                    f"Slot already booked: {conflict.start_at} - {conflict.end_at}"
                )
            
            # Create booking
            booking = Booking(
                client_id=client_id,
                branch_id=branch_id or specialist.branch_id,
                specialist_id=specialist_id,
                conversation_id=conversation_id,
                start_at=start_at,
                end_at=end_at,
                customer_name=customer_name,
                customer_phone=customer_phone,
                service_type=service_type,
                notes=notes,
                created_by=created_by,
                status="confirmed"
            )
            
            self.db.add(booking)
            self.db.commit()
            self.db.refresh(booking)
            
            logger.info(f"Created booking {booking.id} for specialist {specialist_id}")
            
            # Sync with Google Calendar (async-safe, after commit)
            if specialist.google_calendar_id:
                try:
                    event_id = self.calendar_service.create_event(
                        calendar_id=specialist.google_calendar_id,
                        client_id=client_id,
                        branch_id=booking.branch_id,
                        booking=booking,
                        specialist_name=specialist.name
                    )
                    if event_id:
                        booking.google_event_id = event_id
                        booking.google_sync_status = "synced"
                        self.db.commit()
                except Exception as e:
                    logger.error(f"Failed to sync with Google Calendar: {e}")
                    booking.google_sync_status = "failed"
                    self.db.commit()
            
            return booking
            
        except OperationalError as e:
            # Row is locked by another transaction
            self.db.rollback()
            raise BookingConflictError("Slot is being booked by another user")
    
    def cancel_booking(
        self,
        booking_id: UUID,
        client_id: UUID,
        reason: Optional[str] = None
    ) -> Booking:
        """
        Cancel a booking.
        """
        booking = self.db.query(Booking).filter(
            Booking.id == booking_id,
            Booking.client_id == client_id
        ).first()
        
        if not booking:
            raise BookingNotFoundError(f"Booking {booking_id} not found")
        
        if booking.status == "cancelled":
            raise ValueError("Booking is already cancelled")
        
        booking.status = "cancelled"
        booking.cancellation_reason = reason
        booking.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        
        # Delete from Google Calendar
        if booking.google_event_id:
            specialist = self.db.query(Specialist).filter(
                Specialist.id == booking.specialist_id
            ).first()
            
            if specialist and specialist.google_calendar_id:
                self.calendar_service.delete_event(
                    calendar_id=specialist.google_calendar_id,
                    client_id=client_id,
                    branch_id=booking.branch_id,
                    event_id=booking.google_event_id
                )
        
        logger.info(f"Cancelled booking {booking_id}")
        return booking
    
    def get_bookings(
        self,
        client_id: UUID,
        specialist_id: Optional[UUID] = None,
        branch_id: Optional[UUID] = None,
        branch_ids: Optional[list[UUID]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Booking]:
        """
        Get bookings with filters.
        """
        query = self.db.query(Booking).filter(Booking.client_id == client_id)
        
        if specialist_id:
            query = query.filter(Booking.specialist_id == specialist_id)
        if branch_ids:
            query = query.filter(Booking.branch_id.in_(branch_ids))
        elif branch_id:
            query = query.filter(Booking.branch_id == branch_id)
        if date_from:
            query = query.filter(Booking.start_at >= date_from)
        if date_to:
            query = query.filter(Booking.start_at <= date_to)
        if status:
            query = query.filter(Booking.status == status)
        
        return query.order_by(Booking.start_at.desc()).limit(limit).all()
