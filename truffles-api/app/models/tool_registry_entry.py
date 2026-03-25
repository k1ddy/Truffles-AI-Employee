import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class ToolRegistryEntry(Base):
    __tablename__ = "tool_registry_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tool_action = Column(Text, nullable=False, unique=True)
    tool_group = Column(Text, nullable=False)
    title = Column(Text)
    summary = Column(Text)
    schema_version = Column(Text, nullable=False, default="v1")
    status = Column(Text, nullable=False, default="active")
    certification_status = Column(Text, nullable=False, default="certified")
    health_status = Column(Text, nullable=False, default="healthy")
    allowed_scopes_json = Column(JSONB, nullable=False, default=list)
    metadata_json = Column(JSONB, nullable=False, default=dict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
