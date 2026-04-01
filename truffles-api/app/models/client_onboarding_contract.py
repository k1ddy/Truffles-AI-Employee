import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class ClientOnboardingContract(Base):
    __tablename__ = "client_onboarding_contracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"))
    scope = Column(Text, nullable=False)
    payload_json = Column(JSONB, nullable=False, default={})
    schema_version = Column(Text, nullable=False, default="v1")
    status = Column(Text, nullable=False, default="active")
    payment_status = Column(Text, nullable=False, default="pending")
    payment_confirmed_at = Column(DateTime(timezone=True))
    payment_confirmed_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
