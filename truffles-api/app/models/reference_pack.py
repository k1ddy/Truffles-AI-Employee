import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class ReferencePack(Base):
    __tablename__ = "reference_packs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain_slug = Column(Text, nullable=False, unique=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    schema_version = Column(Text, nullable=False, default="v1")
    status = Column(Text, nullable=False, default="active")
    metadata_json = Column(JSONB, nullable=False, default={})
    created_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
