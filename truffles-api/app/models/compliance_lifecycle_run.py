import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class ComplianceLifecycleRun(Base):
    __tablename__ = "compliance_lifecycle_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope = Column(Text, nullable=False)
    data_class = Column(Text, nullable=False)
    operation = Column(Text, nullable=False)
    run_mode = Column(Text, nullable=False, default="preview")
    status = Column(Text, nullable=False, default="completed")
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"))
    domain_key = Column(Text)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"))
    policy_version_id = Column(UUID(as_uuid=True), ForeignKey("compliance_policy_versions.id"))
    policy_scope = Column(Text)
    policy_schema_version = Column(Text)
    policy_snapshot_json = Column(JSONB, nullable=False, default=dict)
    summary_json = Column(JSONB, nullable=False, default=dict)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    triggered_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
