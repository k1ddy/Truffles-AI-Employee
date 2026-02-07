import uuid

from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class ConsoleOpsJob(Base):
    __tablename__ = "console_ops_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)
    actor_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    job_type = Column(Text, nullable=False)
    mode = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    request_payload = Column(JSONB, nullable=False, default=dict)
    result_payload = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    finished_at = Column(TIMESTAMP(timezone=True), nullable=True)
