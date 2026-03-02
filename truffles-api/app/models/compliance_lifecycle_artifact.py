import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class ComplianceLifecycleArtifact(Base):
    __tablename__ = "compliance_lifecycle_artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("compliance_lifecycle_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    scope = Column(Text, nullable=False)
    data_class = Column(Text, nullable=False)
    operation = Column(Text, nullable=False)
    run_mode = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"))
    artifact_type = Column(Text, nullable=False, default="compliance_lifecycle_evidence")
    artifact_digest = Column(Text, nullable=False)
    payload_json = Column(JSONB, nullable=False, default=dict)
    records_count = Column(Integer, nullable=False, default=0)
    evidence_record_count = Column(Integer, nullable=False, default=0)
    published_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    published_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
