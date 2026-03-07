import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.sql import func

from app.database import Base


class ConsoleSavedView(Base):
    __tablename__ = "console_saved_views"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "agent_id",
            "surface",
            "name",
            name="ux_console_saved_views_name",
        ),
        Index("ix_console_saved_views_surface_updated_at", "surface", "updated_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    surface = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    query_state = Column(JSONB, nullable=False, default=dict)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
