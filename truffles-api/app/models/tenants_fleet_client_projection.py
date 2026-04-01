import uuid

from sqlalchemy import Column, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class TenantsFleetClientProjection(Base):
    __tablename__ = "tenants_fleet_client_projection"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    company_id = Column(UUID(as_uuid=True), nullable=True)
    lifecycle_state = Column(Text, nullable=False)
    payment_status = Column(Text, nullable=False)
    commercial_state = Column(Text, nullable=False)
    service_state = Column(Text, nullable=False)
    owner_name = Column(Text, nullable=True)
    next_action = Column(Text, nullable=False)
    total_branches = Column(Integer, nullable=False, default=0)
    active_branches = Column(Integer, nullable=False, default=0)
    degraded_branches = Column(Integer, nullable=False, default=0)
    go_live_ready_branches = Column(Integer, nullable=False, default=0)
    reference_branch_ids = Column(JSONB, nullable=False, default=list)
    reference_branch_reason = Column(Text, nullable=False, default="no_active_branches")
    refreshed_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
