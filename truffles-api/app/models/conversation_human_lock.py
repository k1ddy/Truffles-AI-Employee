import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class ConversationHumanLock(Base):
    __tablename__ = "conversation_human_locks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    remote_jid = Column(Text, nullable=False)
    lock_scope = Column(Text, nullable=False, default="conversation")
    source = Column(Text, nullable=False, default="console")
    reason = Column(Text, nullable=True)
    locked_by_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    locked_by_name = Column(Text, nullable=True)
    lock_until = Column(TIMESTAMP(timezone=True), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    released_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
