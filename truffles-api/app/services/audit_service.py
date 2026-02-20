"""
Audit service for recording and querying audit events.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.database import Base


class AuditEvent(Base):
    """Audit log entry for tracking actions in the console."""

    __tablename__ = "audit_events"

    id = Column("event_id", PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    client_id = Column(PGUUID(as_uuid=True), nullable=False)
    branch_id = Column(PGUUID(as_uuid=True), nullable=True)
    actor_id = Column("actor_agent_id", PGUUID(as_uuid=True), nullable=True)
    actor_name = Column(String(255), nullable=True)
    event_type = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(PGUUID(as_uuid=True), nullable=True)
    payload = Column(JSON, nullable=True)


def record_audit_event(
    db: Session,
    actor: Any = None,
    event_type: str = "",
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    payload: Optional[dict] = None,
    *,
    client_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    actor_id: Optional[UUID | str] = None,
    actor_name: Optional[str] = None,
) -> AuditEvent:
    """
    Record an audit event.

    Args:
        db: Database session
        actor: The agent performing the action (has id, name, client_id, optional branch_id)
        event_type: Type of event (case_taken, case_resolved, message_sent, etc.)
        entity_type: Type of entity being acted upon (handover, conversation, etc.)
        entity_id: ID of the entity
        payload: Additional event data

    Returns:
        The created AuditEvent
    """
    resolved_client_id = client_id or getattr(actor, "client_id", None)
    resolved_branch_id = branch_id or getattr(actor, "branch_id", None)
    resolved_actor_id = actor_id or getattr(actor, "id", None)
    resolved_actor_name = actor_name or getattr(actor, "name", None)

    event = AuditEvent(
        id=uuid4(),
        created_at=datetime.utcnow(),
        client_id=resolved_client_id,
        branch_id=resolved_branch_id,
        actor_id=resolved_actor_id,
        actor_name=resolved_actor_name,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
    )
    db.add(event)
    # Note: commit is expected to be called by the caller
    return event


def list_audit_events(
    db: Session,
    client_id: UUID,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditEvent]:
    """
    List audit events for a client.

    Args:
        db: Database session
        client_id: Filter by client ID
        limit: Maximum number of events to return
        offset: Number of events to skip

    Returns:
        List of AuditEvent objects
    """
    return (
        db.query(AuditEvent)
        .filter(AuditEvent.client_id == client_id)
        .order_by(AuditEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
