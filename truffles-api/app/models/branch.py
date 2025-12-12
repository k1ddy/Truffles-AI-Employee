import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Branch(Base):
    __tablename__ = "branches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    slug = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    instance_id = Column(Text, nullable=False)
    phone = Column(Text)
    telegram_chat_id = Column(Text)
    knowledge_tag = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))

    client = relationship("Client", back_populates="branches")
