"""
Google Calendar Token storage model.
Stores OAuth2 tokens for Google Calendar API access.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class GoogleCalendarToken(Base):
    """
    Stores OAuth2 tokens for Google Calendar API.
    Tokens are stored at client/branch level.
    """
    __tablename__ = "google_calendar_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)
    
    # OAuth2 tokens
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_type = Column(String(50), default="Bearer")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Scopes granted
    scopes = Column(ARRAY(String), default=["https://www.googleapis.com/auth/calendar"])
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    client = relationship("Client")
    branch = relationship("Branch")

    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        return datetime.now(timezone.utc) >= self.expires_at

    def __repr__(self):
        return f"<GoogleCalendarToken client={self.client_id} branch={self.branch_id}>"
