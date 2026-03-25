import uuid

from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class ConsoleBranchChange(Base):
    __tablename__ = "console_branch_changes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)
    actor_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    status = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    draft_payload = Column(JSONB, nullable=False, default=dict)
    diff_payload = Column(JSONB, nullable=False, default=dict)
    validation_payload = Column(JSONB, nullable=True)
    base_snapshot = Column(JSONB, nullable=False, default=dict)
    published_snapshot = Column(JSONB, nullable=True)
    rollback_snapshot = Column(JSONB, nullable=True)
    base_branch_updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    publish_error = Column(Text, nullable=True)
    rollback_error = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    validated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    published_at = Column(TIMESTAMP(timezone=True), nullable=True)
    rolled_back_at = Column(TIMESTAMP(timezone=True), nullable=True)
    published_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    rolled_back_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
