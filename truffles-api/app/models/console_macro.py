import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID

from app.database import Base


class ConsoleMacro(Base):
    __tablename__ = "console_macros"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    scope = Column(Text, nullable=False)
    label = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    action_config = Column(JSONB, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)
