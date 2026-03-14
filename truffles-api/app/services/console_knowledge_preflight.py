"""Safety preflight helpers for console knowledge publish."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.audit_service import AuditEvent

DEFAULT_PREFLIGHT_WINDOW_MINUTES = 30


def build_knowledge_draft_hash(draft_text: str) -> str:
    normalized = draft_text.strip().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()[:16]


def build_knowledge_draft_hash_from_payload(
    payload_json: dict | None,
    *,
    fallback_draft_text: str | None = None,
) -> str:
    if isinstance(payload_json, dict):
        return build_knowledge_draft_hash(
            json.dumps(payload_json, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
    return build_knowledge_draft_hash(fallback_draft_text or "")


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


def build_knowledge_compare_payload(
    *,
    draft_hash: str,
    readiness_status: str,
    improved_total: int,
    unchanged_total: int,
    regressed_total: int,
    manual_review_total: int,
    total_cases: int,
) -> dict:
    return {
        "draft_hash": draft_hash,
        "status": readiness_status,
        "improved_total": improved_total,
        "unchanged_total": unchanged_total,
        "regressed_total": regressed_total,
        "manual_review_total": manual_review_total,
        "total_cases": total_cases,
        "ready": readiness_status == "ready",
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


def get_recent_knowledge_compare_preflight(
    *,
    db: Session,
    client_id: UUID,
    branch_id: UUID,
    draft_hash: str,
    now: Optional[datetime] = None,
    window_minutes: int = DEFAULT_PREFLIGHT_WINDOW_MINUTES,
) -> dict | None:
    resolved_now = now or datetime.now(timezone.utc)
    window_start = resolved_now - timedelta(minutes=max(1, window_minutes))

    events = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.client_id == client_id,
            AuditEvent.branch_id == branch_id,
            AuditEvent.event_type == "knowledge_compare_readiness",
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
        return payload

    return None


def has_recent_knowledge_compare_preflight(
    *,
    db: Session,
    client_id: UUID,
    branch_id: UUID,
    draft_hash: str,
    now: Optional[datetime] = None,
    window_minutes: int = DEFAULT_PREFLIGHT_WINDOW_MINUTES,
    require_ready: bool = True,
) -> bool:
    payload = get_recent_knowledge_compare_preflight(
        db=db,
        client_id=client_id,
        branch_id=branch_id,
        draft_hash=draft_hash,
        now=now,
        window_minutes=window_minutes,
    )
    if not isinstance(payload, dict):
        return False
    if not require_ready:
        return True
    return payload.get("ready") is True or payload.get("status") == "ready"
