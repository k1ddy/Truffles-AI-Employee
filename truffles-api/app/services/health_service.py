import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Branch, Conversation, Handover, OutboxMessage, User
from app.services.knowledge_registry_service import get_current_published
from app.services.knowledge_validation import (
    MINIMUM_DATA_CONTRACT_VERSION,
    evaluate_minimum_data_contract,
)
from app.services.runtime_safety import build_runtime_safety_snapshot
from app.services.state_machine import ConversationState
from app.services.state_service import force_state

logger = get_logger("health_service")
_OUTBOX_ARCHIVE_REASON_PREFIX = "archived_pending:"
_OUTBOX_CALENDAR_SYNC_REASON_PREFIX = "calendar_sync_failed:"
_OUTBOX_SYSTEM_EVENT_TYPES = ("calendar.sync_inbound", "calendar.sync_outbound")


def _int_env(name: str, default: int, minimum: int = 0) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        return default
    return max(value, minimum)


def _coerce_int(value, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _outbox_actionable_failure_filter():
    event_type = OutboxMessage.payload_json["event_type"].astext
    return and_(
        or_(
            OutboxMessage.last_error.is_(None),
            ~OutboxMessage.last_error.ilike(f"{_OUTBOX_ARCHIVE_REASON_PREFIX}%"),
        ),
        or_(
            OutboxMessage.last_error.is_(None),
            ~OutboxMessage.last_error.ilike(f"{_OUTBOX_CALENDAR_SYNC_REASON_PREFIX}%"),
        ),
        or_(
            event_type.is_(None),
            ~event_type.in_(_OUTBOX_SYSTEM_EVENT_TYPES),
        ),
    )


def build_outbox_health_snapshot(db: Session, *, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    counts_rows = (
        db.query(
            OutboxMessage.status,
            func.count(OutboxMessage.id).label("count"),
        )
        .filter(OutboxMessage.status.in_(["PENDING", "FAILED"]))
        .group_by(OutboxMessage.status)
        .all()
    )

    pending = 0
    failed_total = 0
    for status_value, count in counts_rows:
        normalized = str(status_value or "").upper()
        if normalized == "PENDING":
            pending = int(count or 0)
        elif normalized == "FAILED":
            failed_total = int(count or 0)

    failed_24h = (
        db.query(func.count(OutboxMessage.id))
        .filter(
            OutboxMessage.status == "FAILED",
            OutboxMessage.created_at >= cutoff,
            _outbox_actionable_failure_filter(),
        )
        .scalar()
        or 0
    )
    failed_24h = int(failed_24h)

    pending_warning = _int_env("OUTBOX_HEALTH_PENDING_WARNING", 500, minimum=0)
    pending_critical = _int_env("OUTBOX_HEALTH_PENDING_CRITICAL", 1000, minimum=pending_warning)
    failed_warning = _int_env("OUTBOX_HEALTH_FAILED_24H_WARNING", 30, minimum=0)
    failed_critical = _int_env("OUTBOX_HEALTH_FAILED_24H_CRITICAL", 100, minimum=failed_warning)

    status = "healthy"
    if pending >= pending_critical or failed_24h >= failed_critical:
        status = "critical"
    elif pending >= pending_warning or failed_24h >= failed_warning:
        status = "warning"

    return {
        "status": status,
        "pending": pending,
        # Keep legacy key stable for existing consumers.
        "failed": failed_total,
        "failed_total": failed_total,
        "failed_24h": failed_24h,
        "metric_basis": "failed_24h_non_archived",
        "thresholds": {
            "pending_warning": pending_warning,
            "pending_critical": pending_critical,
            "failed_24h_warning": failed_warning,
            "failed_24h_critical": failed_critical,
        },
    }


def _append_decision_trace(context: dict, payload: dict) -> dict:
    trace = context.get("decision_trace")
    trace_list = trace if isinstance(trace, list) else []
    trace_list.append(payload)
    context["decision_trace"] = trace_list
    return context


def is_probably_whatsapp_jid(value: str | None) -> bool:
    if not value:
        return False
    # We only need to distinguish between real WhatsApp JIDs and broken numeric topic_ids.
    # WhatsApp identifiers always contain "@" (e.g. 7701...@s.whatsapp.net, ...@lid).
    return "@" in value


def check_and_heal_conversations(db: Session) -> dict:
    """Проверить инварианты и починить нарушения."""
    healed = []

    # Инвариант 1: manager_active/pending без topic_id → сбросить на bot_active
    broken_no_topic = (
        db.query(Conversation)
        .filter(
            Conversation.state.in_([ConversationState.MANAGER_ACTIVE.value, ConversationState.PENDING.value]),
            Conversation.telegram_topic_id == None,  # noqa: E711
        )
        .all()
    )

    for conv in broken_no_topic:
        user = db.query(User).filter(User.id == conv.user_id).first()
        if user and user.telegram_topic_id:
            conv.telegram_topic_id = user.telegram_topic_id
            healed.append(
                {
                    "conversation_id": str(conv.id),
                    "issue": f"{conv.state}_no_topic",
                    "action": "restored_topic_from_user",
                }
            )
            logger.warning(f"Restored topic for conversation {conv.id} from user {user.id}")
            continue

        old_state = conv.state
        transition = force_state(conv, ConversationState.BOT_ACTIVE, reason="heal_no_topic")
        conv.retry_offered_at = None

        open_handovers = (
            db.query(Handover)
            .filter(
                Handover.conversation_id == conv.id,
                Handover.status.in_(["pending", "active"]),
            )
            .all()
        )

        for h in open_handovers:
            h.status = "resolved"
            h.resolved_at = datetime.now(timezone.utc)
            h.resolution_notes = f"Auto-healed: {old_state} without topic"

        healed.append(
            {
                "conversation_id": str(conv.id),
                "issue": f"{old_state}_no_topic",
                "action": "reset_to_bot_active",
            }
        )
        context = conv.context if isinstance(conv.context, dict) else {}
        context = _append_decision_trace(
            context,
            {
                "stage": "state_transition",
                "decision": "forced",
                "reason": "heal_no_topic",
                "meta": {
                    "from": transition["from_state"],
                    "to": transition["to_state"],
                    "violations": transition["violations"],
                },
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        conv.context = context
        logger.warning(f"Healed conversation {conv.id}: {old_state} without topic")

    # Инвариант 2: pending/manager_active без активного handover → сбросить
    conversations_with_state = (
        db.query(Conversation)
        .filter(
            Conversation.state.in_([ConversationState.MANAGER_ACTIVE.value, ConversationState.PENDING.value]),
        )
        .all()
    )

    for conv in conversations_with_state:
        active_handover = (
            db.query(Handover)
            .filter(
                Handover.conversation_id == conv.id,
                Handover.status.in_(["pending", "active"]),
            )
            .first()
        )

        if not active_handover:
            old_state = conv.state
            transition = force_state(conv, ConversationState.BOT_ACTIVE, reason="heal_no_handover")
            conv.retry_offered_at = None
            healed.append(
                {
                    "conversation_id": str(conv.id),
                    "issue": f"{old_state}_no_handover",
                    "action": "reset_to_bot_active",
                }
            )
            context = conv.context if isinstance(conv.context, dict) else {}
            context = _append_decision_trace(
                context,
                {
                    "stage": "state_transition",
                    "decision": "forced",
                    "reason": "heal_no_handover",
                    "meta": {
                        "from": transition["from_state"],
                        "to": transition["to_state"],
                        "violations": transition["violations"],
                    },
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            conv.context = context
            logger.warning(f"Healed conversation {conv.id}: {old_state} without active handover")

    # Инвариант 3: pending/active handovers должны указывать на того же WhatsApp пользователя,
    # что и conversation.user.remote_jid (иначе менеджер может ответить не тому клиенту).
    broken_handover_refs = (
        db.query(Handover, Conversation, User)
        .join(Conversation, Conversation.id == Handover.conversation_id)
        .join(User, User.id == Conversation.user_id)
        .filter(
            Handover.status.in_(["pending", "active"]),
            Conversation.channel == "whatsapp",
        )
        .all()
    )

    for handover, conversation, user in broken_handover_refs:
        desired_ref = user.remote_jid
        if not is_probably_whatsapp_jid(desired_ref):
            continue

        old_ref = handover.channel_ref
        if old_ref == desired_ref:
            continue

        if not is_probably_whatsapp_jid(old_ref):
            issue = "handover_invalid_channel_ref"
        else:
            issue = "handover_mismatched_channel_ref"

        handover.channel_ref = desired_ref
        healed.append(
            {
                "handover_id": str(handover.id),
                "conversation_id": str(conversation.id),
                "issue": issue,
                "action": f"set_channel_ref_to_user_remote_jid (old='{old_ref}')",
            }
        )
        logger.warning(f"Healed handover {handover.id}: channel_ref='{old_ref}' -> '{desired_ref}'")

    db.commit()

    return {
        "healed_count": len(healed),
        "details": healed,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def build_minimum_data_status(db: Session) -> dict:
    branches = (
        db.query(Branch)
        .filter(Branch.is_active.is_(True))
        .all()
    )
    missing_branches: list[dict] = []
    ready_count = 0

    for branch in branches:
        published = get_current_published(db, branch_id=branch.id)
        if not published or not isinstance(published.payload_json, dict):
            missing_fields = ["knowledge_published"]
        else:
            status = evaluate_minimum_data_contract(published.payload_json)
            missing_fields = status.missing_fields

        if missing_fields:
            missing_branches.append(
                {
                    "branch_id": str(branch.id),
                    "knowledge_tag": branch.knowledge_tag,
                    "missing_fields": missing_fields,
                }
            )
        else:
            ready_count += 1

    total = len(branches)
    return {
        "version": MINIMUM_DATA_CONTRACT_VERSION,
        "branches_total": total,
        "ready_count": ready_count,
        "missing_count": total - ready_count,
        "missing": missing_branches,
    }


def get_system_health(db: Session) -> dict:
    """Получить общее состояние системы."""

    bot_active = db.query(Conversation).filter(Conversation.state == ConversationState.BOT_ACTIVE.value).count()

    pending = db.query(Conversation).filter(Conversation.state == ConversationState.PENDING.value).count()

    manager_active = db.query(Conversation).filter(Conversation.state == ConversationState.MANAGER_ACTIVE.value).count()

    pending_handovers = db.query(Handover).filter(Handover.status == "pending").count()

    active_handovers = db.query(Handover).filter(Handover.status == "active").count()
    safety_snapshot = build_runtime_safety_snapshot()

    return {
        "conversations": {
            "bot_active": bot_active,
            "pending": pending,
            "manager_active": manager_active,
        },
        "handovers": {
            "pending": pending_handovers,
            "active": active_handovers,
        },
        "safety": safety_snapshot.to_dict(),
        "minimum_data_contract": build_minimum_data_status(db),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def check_and_alert_health(checks: dict) -> list[str]:
    """Check health results and log alerts for critical issues.
    
    Returns list of alert messages sent.
    Currently just logs warnings, can be extended to send Telegram/email alerts.
    """
    alerts_sent = []
    
    # Check database
    db_status = checks.get("database", {})
    if db_status.get("status") == "unhealthy":
        msg = f"Database unhealthy: {db_status.get('error', 'unknown')}"
        logger.error(msg)
        alerts_sent.append(msg)
    
    # Check Qdrant
    qdrant_status = checks.get("qdrant", {})
    if qdrant_status.get("status") == "unhealthy":
        msg = f"Qdrant unhealthy: {qdrant_status.get('error', 'unknown')}"
        logger.warning(msg)
        # Don't add to alerts_sent - Qdrant is optional
    
    # Check outbox
    outbox_status = checks.get("outbox", {})
    if not isinstance(outbox_status, dict):
        outbox_status = {}
    pending = _coerce_int(outbox_status.get("pending"), 0)
    failed_total = _coerce_int(outbox_status.get("failed_total", outbox_status.get("failed")), 0)
    failed_24h = _coerce_int(outbox_status.get("failed_24h", outbox_status.get("failed")), 0)
    thresholds = outbox_status.get("thresholds", {})
    if not isinstance(thresholds, dict):
        thresholds = {}
    pending_warning = _coerce_int(thresholds.get("pending_warning"), 500)
    pending_critical = _coerce_int(thresholds.get("pending_critical"), 1000)
    failed_warning = _coerce_int(thresholds.get("failed_24h_warning"), 50)
    failed_critical = _coerce_int(thresholds.get("failed_24h_critical"), 100)

    is_critical = pending >= pending_critical or failed_24h >= failed_critical
    is_warning = pending >= pending_warning or failed_24h >= failed_warning
    if is_critical:
        msg = (
            "Outbox critical: "
            f"pending={pending}, failed_24h={failed_24h}, failed_total={failed_total}"
        )
        logger.error(msg)
        alerts_sent.append(msg)
    elif is_warning:
        msg = (
            "Outbox warning: "
            f"pending={pending}, failed_24h={failed_24h}, failed_total={failed_total}"
        )
        logger.warning(msg)
    
    return alerts_sent
