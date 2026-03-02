import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class ComplianceLifecycleRecord(Base):
    __tablename__ = "compliance_lifecycle_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("compliance_lifecycle_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type = Column(Text, nullable=False)
    entity_id = Column(Text)
    action = Column(Text, nullable=False)
    result = Column(Text, nullable=False)
    payload_json = Column(JSONB, nullable=False, default=dict)
    occurred_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
