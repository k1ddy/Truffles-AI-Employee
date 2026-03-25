import uuid

from sqlalchemy import Boolean, Column, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class TenantsFleetPrewarmJob(Base):
    __tablename__ = "tenants_fleet_prewarm_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_ids = Column(JSONB, nullable=False, default=list)
    global_required = Column(Boolean, nullable=False, default=False)
    reason = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="pending")
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    locked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
