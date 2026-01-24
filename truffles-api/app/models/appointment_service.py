"""
Appointment services snapshot.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class AppointmentService(Base):
    __tablename__ = "appointment_services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"), nullable=True)
    service_name = Column(Text, nullable=False)
    duration_min = Column(Integer, nullable=False)
    price = Column(Integer)
    buffer_before_min = Column(Integer, default=0, nullable=False)
    buffer_after_min = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    appointment = relationship("Appointment")
    service = relationship("Service")
