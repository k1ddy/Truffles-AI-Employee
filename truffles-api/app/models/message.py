import uuid

from sqlalchemy import Column, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), nullable=False)
    role = Column(Text, nullable=False)  # user, assistant, system, manager
    content = Column(Text, nullable=False)
    intent = Column(Text)
    confidence = Column(Numeric(5, 3))
    message_metadata = Column("metadata", JSONB, nullable=False, default={})
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    processed_at = Column(TIMESTAMP(timezone=True))

    conversation = relationship("Conversation", back_populates="messages")
