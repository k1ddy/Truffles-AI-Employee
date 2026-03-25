import uuid

from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class ConsoleConsultantVerificationSession(Base):
    __tablename__ = "console_consultant_verification_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)
    actor_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    actor_role = Column(Text, nullable=False)
    source_mode = Column(Text, nullable=False)
    challenge_mode = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="active")
    title = Column(Text, nullable=True)
    remote_jid = Column(Text, nullable=False)
    runtime_snapshot = Column(JSONB, nullable=False, default=dict)
    latest_preview = Column(JSONB, nullable=False, default=dict)
    latest_outcome = Column(Text, nullable=True)
    latest_business_verdict = Column(Text, nullable=True)
    turns_total = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    last_message_at = Column(TIMESTAMP(timezone=True), nullable=True)
