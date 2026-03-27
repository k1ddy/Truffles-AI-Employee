import uuid

from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class KnowledgeActivationJob(Base):
    __tablename__ = "knowledge_activation_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)
    version_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_versions.id"), nullable=False)
    state = Column(Text, nullable=False, default="queued")
    current_stage = Column(Text, nullable=False, default="queued")
    source = Column(Text, nullable=False, default="knowledge_publish")
    attempt_count = Column(Integer, nullable=False, default=1)
    queued_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    started_at = Column(TIMESTAMP(timezone=True))
    heartbeat_at = Column(TIMESTAMP(timezone=True))
    finished_at = Column(TIMESTAMP(timezone=True))
    last_error = Column(Text)
    error_code = Column(Text)
    triggered_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
