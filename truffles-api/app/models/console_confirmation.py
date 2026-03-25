import uuid

from sqlalchemy import Column, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class ConsoleConfirmation(Base):
    __tablename__ = "console_confirmations"
    __table_args__ = (
        Index("ix_console_confirmations_client_id", "client_id"),
        Index("ix_console_confirmations_branch_id", "branch_id"),
        Index("ix_console_confirmations_expires_at", "expires_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"))
    actor_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    action = Column(Text, nullable=False)
    target_type = Column(Text, nullable=False)
    target_id = Column(UUID(as_uuid=True), nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    used_at = Column(TIMESTAMP(timezone=True))
