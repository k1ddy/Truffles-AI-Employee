from sqlalchemy import Column, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import relationship

from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    config = Column(JSONB, nullable=False, default={})
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)

    company = relationship("Company", back_populates="clients")
    branches = relationship("Branch", back_populates="client")

    @property
    def instance_id(self):
        """Legacy: get instance_id from config. Use branch.instance_id instead."""
        return self.config.get("instance_id") if self.config else None
