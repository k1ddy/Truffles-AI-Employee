from sqlalchemy import Boolean, Column, Numeric, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

from app.database import Base


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(UUID(as_uuid=True), primary_key=True)
    client_id = Column(UUID(as_uuid=True))
    name = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    model = Column(Text)
    temperature = Column(Numeric(3, 2))
    version = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
