from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models import Branch, ConsoleConfirmation, KnowledgeVersion
from app.services.audit_service import record_audit_event
from app.services.console_auth import ConsoleAuthContext
from app.services.console_errors import ConsoleAPIError

CONFIRMATION_TTL_SECONDS = 10 * 60
CONFIRMATION_REASON_MAX_LEN = 500

CONFIRMATION_ACTIONS = {
    "knowledge_rollback": "knowledge_version",
    "branch_deactivate": "branch",
    "integration_reconcile": "branch",
}


@dataclass(frozen=True)
class ConfirmationTarget:
    client_id: UUID
    branch_id: Optional[UUID]


def _normalize_reason(reason: str) -> str:
    value = (reason or "").strip()
    if not value:
        raise ConsoleAPIError(400, "INVALID_PARAM", "reason required")
    if len(value) > CONFIRMATION_REASON_MAX_LEN:
        raise ConsoleAPIError(400, "INVALID_PARAM", "reason too long")
    return value


def _resolve_target(
    db: Session,
    context: ConsoleAuthContext,
    target_type: str,
    target_id: UUID,
) -> ConfirmationTarget:
    if target_type == "branch":
        branch = db.query(Branch).filter(Branch.id == target_id).first()
        if not branch:
            raise ConsoleAPIError(404, "NOT_FOUND", "Branch not found")
        if branch.client_id != context.client.id:
            raise ConsoleAPIError(403, "TENANT_MISMATCH", "Branch access denied")
        if context.effective_branch_id and context.effective_branch_id != branch.id:
            raise ConsoleAPIError(403, "BRANCH_ACCESS_DENIED", "Branch access denied")
        return ConfirmationTarget(client_id=branch.client_id, branch_id=branch.id)

    if target_type == "knowledge_version":
        version = db.query(KnowledgeVersion).filter(KnowledgeVersion.id == target_id).first()
        if not version:
            raise ConsoleAPIError(404, "NOT_FOUND", "Knowledge version not found")
        if version.client_id != context.client.id:
            raise ConsoleAPIError(403, "TENANT_MISMATCH", "Knowledge access denied")
        if context.effective_branch_id and context.effective_branch_id != version.branch_id:
            raise ConsoleAPIError(403, "BRANCH_ACCESS_DENIED", "Branch access denied")
        return ConfirmationTarget(client_id=version.client_id, branch_id=version.branch_id)

    raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid confirmation target")


def create_confirmation(
    db: Session,
    context: ConsoleAuthContext,
    *,
    action: str,
    target_type: str,
    target_id: UUID,
    reason: str,
) -> ConsoleConfirmation:
    expected_target = CONFIRMATION_ACTIONS.get(action)
    if not expected_target:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid confirmation action")
    if expected_target != target_type:
        raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid confirmation target")

    normalized_reason = _normalize_reason(reason)
    target = _resolve_target(db, context, target_type, target_id)
    now = datetime.now(timezone.utc)
    confirmation = ConsoleConfirmation(
        id=uuid4(),
        client_id=target.client_id,
        branch_id=target.branch_id,
        actor_id=context.agent.id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        reason=normalized_reason,
        created_at=now,
        expires_at=now + timedelta(seconds=CONFIRMATION_TTL_SECONDS),
    )
    db.add(confirmation)
    record_audit_event(
        db,
        actor=context.agent,
        event_type="confirmation_created",
        entity_type="confirmation",
        entity_id=confirmation.id,
        payload={
            "action": action,
            "target_type": target_type,
            "target_id": str(target_id),
            "expires_at": confirmation.expires_at.isoformat(),
        },
        client_id=target.client_id,
        branch_id=target.branch_id,
    )
    return confirmation


def require_confirmation(
    db: Session,
    context: ConsoleAuthContext,
    *,
    confirmation_id: Optional[UUID],
    action: str,
    target_type: str,
    target_id: UUID,
) -> ConsoleConfirmation:
    if not confirmation_id:
        raise ConsoleAPIError(
            409,
            "CONFIRMATION_REQUIRED",
            "Confirmation required",
            {"action": action, "target_type": target_type, "target_id": str(target_id)},
        )

    confirmation = db.query(ConsoleConfirmation).filter(ConsoleConfirmation.id == confirmation_id).first()
    now = datetime.now(timezone.utc)
    if not confirmation:
        _record_confirmation_failure(db, context, confirmation_id, action, target_type, target_id, "not_found")
        raise ConsoleAPIError(409, "CONFIRMATION_REQUIRED", "Confirmation not found")
    if confirmation.action != action or confirmation.target_type != target_type or confirmation.target_id != target_id:
        _record_confirmation_failure(db, context, confirmation_id, action, target_type, target_id, "mismatch")
        raise ConsoleAPIError(409, "CONFIRMATION_REQUIRED", "Confirmation mismatch")
    if confirmation.actor_id != context.agent.id:
        _record_confirmation_failure(db, context, confirmation_id, action, target_type, target_id, "actor_mismatch")
        raise ConsoleAPIError(409, "CONFIRMATION_REQUIRED", "Confirmation mismatch")
    if confirmation.client_id != context.client.id:
        _record_confirmation_failure(db, context, confirmation_id, action, target_type, target_id, "tenant_mismatch")
        raise ConsoleAPIError(409, "CONFIRMATION_REQUIRED", "Confirmation mismatch")
    if confirmation.branch_id and context.effective_branch_id and confirmation.branch_id != context.effective_branch_id:
        _record_confirmation_failure(db, context, confirmation_id, action, target_type, target_id, "branch_mismatch")
        raise ConsoleAPIError(409, "CONFIRMATION_REQUIRED", "Confirmation mismatch")
    if confirmation.used_at:
        _record_confirmation_failure(db, context, confirmation_id, action, target_type, target_id, "already_used")
        raise ConsoleAPIError(409, "CONFIRMATION_REQUIRED", "Confirmation already used")
    if confirmation.expires_at <= now:
        _record_confirmation_failure(db, context, confirmation_id, action, target_type, target_id, "expired")
        raise ConsoleAPIError(409, "CONFIRMATION_REQUIRED", "Confirmation expired")

    return confirmation


def mark_confirmation_used(
    db: Session,
    context: ConsoleAuthContext,
    confirmation: ConsoleConfirmation,
    *,
    action: str,
    target_type: str,
    target_id: UUID,
    outcome: str = "success",
) -> None:
    if confirmation.used_at:
        return
    now = datetime.now(timezone.utc)
    confirmation.used_at = now
    record_audit_event(
        db,
        actor=context.agent,
        event_type="confirmation_used",
        entity_type="confirmation",
        entity_id=confirmation.id,
        payload={
            "action": action,
            "target_type": target_type,
            "target_id": str(target_id),
            "outcome": outcome,
        },
        client_id=confirmation.client_id,
        branch_id=confirmation.branch_id,
    )


def _record_confirmation_failure(
    db: Session,
    context: ConsoleAuthContext,
    confirmation_id: UUID,
    action: str,
    target_type: str,
    target_id: UUID,
    reason: str,
) -> None:
    record_audit_event(
        db,
        actor=context.agent,
        event_type="confirmation_failed",
        entity_type="confirmation",
        entity_id=confirmation_id,
        payload={
            "action": action,
            "target_type": target_type,
            "target_id": str(target_id),
            "reason": reason,
        },
        client_id=context.client.id,
        branch_id=context.effective_branch_id,
    )
    db.commit()
