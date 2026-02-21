import uuid

from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class MarketingDeliveryEvent(Base):
    __tablename__ = "marketing_delivery_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("marketing_campaigns.id"), nullable=False)
    delivery_id = Column(UUID(as_uuid=True), ForeignKey("marketing_campaign_deliveries.id"), nullable=True)
    outbox_id = Column(UUID(as_uuid=True), ForeignKey("outbox_messages.id"), nullable=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False)
    recipient_jid = Column(Text, nullable=True)
    event_type = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False, default=dict)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
