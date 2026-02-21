import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class MarketingCampaign(Base):
    __tablename__ = "marketing_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    name = Column(Text, nullable=False)
    message_text = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="draft")
    status_v2 = Column(Text, nullable=False, default="draft")
    segment_code = Column(Text, nullable=False, default="reactivation_30_120")
    audience_mode = Column(Text, nullable=False, default="branch_active_conversations")
    audience_filter = Column(JSONB, nullable=False, default=dict)
    preview_total = Column(Integer, nullable=False, default=0)
    preflight_snapshot = Column(JSONB, nullable=False, default=dict)
    preflight_valid = Column(Boolean, nullable=False, default=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    approved_at = Column(TIMESTAMP(timezone=True))
    requested_review_at = Column(TIMESTAMP(timezone=True))
    run_started_at = Column(TIMESTAMP(timezone=True))
    run_completed_at = Column(TIMESTAMP(timezone=True))
    last_preview_at = Column(TIMESTAMP(timezone=True))
    executed_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
