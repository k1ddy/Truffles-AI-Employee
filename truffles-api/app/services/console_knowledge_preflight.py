"""Safety preflight helpers for console knowledge publish."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.audit_service import AuditEvent

DEFAULT_PREFLIGHT_WINDOW_MINUTES = 30


def build_knowledge_draft_hash(draft_text: str) -> str:
    normalized = draft_text.strip().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()[:16]


def build_knowledge_validate_payload(
    *,
    valid: bool,
    errors: list[str],
    warnings: list[str],
    draft_hash: str,
) -> dict:
    return {
        "valid": bool(valid),
        "errors": errors,
        "warnings": warnings,
        "errors_count": len(errors),
        "warnings_count": len(warnings),
        "draft_hash": draft_hash,
    }


def has_recent_knowledge_preflight(
    *,
    db: Session,
    client_id: UUID,
    branch_id: UUID,
    draft_hash: str,
    now: Optional[datetime] = None,
    window_minutes: int = DEFAULT_PREFLIGHT_WINDOW_MINUTES,
) -> bool:
    resolved_now = now or datetime.now(timezone.utc)
    window_start = resolved_now - timedelta(minutes=max(1, window_minutes))

    events = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.client_id == client_id,
            AuditEvent.branch_id == branch_id,
            AuditEvent.event_type == "knowledge_validate",
            AuditEvent.created_at >= window_start,
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(25)
        .all()
    )

    for event in events:
        payload = event.payload if isinstance(event.payload, dict) else {}
        if payload.get("draft_hash") != draft_hash:
            continue
        if payload.get("valid") is not True:
            continue
        errors = payload.get("errors")
        if isinstance(errors, list) and len(errors) > 0:
            continue
        return True

    return False
