from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models import (
    Conversation,
    ConversationHumanLock,
    MarketingCampaign,
    MarketingCampaignDelivery,
    MarketingCampaignRecipient,
    MarketingConsent,
    MarketingDeliveryEvent,
    MarketingSuppression,
    OutboxMessage,
    User,
)
from app.models.appointment import Appointment
from app.services.health_service import build_outbox_health_snapshot
from app.services.provider_error_policy import classify_provider_error

MARKETING_SEGMENT_REACTIVATION_30_120 = "reactivation_30_120"
MARKETING_SEGMENT_NO_SHOW_RECOVERY_14D = "no_show_recovery_14d"
MARKETING_SEGMENT_ENGAGED_NO_BOOKING_7D = "engaged_no_booking_7d"
MARKETING_SEGMENT_CODES = {
    MARKETING_SEGMENT_REACTIVATION_30_120,
    MARKETING_SEGMENT_NO_SHOW_RECOVERY_14D,
    MARKETING_SEGMENT_ENGAGED_NO_BOOKING_7D,
}

MARKETING_STATUS_DRAFT = "draft"
MARKETING_STATUS_IN_REVIEW = "in_review"
MARKETING_STATUS_APPROVED = "approved"
MARKETING_STATUS_SCHEDULED = "scheduled"
MARKETING_STATUS_RUNNING = "running"
MARKETING_STATUS_PAUSED = "paused"
MARKETING_STATUS_COMPLETED = "completed"
MARKETING_STATUS_CANCELLED = "cancelled"
MARKETING_STATUS_FAILED = "failed"
MARKETING_STATUS_VALUES = {
    MARKETING_STATUS_DRAFT,
    MARKETING_STATUS_IN_REVIEW,
    MARKETING_STATUS_APPROVED,
    MARKETING_STATUS_SCHEDULED,
    MARKETING_STATUS_RUNNING,
    MARKETING_STATUS_PAUSED,
    MARKETING_STATUS_COMPLETED,
    MARKETING_STATUS_CANCELLED,
    MARKETING_STATUS_FAILED,
    # Backward-compat statuses from Wave 3.
    "ready",
    "executed",
}

MARKETING_FREQUENCY_CAP_DAYS = 7
MARKETING_PERMANENT_FAILURE_LOOKBACK_DAYS = 90

_CANCELLED_APPOINTMENT_STATUSES = {"CANCELLED", "CANCELED", "cancelled", "canceled"}
_NO_SHOW_APPOINTMENT_STATUSES = {"NO_SHOW", "no_show"}
_TRANSITIONS: dict[str, set[str]] = {
    MARKETING_STATUS_DRAFT: {MARKETING_STATUS_IN_REVIEW, MARKETING_STATUS_CANCELLED},
    "ready": {MARKETING_STATUS_IN_REVIEW, MARKETING_STATUS_APPROVED, MARKETING_STATUS_CANCELLED},
    MARKETING_STATUS_IN_REVIEW: {MARKETING_STATUS_DRAFT, MARKETING_STATUS_APPROVED, MARKETING_STATUS_CANCELLED},
    MARKETING_STATUS_APPROVED: {
        MARKETING_STATUS_SCHEDULED,
        MARKETING_STATUS_RUNNING,
        MARKETING_STATUS_PAUSED,
        MARKETING_STATUS_CANCELLED,
    },
    MARKETING_STATUS_SCHEDULED: {MARKETING_STATUS_RUNNING, MARKETING_STATUS_PAUSED, MARKETING_STATUS_CANCELLED},
    MARKETING_STATUS_RUNNING: {
        MARKETING_STATUS_COMPLETED,
        MARKETING_STATUS_PAUSED,
        MARKETING_STATUS_FAILED,
        MARKETING_STATUS_CANCELLED,
    },
    "executed": {
        MARKETING_STATUS_RUNNING,
        MARKETING_STATUS_PAUSED,
        MARKETING_STATUS_COMPLETED,
        MARKETING_STATUS_FAILED,
        MARKETING_STATUS_CANCELLED,
    },
    MARKETING_STATUS_PAUSED: {
        MARKETING_STATUS_APPROVED,
        MARKETING_STATUS_SCHEDULED,
        MARKETING_STATUS_RUNNING,
        MARKETING_STATUS_CANCELLED,
    },
}


def check_marketing_transition(current_status: str, target_status: str) -> bool:
    if current_status == target_status:
        return True
    allowed = _TRANSITIONS.get(current_status)
    if not allowed:
        return False
    return target_status in allowed


def _normalize_jid(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _is_cancelled_appointment_status(value: Optional[str]) -> bool:
    return (value or "").strip() in _CANCELLED_APPOINTMENT_STATUSES


def _days_since(when: Optional[datetime], *, now: datetime) -> Optional[int]:
    if not when:
        return None
    delta = now - when
    return max(int(delta.total_seconds() // 86400), 0)


def _load_candidate_conversations(
    db: Session,
    *,
    client_id: UUID,
    branch_id: UUID,
) -> list[dict[str, Any]]:
    rows = (
        db.query(
            Conversation.id.label("conversation_id"),
            Conversation.user_id.label("user_id"),
            Conversation.last_message_at.label("last_message_at"),
            User.remote_jid.label("recipient_jid"),
        )
        .join(User, User.id == Conversation.user_id)
        .filter(
            Conversation.client_id == client_id,
            Conversation.branch_id == branch_id,
            Conversation.channel == "whatsapp",
            User.remote_jid.isnot(None),
            func.length(func.trim(User.remote_jid)) > 0,
        )
        .order_by(Conversation.last_message_at.desc().nullslast(), Conversation.id.desc())
        .all()
    )
    by_jid: dict[str, dict[str, Any]] = {}
    for row in rows:
        normalized_jid = _normalize_jid(row.recipient_jid)
        if not normalized_jid or normalized_jid in by_jid:
            continue
        by_jid[normalized_jid] = {
            "recipient_jid": row.recipient_jid,
            "user_id": row.user_id,
            "conversation_id": row.conversation_id,
            "last_message_at": row.last_message_at,
        }
    return list(by_jid.values())


def _load_appointment_stats(
    db: Session,
    *,
    client_id: UUID,
    branch_id: UUID,
    user_ids: set[UUID],
    now: datetime,
) -> dict[UUID, dict[str, Any]]:
    if not user_ids:
        return {}

    stats: dict[UUID, dict[str, Any]] = {
        user_id: {"last_visit_at": None, "future_count": 0, "no_show_14d_count": 0}
        for user_id in user_ids
    }
    base_query = db.query(Appointment).filter(
        Appointment.client_id == client_id,
        Appointment.branch_id == branch_id,
        Appointment.user_id.in_(user_ids),
    )

    past_rows = (
        db.query(
            Appointment.user_id,
            func.max(Appointment.start_at).label("last_visit_at"),
        )
        .filter(
            Appointment.client_id == client_id,
            Appointment.branch_id == branch_id,
            Appointment.user_id.in_(user_ids),
            Appointment.start_at <= now,
            ~Appointment.status.in_(_CANCELLED_APPOINTMENT_STATUSES),
        )
        .group_by(Appointment.user_id)
        .all()
    )
    for row in past_rows:
        if row.user_id in stats:
            stats[row.user_id]["last_visit_at"] = row.last_visit_at

    future_rows = (
        db.query(
            Appointment.user_id,
            func.count(Appointment.id).label("future_count"),
        )
        .filter(
            Appointment.client_id == client_id,
            Appointment.branch_id == branch_id,
            Appointment.user_id.in_(user_ids),
            Appointment.start_at > now,
            ~Appointment.status.in_(_CANCELLED_APPOINTMENT_STATUSES),
        )
        .group_by(Appointment.user_id)
        .all()
    )
    for row in future_rows:
        if row.user_id in stats:
            stats[row.user_id]["future_count"] = int(row.future_count or 0)

    no_show_cutoff = now - timedelta(days=14)
    no_show_rows = (
        db.query(
            Appointment.user_id,
            func.count(Appointment.id).label("no_show_count"),
        )
        .filter(
            Appointment.client_id == client_id,
            Appointment.branch_id == branch_id,
            Appointment.user_id.in_(user_ids),
            Appointment.start_at >= no_show_cutoff,
            Appointment.status.in_(_NO_SHOW_APPOINTMENT_STATUSES),
        )
        .group_by(Appointment.user_id)
        .all()
    )
    for row in no_show_rows:
        if row.user_id in stats:
            stats[row.user_id]["no_show_14d_count"] = int(row.no_show_count or 0)

    return stats


def _matches_segment(
    *,
    segment_code: str,
    candidate: dict[str, Any],
    stats: dict[str, Any],
    now: datetime,
) -> tuple[bool, list[str]]:
    last_visit_at = stats.get("last_visit_at")
    future_count = int(stats.get("future_count") or 0)
    no_show_14d_count = int(stats.get("no_show_14d_count") or 0)
    last_message_at = candidate.get("last_message_at")
    days_since_last_visit = _days_since(last_visit_at, now=now)
    reason_codes: list[str] = []

    if segment_code == MARKETING_SEGMENT_REACTIVATION_30_120:
        if days_since_last_visit is None:
            return False, []
        if days_since_last_visit < 30 or days_since_last_visit > 120:
            return False, []
        if future_count > 0:
            return False, []
        reason_codes.extend(
            [
                "segment=reactivation_30_120",
                f"last_visit_days={days_since_last_visit}",
                "no_future_booking=true",
            ]
        )
        return True, reason_codes

    if segment_code == MARKETING_SEGMENT_NO_SHOW_RECOVERY_14D:
        if no_show_14d_count <= 0:
            return False, []
        if future_count > 0:
            return False, []
        reason_codes.extend(
            [
                "segment=no_show_recovery_14d",
                f"no_show_14d_count={no_show_14d_count}",
                "no_future_booking=true",
            ]
        )
        return True, reason_codes

    if segment_code == MARKETING_SEGMENT_ENGAGED_NO_BOOKING_7D:
        if not isinstance(last_message_at, datetime):
            return False, []
        if last_message_at < now - timedelta(days=7):
            return False, []
        if future_count > 0:
            return False, []
        days_since_message = _days_since(last_message_at, now=now) or 0
        reason_codes.extend(
            [
                "segment=engaged_no_booking_7d",
                f"last_message_days={days_since_message}",
                "no_future_booking=true",
            ]
        )
        return True, reason_codes

    return False, []


def _load_latest_consent_map(
    db: Session,
    *,
    client_id: UUID,
    recipient_jids: Iterable[str],
) -> dict[str, str]:
    normalized = {_normalize_jid(value) for value in recipient_jids if _normalize_jid(value)}
    if not normalized:
        return {}
    rows = (
        db.query(MarketingConsent)
        .filter(
            MarketingConsent.client_id == client_id,
            MarketingConsent.active.is_(True),
            MarketingConsent.recipient_jid.in_(normalized),
        )
        .order_by(MarketingConsent.changed_at.desc(), MarketingConsent.id.desc())
        .all()
    )
    resolved: dict[str, str] = {}
    for row in rows:
        jid = _normalize_jid(row.recipient_jid)
        if jid and jid not in resolved:
            resolved[jid] = (row.status or "").strip()
    return resolved


def _load_active_suppressions(
    db: Session,
    *,
    client_id: UUID,
    recipient_jids: Iterable[str],
    now: datetime,
) -> dict[str, list[str]]:
    normalized = {_normalize_jid(value) for value in recipient_jids if _normalize_jid(value)}
    if not normalized:
        return {}
    rows = (
        db.query(MarketingSuppression)
        .filter(
            MarketingSuppression.client_id == client_id,
            MarketingSuppression.active.is_(True),
            MarketingSuppression.recipient_jid.in_(normalized),
            or_(MarketingSuppression.expires_at.is_(None), MarketingSuppression.expires_at > now),
        )
        .all()
    )
    mapped: dict[str, list[str]] = {}
    for row in rows:
        jid = _normalize_jid(row.recipient_jid)
        if not jid:
            continue
        mapped.setdefault(jid, []).append(f"suppression:{row.reason}")
    return mapped


def _load_active_human_locks(
    db: Session,
    *,
    client_id: UUID,
    recipient_jids: Iterable[str],
    now: datetime,
) -> set[str]:
    normalized = {_normalize_jid(value) for value in recipient_jids if _normalize_jid(value)}
    if not normalized:
        return set()
    rows = (
        db.query(ConversationHumanLock.remote_jid)
        .filter(
            ConversationHumanLock.client_id == client_id,
            ConversationHumanLock.remote_jid.in_(normalized),
            ConversationHumanLock.lock_until > now,
        )
        .all()
    )
    return {_normalize_jid(row[0]) for row in rows if row and row[0]}


def _load_recent_marketing_touch_jids(
    db: Session,
    *,
    client_id: UUID,
    recipient_jids: Iterable[str],
    now: datetime,
) -> set[str]:
    normalized = {_normalize_jid(value) for value in recipient_jids if _normalize_jid(value)}
    if not normalized:
        return set()
    cutoff = now - timedelta(days=MARKETING_FREQUENCY_CAP_DAYS)
    rows = (
        db.query(User.remote_jid)
        .join(Conversation, Conversation.user_id == User.id)
        .join(OutboxMessage, OutboxMessage.conversation_id == Conversation.id)
        .filter(
            Conversation.client_id == client_id,
            OutboxMessage.client_id == client_id,
            OutboxMessage.created_at >= cutoff,
            OutboxMessage.meta["source"].astext == "marketing_campaign",
            User.remote_jid.in_(normalized),
        )
        .all()
    )
    return {_normalize_jid(row[0]) for row in rows if row and row[0]}


def _load_permanent_failure_jids(
    db: Session,
    *,
    client_id: UUID,
    recipient_jids: Iterable[str],
    now: datetime,
) -> set[str]:
    normalized = {_normalize_jid(value) for value in recipient_jids if _normalize_jid(value)}
    if not normalized:
        return set()
    cutoff = now - timedelta(days=MARKETING_PERMANENT_FAILURE_LOOKBACK_DAYS)
    rows = (
        db.query(User.remote_jid, OutboxMessage.last_error)
        .join(Conversation, Conversation.user_id == User.id)
        .join(OutboxMessage, OutboxMessage.conversation_id == Conversation.id)
        .filter(
            Conversation.client_id == client_id,
            OutboxMessage.client_id == client_id,
            OutboxMessage.status == "FAILED",
            OutboxMessage.created_at >= cutoff,
            User.remote_jid.in_(normalized),
        )
        .all()
    )
    permanent: set[str] = set()
    for jid, last_error in rows:
        normalized_jid = _normalize_jid(jid)
        if not normalized_jid:
            continue
        classification = classify_provider_error(last_error)
        if not classification.retryable:
            permanent.add(normalized_jid)
    return permanent


def _resolve_suppression_reasons(
    *,
    consent_status: Optional[str],
    explicit_suppressions: list[str],
    human_lock: bool,
    frequency_cap_hit: bool,
    permanent_failure: bool,
) -> list[str]:
    reasons: list[str] = []
    if (consent_status or "").strip() == "opt_out":
        reasons.append("consent:opt_out")
    reasons.extend(explicit_suppressions)
    if human_lock:
        reasons.append("state:human_lock_active")
    if frequency_cap_hit:
        reasons.append(f"frequency_cap:{MARKETING_FREQUENCY_CAP_DAYS}d")
    if permanent_failure:
        reasons.append("provider:permanent_failure_history")
    return reasons


def materialize_marketing_campaign_audience(
    db: Session,
    *,
    campaign: MarketingCampaign,
    segment_code: str,
    sample_limit: int,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if segment_code not in MARKETING_SEGMENT_CODES:
        raise ValueError("unsupported_segment")

    candidates = _load_candidate_conversations(
        db,
        client_id=campaign.client_id,
        branch_id=campaign.branch_id,
    )
    user_ids = {candidate["user_id"] for candidate in candidates if candidate.get("user_id")}
    stats_by_user = _load_appointment_stats(
        db,
        client_id=campaign.client_id,
        branch_id=campaign.branch_id,
        user_ids=user_ids,
        now=now,
    )

    selected: list[dict[str, Any]] = []
    for candidate in candidates:
        user_id = candidate.get("user_id")
        stats = stats_by_user.get(user_id, {"last_visit_at": None, "future_count": 0, "no_show_14d_count": 0})
        matches, reason_codes = _matches_segment(
            segment_code=segment_code,
            candidate=candidate,
            stats=stats,
            now=now,
        )
        if not matches:
            continue
        selected.append(
            {
                **candidate,
                "reason_codes": reason_codes,
            }
        )

    recipient_jids = [item["recipient_jid"] for item in selected]
    consent_by_jid = _load_latest_consent_map(
        db,
        client_id=campaign.client_id,
        recipient_jids=recipient_jids,
    )
    suppressions_by_jid = _load_active_suppressions(
        db,
        client_id=campaign.client_id,
        recipient_jids=recipient_jids,
        now=now,
    )
    human_lock_jids = _load_active_human_locks(
        db,
        client_id=campaign.client_id,
        recipient_jids=recipient_jids,
        now=now,
    )
    frequency_cap_jids = _load_recent_marketing_touch_jids(
        db,
        client_id=campaign.client_id,
        recipient_jids=recipient_jids,
        now=now,
    )
    permanent_failure_jids = _load_permanent_failure_jids(
        db,
        client_id=campaign.client_id,
        recipient_jids=recipient_jids,
        now=now,
    )

    db.query(MarketingCampaignRecipient).filter(MarketingCampaignRecipient.campaign_id == campaign.id).delete()

    suppressed_count = 0
    for item in selected:
        normalized_jid = _normalize_jid(item["recipient_jid"])
        suppression_reasons = _resolve_suppression_reasons(
            consent_status=consent_by_jid.get(normalized_jid),
            explicit_suppressions=suppressions_by_jid.get(normalized_jid, []),
            human_lock=normalized_jid in human_lock_jids,
            frequency_cap_hit=normalized_jid in frequency_cap_jids,
            permanent_failure=normalized_jid in permanent_failure_jids,
        )
        suppressed = len(suppression_reasons) > 0
        if suppressed:
            suppressed_count += 1
        db.add(
            MarketingCampaignRecipient(
                campaign_id=campaign.id,
                client_id=campaign.client_id,
                branch_id=campaign.branch_id,
                user_id=item.get("user_id"),
                conversation_id=item.get("conversation_id"),
                recipient_jid=item["recipient_jid"],
                segment_code=segment_code,
                reason_codes=item["reason_codes"],
                suppressed=suppressed,
                suppression_reasons=suppression_reasons,
                created_at=now,
                updated_at=now,
            )
        )

    campaign.segment_code = segment_code
    campaign.preview_total = len(selected)
    campaign.last_preview_at = now
    campaign.preflight_valid = False
    campaign.preflight_snapshot = {
        "generated_at": now.isoformat(),
        "reason": "preview_refresh_required_before_execute",
        "eligible_count": max(len(selected) - suppressed_count, 0),
        "suppressed_count": suppressed_count,
    }
    campaign.updated_at = now
    db.add(campaign)
    db.flush()

    preview_rows = (
        db.query(MarketingCampaignRecipient)
        .filter(MarketingCampaignRecipient.campaign_id == campaign.id)
        .order_by(MarketingCampaignRecipient.suppressed.asc(), MarketingCampaignRecipient.created_at.desc())
        .limit(max(sample_limit, 1))
        .all()
    )

    return {
        "estimated_recipients": len(selected),
        "eligible_count": max(len(selected) - suppressed_count, 0),
        "suppressed_count": suppressed_count,
        "sample_conversation_ids": [
            row.conversation_id
            for row in preview_rows
            if row.conversation_id
        ],
        "sample_recipient_jids": [
            row.recipient_jid
            for row in preview_rows
            if row.recipient_jid
        ],
    }


def fetch_marketing_audience_preview(
    db: Session,
    *,
    campaign_id: UUID,
    include_suppressed: bool,
    limit: int,
) -> list[MarketingCampaignRecipient]:
    query = db.query(MarketingCampaignRecipient).filter(MarketingCampaignRecipient.campaign_id == campaign_id)
    if not include_suppressed:
        query = query.filter(MarketingCampaignRecipient.suppressed.is_(False))
    return (
        query.order_by(
            MarketingCampaignRecipient.suppressed.asc(),
            MarketingCampaignRecipient.updated_at.desc(),
            MarketingCampaignRecipient.id.desc(),
        )
        .limit(max(limit, 1))
        .all()
    )


def build_marketing_campaign_preflight(
    db: Session,
    *,
    campaign: MarketingCampaign,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    total_count = (
        db.query(func.count(MarketingCampaignRecipient.id))
        .filter(MarketingCampaignRecipient.campaign_id == campaign.id)
        .scalar()
        or 0
    )
    suppressed_count = (
        db.query(func.count(MarketingCampaignRecipient.id))
        .filter(
            MarketingCampaignRecipient.campaign_id == campaign.id,
            MarketingCampaignRecipient.suppressed.is_(True),
        )
        .scalar()
        or 0
    )
    eligible_count = max(int(total_count) - int(suppressed_count), 0)

    outbox_snapshot = build_outbox_health_snapshot(db, now=now)
    runtime_blocked = outbox_snapshot.get("status") == "critical"
    approval_ok = campaign.status in {MARKETING_STATUS_APPROVED, MARKETING_STATUS_SCHEDULED}
    preview_ok = int(total_count) > 0
    eligible_ok = eligible_count > 0

    blocked_reasons: list[str] = []
    if runtime_blocked:
        blocked_reasons.append("runtime_health_critical")
    if not approval_ok:
        blocked_reasons.append("campaign_not_approved")
    if not preview_ok:
        blocked_reasons.append("audience_snapshot_missing")
    if not eligible_ok:
        blocked_reasons.append("eligible_recipients_empty")

    preflight_valid = len(blocked_reasons) == 0
    snapshot = {
        "generated_at": now.isoformat(),
        "campaign_id": str(campaign.id),
        "outbox_health": outbox_snapshot,
        "audience_total": int(total_count),
        "suppressed_count": int(suppressed_count),
        "eligible_count": int(eligible_count),
        "approval_ok": approval_ok,
        "preview_ok": preview_ok,
        "runtime_blocked": runtime_blocked,
        "blocked_reasons": blocked_reasons,
        "preflight_valid": preflight_valid,
    }
    campaign.preflight_snapshot = snapshot
    campaign.preflight_valid = preflight_valid
    campaign.updated_at = now
    db.add(campaign)
    db.flush()
    return snapshot


def mark_campaign_under_review(campaign: MarketingCampaign, *, now: Optional[datetime] = None) -> None:
    now = now or datetime.now(timezone.utc)
    if not check_marketing_transition(campaign.status, MARKETING_STATUS_IN_REVIEW):
        raise ValueError("invalid_transition_to_in_review")
    campaign.status = MARKETING_STATUS_IN_REVIEW
    campaign.requested_review_at = now
    campaign.updated_at = now


def mark_campaign_approved(campaign: MarketingCampaign, *, approved_by: UUID, now: Optional[datetime] = None) -> None:
    now = now or datetime.now(timezone.utc)
    if not check_marketing_transition(campaign.status, MARKETING_STATUS_APPROVED):
        raise ValueError("invalid_transition_to_approved")
    campaign.status = MARKETING_STATUS_APPROVED
    campaign.approved_by = approved_by
    campaign.approved_at = now
    campaign.updated_at = now


def mark_campaign_paused(campaign: MarketingCampaign, *, now: Optional[datetime] = None) -> None:
    now = now or datetime.now(timezone.utc)
    if not check_marketing_transition(campaign.status, MARKETING_STATUS_PAUSED):
        raise ValueError("invalid_transition_to_paused")
    campaign.status = MARKETING_STATUS_PAUSED
    campaign.updated_at = now


def mark_campaign_resume(campaign: MarketingCampaign, *, now: Optional[datetime] = None) -> None:
    now = now or datetime.now(timezone.utc)
    if not check_marketing_transition(campaign.status, MARKETING_STATUS_APPROVED):
        raise ValueError("invalid_transition_to_approved")
    campaign.status = MARKETING_STATUS_APPROVED
    campaign.updated_at = now


def run_marketing_campaign_execute(
    db: Session,
    *,
    campaign: MarketingCampaign,
    message_text: str,
    max_recipients: Optional[int],
    now: Optional[datetime] = None,
) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    preflight = build_marketing_campaign_preflight(db, campaign=campaign, now=now)
    if not preflight.get("preflight_valid"):
        raise ValueError("preflight_failed")

    recipients_query = db.query(MarketingCampaignRecipient).filter(
        MarketingCampaignRecipient.campaign_id == campaign.id,
        MarketingCampaignRecipient.suppressed.is_(False),
    )
    recipients_query = recipients_query.order_by(
        MarketingCampaignRecipient.updated_at.desc(),
        MarketingCampaignRecipient.id.desc(),
    )
    if max_recipients is not None:
        recipients_query = recipients_query.limit(max_recipients)
    recipients = recipients_query.all()

    existing_jids = {
        _normalize_jid(row.recipient_jid)
        for row in db.query(MarketingCampaignDelivery.recipient_jid)
        .filter(
            MarketingCampaignDelivery.campaign_id == campaign.id,
            MarketingCampaignDelivery.recipient_jid.isnot(None),
        )
        .all()
        if row and row.recipient_jid
    }

    queued_count = 0
    skipped_count = 0
    for recipient in recipients:
        normalized_jid = _normalize_jid(recipient.recipient_jid)
        if not normalized_jid or normalized_jid in existing_jids:
            skipped_count += 1
            continue

        synthetic_inbound_id = f"marketing:{campaign.id}:{normalized_jid}"
        outbox_item = OutboxMessage(
            client_id=campaign.client_id,
            conversation_id=recipient.conversation_id,
            branch_id=campaign.branch_id,
            inbound_message_id=synthetic_inbound_id,
            payload_json={"text": message_text},
            meta={
                "source": "marketing_campaign",
                "campaign_id": str(campaign.id),
                "campaign_name": campaign.name,
                "segment_code": campaign.segment_code,
                "audience_mode": campaign.audience_mode,
            },
            status="PENDING",
            attempts=0,
            next_attempt_at=None,
            last_error=None,
            created_at=now,
            updated_at=now,
        )
        db.add(outbox_item)
        db.flush()

        delivery = MarketingCampaignDelivery(
            campaign_id=campaign.id,
            client_id=campaign.client_id,
            branch_id=campaign.branch_id,
            conversation_id=recipient.conversation_id,
            user_id=recipient.user_id,
            recipient_jid=recipient.recipient_jid,
            status="queued",
            outbox_id=outbox_item.id,
            error_reason=None,
            created_at=now,
            updated_at=now,
        )
        db.add(delivery)
        db.flush()

        db.add(
            MarketingDeliveryEvent(
                campaign_id=campaign.id,
                delivery_id=delivery.id,
                outbox_id=outbox_item.id,
                client_id=campaign.client_id,
                branch_id=campaign.branch_id,
                recipient_jid=recipient.recipient_jid,
                event_type="queued",
                payload={"reason": "campaign_execute"},
                created_at=now,
            )
        )
        queued_count += 1
        existing_jids.add(normalized_jid)

    if queued_count > 0:
        campaign.status = MARKETING_STATUS_RUNNING
        campaign.executed_at = now
        campaign.run_started_at = campaign.run_started_at or now
    campaign.updated_at = now
    db.add(campaign)
    db.flush()
    return {
        "queued_count": queued_count,
        "skipped_count": skipped_count,
    }


def retry_failed_marketing_deliveries(
    db: Session,
    *,
    campaign: MarketingCampaign,
    limit: int,
    now: Optional[datetime] = None,
) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    failed_query = (
        db.query(MarketingCampaignDelivery, OutboxMessage)
        .join(OutboxMessage, OutboxMessage.id == MarketingCampaignDelivery.outbox_id)
        .filter(
            MarketingCampaignDelivery.campaign_id == campaign.id,
            OutboxMessage.status == "FAILED",
        )
    )
    total_failed = int(failed_query.count() or 0)
    rows = (
        failed_query.order_by(
            OutboxMessage.updated_at.desc().nullslast(),
            OutboxMessage.id.desc(),
        )
        .limit(max(limit, 1))
        .all()
    )

    retried_count = 0
    skipped_permanent = 0
    for delivery, outbox_row in rows:
        classification = classify_provider_error(outbox_row.last_error)
        if not classification.retryable:
            skipped_permanent += 1
            db.add(
                MarketingDeliveryEvent(
                    campaign_id=campaign.id,
                    delivery_id=delivery.id,
                    outbox_id=outbox_row.id,
                    client_id=campaign.client_id,
                    branch_id=campaign.branch_id,
                    recipient_jid=delivery.recipient_jid,
                    event_type="retry_skipped_permanent",
                    payload={
                        "provider_kind": classification.kind,
                        "reason_code": classification.incident_reason_code,
                    },
                    created_at=now,
                )
            )
            continue

        outbox_row.status = "PENDING"
        outbox_row.next_attempt_at = None
        outbox_row.last_error = None
        outbox_row.updated_at = now
        delivery.status = "queued"
        delivery.error_reason = None
        delivery.updated_at = now
        retried_count += 1
        db.add(
            MarketingDeliveryEvent(
                campaign_id=campaign.id,
                delivery_id=delivery.id,
                outbox_id=outbox_row.id,
                client_id=campaign.client_id,
                branch_id=campaign.branch_id,
                recipient_jid=delivery.recipient_jid,
                event_type="retry_queued",
                payload={"reason": "retry_failed"},
                created_at=now,
            )
        )

    skipped_count = max(total_failed - retried_count, 0)
    campaign.updated_at = now
    db.add(campaign)
    db.flush()
    return {
        "retried_count": retried_count,
        "skipped_count": skipped_count,
        "skipped_permanent": skipped_permanent,
    }
