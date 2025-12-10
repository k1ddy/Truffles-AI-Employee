from sqlalchemy import Column, Text, Integer, Boolean, BigInteger, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Handover(Base):
    __tablename__ = "handovers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), nullable=False)
    trigger_type = Column(Text, nullable=False)  # intent, keyword, manual, timeout
    trigger_value = Column(Text)
    context_summary = Column(Text)
    adapter_type = Column(Text)  # telegram, webhook, bitrix, email, whatsapp_web
    adapter_response = Column(JSONB)
    status = Column(Text, nullable=False)  # pending, active, resolved, bot_handling, timeout
    manager_id = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    notified_at = Column(TIMESTAMP(timezone=True))
    first_response_at = Column(TIMESTAMP(timezone=True))
    resolved_at = Column(TIMESTAMP(timezone=True))
    resolution_type = Column(Text)  # solved, transferred, spam, other
    resolution_notes = Column(Text)
    user_message = Column(Text)
    manager_response = Column(Text)
    assigned_to_name = Column(Text)
    resolution_time_seconds = Column(Integer)
    telegram_message_id = Column(BigInteger)
    assigned_to = Column(String(100))
    reminder_1_sent_at = Column(TIMESTAMP(timezone=True))
    reminder_2_sent_at = Column(TIMESTAMP(timezone=True))
    skipped_by = Column(JSONB, default=[])
    resolved_by_name = Column(Text)
    resolved_by_id = Column(Text)
    channel = Column(String(50), default="telegram")
    channel_ref = Column(String(255))

    conversation = relationship("Conversation", back_populates="handovers")
