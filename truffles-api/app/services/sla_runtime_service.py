from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Client, Conversation
from app.services.capabilities_runtime import build_runtime_capabilities
from app.services.sla_profile_registry_service import (
    resolve_effective_profile_payload,
    resolve_effective_profile_version,
)

SLA_RUNTIME_CONTEXT_KEY = "sla_runtime"
SLA_RUNTIME_MODE_COLLECT_ONLY = "collect_only"

SlaSeverity = Literal["none", "warning", "breach", "severe_breach"]
SlaAction = Literal["none", "notify_manager", "escalate", "collect_only"]


@dataclass(frozen=True)
class SlaPendingViolationDecision:
    severity: SlaSeverity
    action: SlaAction
    reason_code: str
    elapsed_minutes: int
    threshold_minutes: int | None
    profile_id: UUID | None
    profile_version: int | None
    profile_scope: str | None
    domain_key: str | None


def _ensure_timezone(value: datetime | None) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _parse_iso_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return _ensure_timezone(parsed)


def _resolve_scope_inputs(
    db: Session,
    *,
    conversation: Conversation,
) -> tuple[UUID | None, str | None]:
    client = (
        db.query(Client)
        .filter(Client.id == conversation.client_id)
        .first()
    )
    company_id = getattr(client, "company_id", None) if client else None
    runtime_capabilities = build_runtime_capabilities(
        db,
        client_id=conversation.client_id,
        branch_id=conversation.branch_id,
    )
    domain_key = runtime_capabilities.payload.domain_slug if runtime_capabilities else None
    return company_id, domain_key


def resolve_pending_sla_violation(
    db: Session,
    *,
    conversation: Conversation,
    now: datetime | None = None,
) -> SlaPendingViolationDecision | None:
    escalated_at = _ensure_timezone(conversation.escalated_at)
    if escalated_at is None:
        return None

    now_utc = _ensure_timezone(now) or datetime.now(timezone.utc)
    elapsed_minutes = max(0, int((now_utc - escalated_at).total_seconds() // 60))

    company_id, domain_key = _resolve_scope_inputs(db, conversation=conversation)
    payload = resolve_effective_profile_payload(
        db,
        company_id=company_id,
        domain_key=domain_key,
        client_id=conversation.client_id,
        branch_id=conversation.branch_id,
    )
    if payload is None:
        return None

    version = resolve_effective_profile_version(
        db,
        company_id=company_id,
        domain_key=domain_key,
        client_id=conversation.client_id,
        branch_id=conversation.branch_id,
    )

    warning_threshold = max(1, int(payload.thresholds.first_response_minutes))
    breach_threshold = max(warning_threshold, int(payload.thresholds.handoff_ack_minutes))
    severe_threshold = max(breach_threshold, int(payload.thresholds.resolution_minutes))

    severity: SlaSeverity = "none"
    threshold_minutes: int | None = None
    if elapsed_minutes >= severe_threshold:
        severity = "severe_breach"
        threshold_minutes = severe_threshold
    elif elapsed_minutes >= breach_threshold:
        severity = "breach"
        threshold_minutes = breach_threshold
    elif elapsed_minutes >= warning_threshold:
        severity = "warning"
        threshold_minutes = warning_threshold

    action_map: dict[SlaSeverity, SlaAction] = {
        "none": "none",
        "warning": payload.actions.warning,  # type: ignore[assignment]
        "breach": payload.actions.breach,  # type: ignore[assignment]
        "severe_breach": payload.actions.severe_breach,  # type: ignore[assignment]
    }
    action = action_map.get(severity, "none")
    reason_code = (
        "sla_within_threshold"
        if severity == "none"
        else f"sla_{severity}_{action}"
    )

    return SlaPendingViolationDecision(
        severity=severity,
        action=action,
        reason_code=reason_code,
        elapsed_minutes=elapsed_minutes,
        threshold_minutes=threshold_minutes,
        profile_id=version.id if version else None,
        profile_version=version.version_number if version else None,
        profile_scope=version.scope if version else None,
        domain_key=domain_key,
    )


def resolve_first_response_threshold_minutes(
    db: Session,
    *,
    conversation: Conversation,
    default_minutes: int,
) -> int:
    company_id, domain_key = _resolve_scope_inputs(db, conversation=conversation)
    payload = resolve_effective_profile_payload(
        db,
        company_id=company_id,
        domain_key=domain_key,
        client_id=conversation.client_id,
        branch_id=conversation.branch_id,
    )
    if payload is None:
        return max(1, int(default_minutes))
    return max(1, int(payload.thresholds.first_response_minutes))


def build_collect_only_runtime_context(
    *,
    decision: SlaPendingViolationDecision,
    now: datetime,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "mode": SLA_RUNTIME_MODE_COLLECT_ONLY,
        "reason_code": decision.reason_code,
        "severity": decision.severity,
        "set_at": now.isoformat(),
        "elapsed_minutes": decision.elapsed_minutes,
        "threshold_minutes": decision.threshold_minutes,
    }
    if decision.profile_id is not None:
        payload["profile_id"] = str(decision.profile_id)
    if decision.profile_version is not None:
        payload["profile_version"] = decision.profile_version
    if decision.profile_scope:
        payload["profile_scope"] = decision.profile_scope
    if decision.domain_key:
        payload["domain_key"] = decision.domain_key
    return payload


def is_collect_only_runtime_active(context: dict, *, now: datetime | None = None) -> bool:
    if not isinstance(context, dict):
        return False
    runtime = context.get(SLA_RUNTIME_CONTEXT_KEY)
    if not isinstance(runtime, dict):
        return False
    mode = runtime.get("mode")
    if mode != SLA_RUNTIME_MODE_COLLECT_ONLY:
        return False
    now_utc = _ensure_timezone(now) or datetime.now(timezone.utc)
    expires_at = _parse_iso_datetime(runtime.get("expires_at"))
    if expires_at and now_utc >= expires_at:
        return False
    return True


__all__ = [
    "SLA_RUNTIME_CONTEXT_KEY",
    "SLA_RUNTIME_MODE_COLLECT_ONLY",
    "SlaPendingViolationDecision",
    "build_collect_only_runtime_context",
    "is_collect_only_runtime_active",
    "resolve_first_response_threshold_minutes",
    "resolve_pending_sla_violation",
]
