import uuid

from sqlalchemy import Column, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class ConsoleQueueState(Base):
    __tablename__ = "console_queue_states"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "agent_id",
            "surface",
            "scope_key",
            name="ux_console_queue_states_scope",
        ),
        Index("ix_console_queue_states_updated_at", "updated_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    surface = Column(Text, nullable=False)
    scope_key = Column(Text, nullable=False)
    selected_branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"))
    case_id = Column(UUID(as_uuid=True))
    conversation_id = Column(UUID(as_uuid=True))
    version = Column(Integer, nullable=False, default=1)
    query_state = Column(JSONB, nullable=False, default=dict)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
