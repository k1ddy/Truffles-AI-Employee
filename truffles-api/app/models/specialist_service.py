"""
Specialist to service mapping.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class SpecialistService(Base):
    __tablename__ = "specialist_services"

    specialist_id = Column(UUID(as_uuid=True), ForeignKey("specialists.id"), primary_key=True)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"), primary_key=True)
    duration_min = Column(Integer)
    price = Column(Integer)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    specialist = relationship("Specialist")
    service = relationship("Service")
