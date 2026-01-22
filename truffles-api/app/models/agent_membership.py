import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class AgentMembership(Base):
    __tablename__ = "agent_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    scope = Column(Text, nullable=False)  # company, client, branch
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"))
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"))
    role = Column(Text, nullable=False)  # owner, admin, manager, support
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))

    agent = relationship("Agent")
