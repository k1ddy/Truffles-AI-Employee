import uuid

from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class OutboxStatusEvent(Base):
    __tablename__ = "outbox_status_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    outbox_id = Column(UUID(as_uuid=True), ForeignKey("outbox_messages.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True))
    branch_id = Column(UUID(as_uuid=True))
    status = Column(Text, nullable=False)
    last_error = Column(Text)
    attempts = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
