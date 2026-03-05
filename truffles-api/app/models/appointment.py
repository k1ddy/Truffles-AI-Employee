"""
Appointment model for scheduling (SoT in Postgres).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)
    specialist_id = Column(UUID(as_uuid=True), ForeignKey("specialists.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("handovers.id"), nullable=True)

    status = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    confirmation_policy = Column(Text, nullable=False, default="manager")

    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    hold_expires_at = Column(DateTime(timezone=True))

    customer_name = Column(Text)
    customer_phone = Column(Text)
    notes = Column(Text)

    version = Column(Integer, default=1, nullable=False)

    created_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    client = relationship("Client")
    branch = relationship("Branch")
    specialist = relationship("Specialist")
    user = relationship("User")
