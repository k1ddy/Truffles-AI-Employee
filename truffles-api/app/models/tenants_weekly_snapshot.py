import uuid

from sqlalchemy import Column, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class TenantsWeeklySnapshot(Base):
    __tablename__ = "tenants_weekly_snapshots"
    __table_args__ = (
        UniqueConstraint("client_id", "week_key", name="uq_tenants_weekly_snapshots_client_week"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    week_key = Column(Text, nullable=False)
    snapshot = Column(JSONB, nullable=False, default=dict)
    snapshot_schema_version = Column(Text, nullable=False, default="v1")
    actor_id = Column(UUID(as_uuid=True), nullable=True)
    actor_name = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
