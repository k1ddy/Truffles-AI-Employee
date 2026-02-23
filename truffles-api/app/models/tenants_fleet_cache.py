import uuid

from sqlalchemy import Column, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class TenantsFleetCache(Base):
    __tablename__ = "tenants_fleet_cache"
    __table_args__ = (
        UniqueConstraint("cache_type", "scope_key", name="uq_tenants_fleet_cache_scope"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_type = Column(Text, nullable=False)
    scope_key = Column(Text, nullable=False)
    payload_json = Column(JSONB, nullable=False, default=dict)
    schema_version = Column(Text, nullable=False, default="v1")
    generated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
