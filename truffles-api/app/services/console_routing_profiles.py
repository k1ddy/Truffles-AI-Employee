from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.console_routing_profile import ConsoleRoutingProfile
from app.services.console_errors import ConsoleAPIError

ROUTING_STATUS_AVAILABLE = "available"
ROUTING_STATUS_PAUSED = "paused"
ROUTING_STATUS_FOLLOW_UP_ONLY = "follow_up_only"
SUPPORTED_ROUTING_STATUSES = (
    ROUTING_STATUS_AVAILABLE,
    ROUTING_STATUS_PAUSED,
    ROUTING_STATUS_FOLLOW_UP_ONLY,
)


@dataclass(frozen=True)
class ResolvedConsoleRoutingProfile:
    profile_id: UUID | None = None
    source: str = "default"
    routing_status: str = ROUTING_STATUS_AVAILABLE
    max_open_case_count: int | None = None
    branch_id: UUID | None = None


def normalize_routing_status(value: Optional[str]) -> str:
    normalized = (value or ROUTING_STATUS_AVAILABLE).strip().lower()
    if normalized not in SUPPORTED_ROUTING_STATUSES:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Unsupported routing status")
    return normalized


def normalize_max_open_case_count(value: Optional[int]) -> int | None:
    if value is None:
        return None
    normalized = int(value)
    if normalized < 1:
        raise ConsoleAPIError(400, "INVALID_PARAM", "max_open_case_count must be >= 1")
    return normalized


def list_routing_profiles(
    db: Session,
    *,
    client_id: UUID,
    agent_id: UUID | None = None,
    branch_id: UUID | None = None,
) -> list[ConsoleRoutingProfile]:
    query = db.query(ConsoleRoutingProfile).filter(ConsoleRoutingProfile.client_id == client_id)
    if agent_id is not None:
        query = query.filter(ConsoleRoutingProfile.agent_id == agent_id)
    if branch_id is not None:
        query = query.filter(ConsoleRoutingProfile.branch_id == branch_id)
    return query.order_by(
        ConsoleRoutingProfile.branch_id.is_(None),
        ConsoleRoutingProfile.created_at.desc(),
    ).all()


def upsert_routing_profile(
    db: Session,
    *,
    client_id: UUID,
    agent_id: UUID,
    branch_id: UUID | None,
    routing_status: str,
    max_open_case_count: int | None,
    updated_by_agent_id: UUID | None,
) -> ConsoleRoutingProfile:
    normalized_status = normalize_routing_status(routing_status)
    normalized_capacity = normalize_max_open_case_count(max_open_case_count)

    query = db.query(ConsoleRoutingProfile).filter(
        ConsoleRoutingProfile.client_id == client_id,
        ConsoleRoutingProfile.agent_id == agent_id,
    )
    if branch_id is None:
        query = query.filter(ConsoleRoutingProfile.branch_id.is_(None))
    else:
        query = query.filter(ConsoleRoutingProfile.branch_id == branch_id)
    record = query.first()

    now = datetime.now(timezone.utc)
    if record is None:
        record = ConsoleRoutingProfile(
            id=uuid4(),
            client_id=client_id,
            agent_id=agent_id,
            branch_id=branch_id,
            routing_status=normalized_status,
            max_open_case_count=normalized_capacity,
            updated_by_agent_id=updated_by_agent_id,
            created_at=now,
            updated_at=now,
        )
        db.add(record)
        return record

    record.routing_status = normalized_status
    record.max_open_case_count = normalized_capacity
    record.updated_by_agent_id = updated_by_agent_id
    record.updated_at = now
    return record


def delete_routing_profile(
    db: Session,
    *,
    client_id: UUID,
    agent_id: UUID,
    branch_id: UUID | None,
) -> ConsoleRoutingProfile | None:
    query = db.query(ConsoleRoutingProfile).filter(
        ConsoleRoutingProfile.client_id == client_id,
        ConsoleRoutingProfile.agent_id == agent_id,
    )
    if branch_id is None:
        query = query.filter(ConsoleRoutingProfile.branch_id.is_(None))
    else:
        query = query.filter(ConsoleRoutingProfile.branch_id == branch_id)
    record = query.first()
    if record is None:
        return None
    db.delete(record)
    return record


def resolve_routing_profile_map(
    db: Session,
    *,
    client_id: UUID,
    agent_ids: list[UUID] | set[UUID],
    branch_id: UUID | None,
) -> dict[UUID, ResolvedConsoleRoutingProfile]:
    if not agent_ids:
        return {}

    rows = (
        db.query(ConsoleRoutingProfile)
        .filter(
            ConsoleRoutingProfile.client_id == client_id,
            ConsoleRoutingProfile.agent_id.in_(tuple(agent_ids)),
            (
                ConsoleRoutingProfile.branch_id == branch_id
                if branch_id is not None
                else ConsoleRoutingProfile.branch_id.is_(None)
            )
            | ConsoleRoutingProfile.branch_id.is_(None),
        )
        .order_by(
            ConsoleRoutingProfile.branch_id.is_(None),
            ConsoleRoutingProfile.updated_at.desc(),
        )
        .all()
    )

    resolved: dict[UUID, ResolvedConsoleRoutingProfile] = {}
    for row in rows:
        if row.agent_id in resolved:
            continue
        source = "branch" if row.branch_id else "client"
        resolved[row.agent_id] = ResolvedConsoleRoutingProfile(
            profile_id=row.id,
            source=source,
            routing_status=normalize_routing_status(row.routing_status),
            max_open_case_count=normalize_max_open_case_count(row.max_open_case_count),
            branch_id=row.branch_id,
        )

    for agent_id in agent_ids:
        resolved.setdefault(
            agent_id,
            ResolvedConsoleRoutingProfile(),
        )
    return resolved
