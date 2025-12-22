from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import OutboxMessage


def build_inbound_message_id(
    message_id: str | None,
    remote_jid: str | None,
    timestamp: int | None,
    message_text: str | None,
) -> str:
    if message_id:
        return message_id.strip()
    if remote_jid and timestamp is not None:
        return f"{remote_jid}:{timestamp}"
    if remote_jid and message_text:
        digest = hashlib.sha256(message_text.encode("utf-8")).hexdigest()[:16]
        return f"{remote_jid}:{digest}"
    return str(uuid.uuid4())


def enqueue_outbox_message(
    db: Session,
    *,
    client_id,
    conversation_id,
    inbound_message_id: str,
    payload_json: dict[str, Any],
) -> bool:
    now = datetime.now(timezone.utc)
    stmt = (
        insert(OutboxMessage)
        .values(
            id=uuid.uuid4(),
            client_id=client_id,
            conversation_id=conversation_id,
            inbound_message_id=inbound_message_id,
            payload_json=payload_json,
            status="PENDING",
            attempts=0,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_nothing(index_elements=["client_id", "inbound_message_id"])
    )
    result = db.execute(stmt)
    return result.rowcount > 0


def claim_pending_outbox(db: Session, *, limit: int = 10) -> list[dict[str, Any]]:
    rows = (
        db.execute(
            text(
                """
                WITH cte AS (
                    SELECT id
                    FROM outbox_messages
                    WHERE status = 'PENDING'
                      AND (next_attempt_at IS NULL OR next_attempt_at <= NOW())
                    ORDER BY created_at
                    LIMIT :limit
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE outbox_messages
                SET status = 'PROCESSING',
                    attempts = attempts + 1,
                    updated_at = NOW()
                FROM cte
                WHERE outbox_messages.id = cte.id
                RETURNING outbox_messages.id,
                          outbox_messages.client_id,
                          outbox_messages.conversation_id,
                          outbox_messages.inbound_message_id,
                          outbox_messages.payload_json,
                          outbox_messages.attempts
                """
            ),
            {"limit": limit},
        )
        .mappings()
        .all()
    )
    db.commit()
    return rows


def mark_outbox_status(
    db: Session,
    *,
    outbox_id,
    status: str,
    last_error: str | None = None,
) -> None:
    db.execute(
        text(
            """
            UPDATE outbox_messages
            SET status = :status,
                last_error = :last_error,
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": outbox_id, "status": status, "last_error": last_error},
    )
    db.commit()
