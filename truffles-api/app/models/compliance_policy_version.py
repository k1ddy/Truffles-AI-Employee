import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class CompliancePolicyVersion(Base):
    __tablename__ = "compliance_policy_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope = Column(Text, nullable=False)
    data_class = Column(Text, nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"))
    domain_key = Column(Text)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"))
    status = Column(Text, nullable=False, default="published")
    schema_version = Column(Text, nullable=False, default="v1")
    version_number = Column(Integer, nullable=False, default=1)
    payload_json = Column(JSONB, nullable=False, default=dict)
    reason = Column(Text)
    source_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("compliance_policy_versions.id"),
    )
    created_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    published_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    published_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
