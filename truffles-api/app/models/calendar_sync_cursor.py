"""
Calendar sync cursors per connection.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class CalendarSyncCursor(Base):
    __tablename__ = "calendar_sync_cursors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("calendar_connections.id"), nullable=False)
    cursor = Column(Text)
    channel_id = Column(Text)
    channel_expiration = Column(DateTime(timezone=True))
    last_synced_at = Column(DateTime(timezone=True))
    cursor_metadata = Column("metadata", JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    connection = relationship("CalendarConnection")
