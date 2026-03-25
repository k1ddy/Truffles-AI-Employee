"""
Calendar busy blocks imported or created manually.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class CalendarBlock(Base):
    __tablename__ = "calendar_blocks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)
    specialist_id = Column(UUID(as_uuid=True), ForeignKey("specialists.id"))
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    source = Column(Text, nullable=False)
    provider = Column(Text)
    external_id = Column(Text)
    status = Column(Text, nullable=False, default="ACTIVE")
    block_metadata = Column("metadata", JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    branch = relationship("Branch")
    specialist = relationship("Specialist")
