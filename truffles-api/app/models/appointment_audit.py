"""
Audit trail for appointment changes.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class AppointmentAudit(Base):
    __tablename__ = "appointment_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=False)
    actor_type = Column(Text, nullable=False)
    actor_id = Column(UUID(as_uuid=True))
    channel = Column(Text, nullable=False)
    action = Column(Text, nullable=False)
    prev_status = Column(Text)
    new_status = Column(Text)
    prev_version = Column(Integer)
    new_version = Column(Integer)
    payload = Column(JSONB, default=dict, nullable=False)
    trace_id = Column(Text)
    correlation_id = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    appointment = relationship("Appointment")
