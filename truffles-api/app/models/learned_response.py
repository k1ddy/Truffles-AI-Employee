import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

from app.database import Base


class LearnedResponse(Base):
    __tablename__ = "learned_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"))
    handover_id = Column(UUID(as_uuid=True), ForeignKey("handovers.id"))

    question_text = Column(Text, nullable=False)
    question_normalized = Column(Text)
    response_text = Column(Text, nullable=False)

    source = Column(Text, default="manager")
    source_name = Column(Text)
    source_role = Column(Text)
    source_channel = Column(Text)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))

    status = Column(Text, default="pending")  # pending, approved, rejected
    approved_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    approved_at = Column(TIMESTAMP(timezone=True))
    rejected_at = Column(TIMESTAMP(timezone=True))
    qdrant_point_id = Column(Text)

    use_count = Column(Integer, default=0)
    last_used_at = Column(TIMESTAMP(timezone=True))
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))
