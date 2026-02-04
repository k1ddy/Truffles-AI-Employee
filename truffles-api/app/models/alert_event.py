import uuid

from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True))
    conversation_id = Column(UUID(as_uuid=True))
    message_id = Column(UUID(as_uuid=True))
    alert_type = Column(Text, nullable=False)
    alert_metadata = Column("metadata", JSONB)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
