import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class AgentLinkToken(Base):
    __tablename__ = "agent_link_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    channel = Column(Text, nullable=False, default="telegram")
    token_hash = Column(Text, nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    used_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))

    agent = relationship("Agent", foreign_keys=[agent_id])
