import uuid

from sqlalchemy import Column, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class ConsoleIdempotencyKey(Base):
    __tablename__ = "console_idempotency_keys"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "idempotency_key",
            "scope",
            name="ux_console_idempotency_client_key_scope",
        ),
        Index("ix_console_idempotency_created_at", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    idempotency_key = Column(Text, nullable=False)
    scope = Column(Text, nullable=False)
    request_hash = Column(Text, nullable=False)
    response_status = Column(Integer)
    response_body = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
