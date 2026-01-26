import uuid

from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class InboxEvent(Base):
    __tablename__ = "inbox_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)
    provider = Column(Text, nullable=False)
    channel = Column(Text, nullable=False)
    provider_message_id = Column(Text, nullable=False)
    received_at = Column(TIMESTAMP(timezone=True), nullable=False)
    raw_ref = Column(Text)
    dedupe_key = Column(Text)
    status = Column(Text)
    status_at = Column(TIMESTAMP(timezone=True))
    tenant_context = Column(JSONB)
    payload_json = Column(JSONB, nullable=False)
    meta = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
