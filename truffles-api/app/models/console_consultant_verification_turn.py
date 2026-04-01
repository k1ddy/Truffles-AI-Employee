import uuid

from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class ConsoleConsultantVerificationTurn(Base):
    __tablename__ = "console_consultant_verification_turns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("console_consultant_verification_sessions.id"),
        nullable=False,
    )
    turn_index = Column(Integer, nullable=False)
    role = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    message_metadata = Column(JSONB, nullable=False, default=dict)
    decision_meta = Column(JSONB, nullable=False, default=dict)
    decision_trace = Column(JSONB, nullable=False, default=list)
    source_refs = Column(JSONB, nullable=False, default=list)
    preview = Column(JSONB, nullable=False, default=dict)
    outcome = Column(Text, nullable=True)
    business_verdict = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
