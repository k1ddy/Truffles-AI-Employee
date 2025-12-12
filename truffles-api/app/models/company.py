from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(Text, nullable=False)
    billing_info = Column(JSONB, default={})
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))

    clients = relationship("Client", back_populates="company")
