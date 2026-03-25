import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Branch(Base):
    __tablename__ = "branches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    slug = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    instance_id = Column(Text)
    webhook_secret = Column(Text)
    phone = Column(Text)
    telegram_chat_id = Column(Text)
    knowledge_tag = Column(Text)
    knowledge_safe_mode = Column(Boolean, default=False)
    knowledge_safe_mode_reason = Column(Text)
    knowledge_safe_mode_at = Column(TIMESTAMP(timezone=True))
    timezone = Column(Text)
    working_hours = Column(JSONB, default=dict)
    booking_settings = Column(JSONB, default=dict)
    onboarding_state = Column(Text)
    onboarding_updated_at = Column(TIMESTAMP(timezone=True))
    go_live_state = Column(Text, nullable=False, default="pending")
    go_live_reason = Column(Text)
    go_live_reviewed_at = Column(TIMESTAMP(timezone=True))
    go_live_reviewed_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    go_live_waiver_until = Column(TIMESTAMP(timezone=True))
    go_live_waiver_reason = Column(Text)
    go_live_waiver_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    is_active = Column(Boolean, default=True)
    integration_state = Column(Text, nullable=False, default="ok")
    integration_reason = Column(Text)
    integration_checked_at = Column(TIMESTAMP(timezone=True))
    integration_degraded_at = Column(TIMESTAMP(timezone=True))
    integration_recovered_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))

    client = relationship("Client", back_populates="branches")
