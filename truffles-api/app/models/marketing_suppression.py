import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class MarketingSuppression(Base):
    __tablename__ = "marketing_suppressions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    recipient_jid = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    source = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
