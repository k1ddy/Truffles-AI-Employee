import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.console_idempotency import ConsoleIdempotencyKey
from app.services.console_errors import ConsoleAPIError


@dataclass
class IdempotencyResult:
    replay: bool
    response_status: Optional[int] = None
    response_body: Optional[dict[str, Any]] = None
    record: Optional[ConsoleIdempotencyKey] = None


def _get_idempotency_ttl_seconds() -> int:
    raw = os.environ.get("CONSOLE_IDEMPOTENCY_TTL_SECONDS", "600")
    try:
        return max(int(raw), 0)
    except ValueError:
        return 600


_IDEMPOTENCY_TTL_SECONDS = _get_idempotency_ttl_seconds()


def _is_stale(record: ConsoleIdempotencyKey, now: datetime) -> bool:
    if _IDEMPOTENCY_TTL_SECONDS <= 0:
        return False
    created_at = record.created_at
    if created_at is None:
        return False
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return (now - created_at).total_seconds() > _IDEMPOTENCY_TTL_SECONDS


def _hash_request(scope: str, agent_id: UUID, payload: dict[str, Any]) -> str:
    raw = json.dumps(
        {
            "scope": scope,
            "agent_id": str(agent_id),
            "payload": payload,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(raw.encode("utf-8")).hexdigest()


def start_idempotency(
    db: Session,
    *,
    client_id: UUID,
    agent_id: UUID,
    idempotency_key: Optional[str],
    scope: str,
    payload: dict[str, Any],
) -> Optional[IdempotencyResult]:
    if not idempotency_key:
        return None

    request_hash = _hash_request(scope, agent_id, payload)
    record = ConsoleIdempotencyKey(
        client_id=client_id,
        agent_id=agent_id,
        idempotency_key=idempotency_key,
        scope=scope,
        request_hash=request_hash,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(ConsoleIdempotencyKey)
            .filter(
                ConsoleIdempotencyKey.client_id == client_id,
                ConsoleIdempotencyKey.idempotency_key == idempotency_key,
                ConsoleIdempotencyKey.scope == scope,
            )
            .first()
        )
        if not existing:
            raise ConsoleAPIError(409, "IDEMPOTENCY_CONFLICT", "Idempotency key conflict")
        if existing.request_hash != request_hash:
            raise ConsoleAPIError(409, "IDEMPOTENCY_CONFLICT", "Idempotency key reuse with different request")
        if existing.response_status is None:
            now = datetime.now(timezone.utc)
            if _is_stale(existing, now):
                db.delete(existing)
                db.commit()
                return start_idempotency(
                    db,
                    client_id=client_id,
                    agent_id=agent_id,
                    idempotency_key=idempotency_key,
                    scope=scope,
                    payload=payload,
                )
            raise ConsoleAPIError(409, "IDEMPOTENCY_CONFLICT", "Idempotency key is already in progress")
        return IdempotencyResult(
            replay=True,
            response_status=existing.response_status,
            response_body=existing.response_body,
        )
    return IdempotencyResult(replay=False, record=record)


def finalize_idempotency(
    db: Session,
    *,
    record: ConsoleIdempotencyKey,
    response_status: int,
    response_body: dict[str, Any],
) -> None:
    record.response_status = response_status
    record.response_body = response_body
    record.updated_at = datetime.now(timezone.utc)
    db.add(record)
    db.commit()


def release_idempotency(db: Session, *, record: ConsoleIdempotencyKey) -> None:
    db.delete(record)
    db.commit()
