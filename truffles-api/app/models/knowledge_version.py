import uuid

from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID

from app.database import Base


class KnowledgeVersion(Base):
    __tablename__ = "knowledge_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)
    status = Column(Text, nullable=False, default="draft")
    payload_json = Column(JSONB, nullable=False, default=dict)
    pack_yaml = Column(Text)
    checksum = Column(Text)
    summary = Column(Text)
    source_version_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_versions.id"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    created_at = Column(TIMESTAMP(timezone=True))
    published_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    published_at = Column(TIMESTAMP(timezone=True))
