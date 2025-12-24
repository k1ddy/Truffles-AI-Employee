import uuid

from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class AgentIdentity(Base):
    __tablename__ = "agent_identities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    channel = Column(Text, nullable=False)  # telegram, email, crm
    external_id = Column(Text, nullable=False)
    username = Column(Text)
    identity_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))

    agent = relationship("Agent", back_populates="identities")
