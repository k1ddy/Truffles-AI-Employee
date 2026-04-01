"""
Visit facts for completed/check-in appointments.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Visit(Base):
    __tablename__ = "visits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)
    specialist_id = Column(UUID(as_uuid=True), ForeignKey("specialists.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    status = Column(Text, nullable=False)
    arrived_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    visit_metadata = Column("metadata", JSONB, default=dict, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    appointment = relationship("Appointment")
