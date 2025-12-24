import uuid

from sqlalchemy import BigInteger, Column, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    channel = Column(Text, nullable=False)  # whatsapp, telegram, instagram
    status = Column(Text, nullable=False)  # active, closed, handover
    started_at = Column(TIMESTAMP(timezone=True), nullable=False)
    last_message_at = Column(TIMESTAMP(timezone=True))
    closed_at = Column(TIMESTAMP(timezone=True))
    escalated_at = Column(TIMESTAMP)
    bot_status = Column(Text, default="active")  # active, muted, etc
    bot_muted_until = Column(TIMESTAMP(timezone=True))
    human_operator_id = Column(Text)
    no_count = Column(Integer, default=0)
    retry_offered_at = Column(TIMESTAMP(timezone=True))
    telegram_topic_id = Column(BigInteger)
    state = Column(Text, default="bot_active")  # bot_active, pending, manager_active
    context = Column(JSONB, nullable=False, default=dict)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")
    handovers = relationship("Handover", back_populates="conversation")
