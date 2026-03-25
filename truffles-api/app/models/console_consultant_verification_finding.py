import uuid

from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class ConsoleConsultantVerificationFinding(Base):
    __tablename__ = "console_consultant_verification_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)
    actor_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    actor_role = Column(Text, nullable=False)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("console_consultant_verification_sessions.id"),
        nullable=False,
    )
    owner_turn_id = Column(
        UUID(as_uuid=True),
        ForeignKey("console_consultant_verification_turns.id"),
        nullable=True,
    )
    assistant_turn_id = Column(
        UUID(as_uuid=True),
        ForeignKey("console_consultant_verification_turns.id"),
        nullable=False,
    )
    source_mode = Column(Text, nullable=False)
    challenge_mode = Column(Text, nullable=False)
    family_key = Column(Text, nullable=False)
    family_kind = Column(Text, nullable=False)
    family_label = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="new")
    owner_prompt = Column(Text, nullable=False)
    assistant_excerpt = Column(Text, nullable=False)
    owner_note = Column(Text, nullable=True)
    resolution_note = Column(Text, nullable=True)
    outcome = Column(Text, nullable=True)
    business_verdict = Column(Text, nullable=True)
    decision_reason_code = Column(Text, nullable=True)
    source_refs = Column(JSONB, nullable=False, default=list)
    latest_preview = Column(JSONB, nullable=False, default=dict)
    linked_knowledge_backlog_id = Column(UUID(as_uuid=True), nullable=True)
    linked_learning_candidate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("learned_responses.id"),
        nullable=True,
    )
    repeat_count = Column(Integer, nullable=False, default=1)
    first_captured_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    last_captured_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
