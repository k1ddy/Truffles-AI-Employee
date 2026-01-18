"""
Booking model for appointment scheduling.
Includes concurrency safety through version field and DB constraints.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Booking(Base):
    """
    Represents a booking/appointment with a specialist.
    
    Concurrency Safety:
    - version field for optimistic locking
    - DB exclusion constraint prevents overlapping bookings (see migration)
    - FOR UPDATE NOWAIT used in service layer
    """
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)
    specialist_id = Column(UUID(as_uuid=True), ForeignKey("specialists.id"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    
    # Time slot
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    
    # Customer info
    customer_name = Column(String(255), nullable=True)
    customer_phone = Column(String(50), nullable=True)
    customer_telegram_id = Column(String(100), nullable=True)
    
    # Service details
    service_type = Column(String(255), nullable=True)
    service_duration_min = Column(Integer, nullable=True)
    service_price = Column(Integer, nullable=True)  # in tenge
    notes = Column(Text, nullable=True)
    
    # Status: pending, confirmed, cancelled, completed, no_show
    status = Column(String(50), default="confirmed", nullable=False)
    cancellation_reason = Column(Text, nullable=True)
    
    # Google Calendar sync
    google_event_id = Column(String(255), nullable=True)
    google_sync_status = Column(String(50), default="pending")  # pending, synced, failed
    
    # Audit
    created_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Concurrency control - optimistic locking
    version = Column(Integer, default=1, nullable=False)

    # Relationships
    client = relationship("Client")
    branch = relationship("Branch")
    specialist = relationship("Specialist", back_populates="bookings")
    conversation = relationship("Conversation")
    created_by_agent = relationship("Agent", foreign_keys=[created_by])

    # Indexes for performance
    __table_args__ = (
        Index("idx_bookings_specialist_time", "specialist_id", "start_at", "end_at"),
        Index("idx_bookings_branch_date", "branch_id", "start_at"),
        Index("idx_bookings_status", "status"),
        CheckConstraint("start_at < end_at", name="check_booking_time_order"),
    )

    def __repr__(self):
        return f"<Booking {self.id} {self.start_at} - {self.end_at}>"
