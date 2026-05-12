from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Branch, Client, Conversation, Message
from app.services.alert_service import alert_error, alert_warning
from app.services.audit_service import record_audit_event
from app.services.webhook_secret_service import derive_webhook_secret_from_instance

logger = get_logger("integration_guardrails")

INTEGRATION_STATE_OK = "ok"
INTEGRATION_STATE_DEGRADED = "degraded"

REASON_INVALID_WEBHOOK_SECRET = "invalid_webhook_secret"
REASON_UNKNOWN_INSTANCE_ID = "unknown_instance_id"
REASON_MISSING_INSTANCE_ID = "missing_instance_id"
REASON_INSTANCE_ID_MISMATCH = "instance_id_mismatch"
REASON_WEBHOOK_SECRET_DRIFT = "webhook_secret_drift"
REASON_NO_RECENT_INBOUND = "no_recent_inbound"
REASON_INBOUND_WITHOUT_OUTBOUND = "inbound_without_outbound"

_DEGRADE_REASONS = {
    REASON_INVALID_WEBHOOK_SECRET,
    REASON_MISSING_INSTANCE_ID,
    REASON_INSTANCE_ID_MISMATCH,
    REASON_WEBHOOK_SECRET_DRIFT,
    REASON_NO_RECENT_INBOUND,
    REASON_INBOUND_WITHOUT_OUTBOUND,
}


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_state(value: str | None) -> str:
    normalized = _clean_text(value)
    if normalized == INTEGRATION_STATE_DEGRADED:
        return INTEGRATION_STATE_DEGRADED
    return INTEGRATION_STATE_OK


def _parse_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        parsed = int(raw.strip())
    except (TypeError, ValueError):
        return default
    return max(parsed, 1)


def _parse_bool_env(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _should_hard_degrade_reason(reason: str) -> bool:
    if reason not in _DEGRADE_REASONS:
        return False
    if reason == REASON_NO_RECENT_INBOUND:
        return _parse_bool_env("INTEGRATION_WATCHDOG_NO_RECENT_INBOUND_DEGRADES", default=False)
    return True


def _extract_instance_id_from_metadata(metadata: dict | None) -> str | None:
    if not isinstance(metadata, dict):
        return None
    direct = metadata.get("instanceId") or metadata.get("instance_id")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    nested = metadata.get("metadata")
    if isinstance(nested, dict):
        nested_value = nested.get("instanceId") or nested.get("instance_id")
        if isinstance(nested_value, str) and nested_value.strip():
            return nested_value.strip()
    return None


def _set_branch_integration_state(
    db: Session,
    *,
    branch: Branch,
    state: str,
    reason: str | None,
    source: str,
    context: dict | None,
    checked_at: datetime,
) -> bool:
    desired_state = _normalize_state(state)
    desired_reason = _clean_text(reason)

    previous_state = _normalize_state(getattr(branch, "integration_state", None))
    previous_reason = _clean_text(getattr(branch, "integration_reason", None))

    changed = previous_state != desired_state or previous_reason != desired_reason

    branch.integration_state = desired_state
    branch.integration_reason = desired_reason
    branch.integration_checked_at = checked_at

    if desired_state == INTEGRATION_STATE_DEGRADED:
        if previous_state != INTEGRATION_STATE_DEGRADED or branch.integration_degraded_at is None:
            branch.integration_degraded_at = checked_at
        branch.integration_recovered_at = None
    elif previous_state == INTEGRATION_STATE_DEGRADED:
        branch.integration_recovered_at = checked_at

    if not changed:
        return False

    event_type = "integration_degraded" if desired_state == INTEGRATION_STATE_DEGRADED else "integration_recovered"
    payload = {
        "previous_state": previous_state,
        "next_state": desired_state,
        "previous_reason": previous_reason,
        "next_reason": desired_reason,
        "source": source,
        "checked_at": checked_at.isoformat(),
    }
    if isinstance(context, dict) and context:
        payload["context"] = dict(context)

    record_audit_event(
        db,
        actor_name="system:integration_guardrail",
        event_type=event_type,
        entity_type="branch",
        entity_id=branch.id,
        payload=payload,
        client_id=branch.client_id,
        branch_id=branch.id,
    )

    alert_payload = {
        "client_id": str(branch.client_id),
        "branch_id": str(branch.id),
        "branch_slug": branch.slug,
        "state": desired_state,
        "reason": desired_reason,
        "source": source,
    }
    if isinstance(context, dict) and context:
        alert_payload.update(context)

    if desired_state == INTEGRATION_STATE_DEGRADED:
        alert_error("Branch integration degraded", alert_payload)
    else:
        alert_warning("Branch integration recovered", alert_payload)

    return True


def degrade_branch_integration(
    db: Session,
    *,
    branch: Branch,
    reason: str,
    source: str,
    context: dict | None = None,
    checked_at: datetime | None = None,
) -> bool:
    when = checked_at or datetime.now(timezone.utc)
    return _set_branch_integration_state(
        db,
        branch=branch,
        state=INTEGRATION_STATE_DEGRADED,
        reason=reason,
        source=source,
        context=context,
        checked_at=when,
    )


def recover_branch_integration(
    db: Session,
    *,
    branch: Branch,
    source: str,
    context: dict | None = None,
    checked_at: datetime | None = None,
) -> bool:
    when = checked_at or datetime.now(timezone.utc)
    return _set_branch_integration_state(
        db,
        branch=branch,
        state=INTEGRATION_STATE_OK,
        reason=None,
        source=source,
        context=context,
        checked_at=when,
    )


def report_integration_incident(
    db: Session,
    *,
    client: Client,
    reason: str,
    source: str,
    branch: Branch | None = None,
    context: dict | None = None,
    commit: bool = False,
) -> bool:
    now = datetime.now(timezone.utc)
    changed = False

    payload = {
        "reason": reason,
        "source": source,
        "client_id": str(client.id),
        "client_slug": client.name,
        "recorded_at": now.isoformat(),
    }
    if branch:
        payload["branch_id"] = str(branch.id)
        payload["branch_slug"] = branch.slug
    if isinstance(context, dict) and context:
        payload.update(context)

    record_audit_event(
        db,
        actor_name="system:integration_guardrail",
        event_type="integration_incident",
        entity_type="branch" if branch else "client",
        entity_id=branch.id if branch else client.id,
        payload=payload,
        client_id=client.id,
        branch_id=branch.id if branch else None,
    )

    alert_error("Integration incident", payload)

    if branch and _should_hard_degrade_reason(reason):
        changed = degrade_branch_integration(
            db,
            branch=branch,
            reason=reason,
            source=source,
            context=context,
            checked_at=now,
        )

    if commit:
        db.commit()

    return changed


def _latest_inbound_for_branch(db: Session, *, branch_id: UUID):
    return (
        db.query(Message.created_at, Message.message_metadata)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .filter(
            Conversation.branch_id == branch_id,
            Message.role == "user",
        )
        .order_by(Message.created_at.desc())
        .first()
    )


def _latest_outbound_for_branch(db: Session, *, branch_id: UUID):
    return (
        db.query(func.max(Message.created_at))
        .join(Conversation, Conversation.id == Message.conversation_id)
        .filter(
            Conversation.branch_id == branch_id,
            Message.role.in_(["assistant", "manager", "system"]),
        )
        .scalar()
    )


def _evaluate_branch_watchdog_reason(
    db: Session,
    *,
    branch: Branch,
    now: datetime,
    stale_after_minutes: int,
    reply_timeout_minutes: int,
    auto_remediate_secret: bool,
) -> tuple[str | None, dict, bool]:
    context: dict[str, object] = {
        "branch_slug": branch.slug,
    }
    remediated = False

    branch_instance_id = _clean_text(branch.instance_id)
    if not branch_instance_id:
        context["check"] = REASON_MISSING_INSTANCE_ID
        return REASON_MISSING_INSTANCE_ID, context, remediated

    expected_secret = derive_webhook_secret_from_instance(branch_instance_id)
    current_secret = _clean_text(branch.webhook_secret)
    if current_secret != expected_secret:
        context["webhook_secret_drift"] = True
        if auto_remediate_secret:
            branch.webhook_secret = expected_secret
            branch.updated_at = now
            remediated = True
            context["webhook_secret_remediated"] = True
        else:
            context["check"] = REASON_WEBHOOK_SECRET_DRIFT
            return REASON_WEBHOOK_SECRET_DRIFT, context, remediated

    latest_inbound = _latest_inbound_for_branch(db, branch_id=branch.id)
    last_inbound_at = latest_inbound[0] if latest_inbound else None
    last_inbound_instance = _extract_instance_id_from_metadata(latest_inbound[1] if latest_inbound else None)

    if last_inbound_at:
        context["last_inbound_at"] = last_inbound_at.isoformat()
    if last_inbound_instance:
        context["last_inbound_instance_id"] = last_inbound_instance

    if last_inbound_instance and last_inbound_instance != branch_instance_id:
        context["check"] = REASON_INSTANCE_ID_MISMATCH
        context["configured_instance_id"] = branch_instance_id
        return REASON_INSTANCE_ID_MISMATCH, context, remediated

    last_outbound_at = _latest_outbound_for_branch(db, branch_id=branch.id)
    if last_outbound_at:
        context["last_outbound_at"] = last_outbound_at.isoformat()

    reply_cutoff = now - timedelta(minutes=reply_timeout_minutes)
    if (
        last_inbound_at
        and (not last_outbound_at or last_outbound_at < last_inbound_at)
        and last_inbound_at <= reply_cutoff
    ):
        context["check"] = REASON_INBOUND_WITHOUT_OUTBOUND
        context["reply_timeout_minutes"] = reply_timeout_minutes
        return REASON_INBOUND_WITHOUT_OUTBOUND, context, remediated

    stale_cutoff = now - timedelta(minutes=stale_after_minutes)
    if last_inbound_at is not None and last_inbound_at <= stale_cutoff:
        context["check"] = REASON_NO_RECENT_INBOUND
        context["stale_after_minutes"] = stale_after_minutes
        context["check_severity"] = "warning"
        context["warning_reason"] = REASON_NO_RECENT_INBOUND
        if _parse_bool_env("INTEGRATION_WATCHDOG_NO_RECENT_INBOUND_DEGRADES", default=False):
            context["check_severity"] = "degrade"
            return REASON_NO_RECENT_INBOUND, context, remediated
        return None, context, remediated

    return None, context, remediated


def run_integration_watchdog_scoped(
    db: Session,
    *,
    client_id: UUID | None = None,
    branch_ids: list[UUID] | None = None,
    dry_run: bool = False,
) -> dict:
    now = datetime.now(timezone.utc)
    stale_after_minutes = _parse_int_env("INTEGRATION_WATCHDOG_STALE_MINUTES", 120)
    reply_timeout_minutes = _parse_int_env("INTEGRATION_WATCHDOG_REPLY_TIMEOUT_MINUTES", 10)
    auto_remediate_secret = os.environ.get("INTEGRATION_WATCHDOG_AUTO_REMEDIATE_SECRET", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
    auto_remediate_secret = auto_remediate_secret and not dry_run

    query = db.query(Branch).filter(Branch.is_active.is_(True))
    if client_id is not None:
        query = query.filter(Branch.client_id == client_id)
    if branch_ids is not None:
        if not branch_ids:
            return {
                "mode": "dry_run" if dry_run else "execute",
                "checked": 0,
                "degraded": 0,
                "recovered": 0,
                "remediated": 0,
                "stale_after_minutes": stale_after_minutes,
                "reply_timeout_minutes": reply_timeout_minutes,
                "checked_at": now.isoformat(),
                "items": [],
            }
        query = query.filter(Branch.id.in_(branch_ids))

    branches = query.order_by(Branch.created_at.asc(), Branch.id.asc()).all()

    degraded = 0
    recovered = 0
    remediated = 0
    checked = 0
    items: list[dict[str, object]] = []

    for branch in branches:
        checked += 1
        previous_state = _normalize_state(getattr(branch, "integration_state", None))
        previous_reason = _clean_text(getattr(branch, "integration_reason", None))
        reason, context, was_remediated = _evaluate_branch_watchdog_reason(
            db,
            branch=branch,
            now=now,
            stale_after_minutes=stale_after_minutes,
            reply_timeout_minutes=reply_timeout_minutes,
            auto_remediate_secret=auto_remediate_secret,
        )
        next_state = INTEGRATION_STATE_DEGRADED if reason else INTEGRATION_STATE_OK
        next_reason = reason if reason else None
        would_change = previous_state != next_state or previous_reason != next_reason

        if dry_run:
            if would_change:
                if next_state == INTEGRATION_STATE_DEGRADED:
                    degraded += 1
                else:
                    recovered += 1
            items.append(
                {
                    "branch_id": str(branch.id),
                    "branch_slug": branch.slug,
                    "previous_state": previous_state,
                    "next_state": next_state,
                    "previous_reason": previous_reason,
                    "next_reason": next_reason,
                    "would_change": would_change,
                    "context": context,
                }
            )
            continue

        if was_remediated:
            remediated += 1
            record_audit_event(
                db,
                actor_name="system:integration_guardrail",
                event_type="integration_secret_remediated",
                entity_type="branch",
                entity_id=branch.id,
                payload={
                    "source": "integration_watchdog",
                    "checked_at": now.isoformat(),
                    "reason": REASON_WEBHOOK_SECRET_DRIFT,
                },
                client_id=branch.client_id,
                branch_id=branch.id,
            )

        changed = False
        if reason:
            changed = degrade_branch_integration(
                db,
                branch=branch,
                reason=reason,
                source="integration_watchdog",
                context=context,
                checked_at=now,
            )
            if changed:
                degraded += 1
        else:
            changed = recover_branch_integration(
                db,
                branch=branch,
                source="integration_watchdog",
                context=context,
                checked_at=now,
            )
            if changed:
                recovered += 1

        items.append(
            {
                "branch_id": str(branch.id),
                "branch_slug": branch.slug,
                "previous_state": previous_state,
                "next_state": next_state,
                "previous_reason": previous_reason,
                "next_reason": next_reason,
                "changed": changed,
                "context": context,
            }
        )

    if not dry_run and (checked or degraded or recovered or remediated):
        db.commit()

    result = {
        "mode": "dry_run" if dry_run else "execute",
        "checked": checked,
        "degraded": degraded,
        "recovered": recovered,
        "remediated": remediated,
        "stale_after_minutes": stale_after_minutes,
        "reply_timeout_minutes": reply_timeout_minutes,
        "checked_at": now.isoformat(),
        "items": items,
    }
    logger.info("Integration watchdog run", extra={"context": result})
    return result


def run_integration_watchdog(db: Session) -> dict:
    return run_integration_watchdog_scoped(db, dry_run=False)


__all__ = [
    "INTEGRATION_STATE_OK",
    "INTEGRATION_STATE_DEGRADED",
    "REASON_INBOUND_WITHOUT_OUTBOUND",
    "REASON_INVALID_WEBHOOK_SECRET",
    "REASON_INSTANCE_ID_MISMATCH",
    "REASON_MISSING_INSTANCE_ID",
    "REASON_NO_RECENT_INBOUND",
    "REASON_UNKNOWN_INSTANCE_ID",
    "REASON_WEBHOOK_SECRET_DRIFT",
    "degrade_branch_integration",
    "recover_branch_integration",
    "report_integration_incident",
    "run_integration_watchdog",
    "run_integration_watchdog_scoped",
]
