"""
Specialist model for Google Calendar integration.
Each specialist represents a master/employee who can receive bookings.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Specialist(Base):
    """
    Represents a specialist/master who can receive bookings.
    Linked to a Google Calendar for availability tracking.
    """
    __tablename__ = "specialists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)
    
    # Identity
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Google Calendar
    google_calendar_id = Column(String(255), nullable=True)  # e.g., "primary" or calendar email
    
    # Services this specialist can perform
    services = Column(JSONB, default=list)  # [{"name": "Стрижка", "duration_min": 60, "price": 5000}]
    
    # Working hours (if not using Google Calendar)
    working_hours = Column(JSONB, default=dict)  # {"mon": {"start": "09:00", "end": "18:00"}, ...}
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships (simplified - no back_populates to avoid modifying existing models)
    branch = relationship("Branch", foreign_keys=[branch_id])
    bookings = relationship("Booking", back_populates="specialist")

    def __repr__(self):
        return f"<Specialist {self.name} ({self.id})>"
