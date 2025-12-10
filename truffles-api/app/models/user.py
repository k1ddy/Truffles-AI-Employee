from sqlalchemy import Column, String, Text, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), nullable=False)
    phone = Column(Text)
    remote_jid = Column(Text)
    name = Column(Text)
    user_metadata = Column("metadata", JSONB, nullable=False, default={})
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    last_active_at = Column(TIMESTAMP(timezone=True))
    telegram_topic_id = Column(BigInteger)

    conversations = relationship("Conversation", back_populates="user")
