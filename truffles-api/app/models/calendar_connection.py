"""
Calendar provider connections per branch.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class CalendarConnection(Base):
    __tablename__ = "calendar_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)
    provider = Column(Text, nullable=False)
    calendar_id = Column(Text)
    status = Column(Text, nullable=False, default="ACTIVE")
    settings = Column(JSONB, default=dict, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    branch = relationship("Branch")
