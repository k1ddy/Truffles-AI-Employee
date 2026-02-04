import os
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import AlertEvent, ClientSettings, Conversation, Handover, Message, User
from app.schemas.reminder import ReminderItem
from app.services.alert_service import alert_warning
from app.services.chatflow_service import send_bot_response
from app.services.message_service import save_message
from app.services.state_machine import ConversationState
from app.services.state_service import force_state, manager_resolve
from app.services.telegram_service import TelegramService

logger = get_logger("reminder_service")

PENDING_SLA_PING_MINUTES = int(os.environ.get("PENDING_SLA_PING_MINUTES", "15"))
PENDING_AUTO_CLOSE_HOURS = int(os.environ.get("PENDING_AUTO_CLOSE_HOURS", "4"))
PENDING_SLA_CONTEXT_KEY = "pending_sla"
PENDING_SLA_PING_SENT_KEY = "ping_sent_at"
PENDING_SLA_AUTO_CLOSE_KEY = "auto_closed_at"
DECISION_TRACE_KEY = "decision_trace"

MSG_PENDING_SLA_PING = "Напоминаю: менеджер ещё не подключился. Я на связи — напишите, что нужно уточнить."
MSG_PENDING_AUTO_CLOSE = "Закрываю ожидание. Если всё ещё актуально — напишите, я помогу."


def _get_no_response_threshold_minutes() -> int:
    try:
        return int(float(os.environ.get("NO_RESPONSE_ALERT_MINUTES", "3")))
    except ValueError:
        return 3


def _get_no_response_max_age_days() -> int:
    try:
        return int(float(os.environ.get("NO_RESPONSE_ALERT_MAX_AGE_DAYS", "30")))
    except ValueError:
        return 30


def _ensure_timezone(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _get_last_message(db: Session, conversation_id, role: str) -> Message | None:
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id, Message.role == role)
        .order_by(Message.created_at.desc())
        .first()
    )


def _get_pending_sla_context(conversation: Conversation) -> tuple[dict, dict]:
    raw_context = conversation.context if isinstance(conversation.context, dict) else {}
    context = dict(raw_context)
    payload = raw_context.get(PENDING_SLA_CONTEXT_KEY)
    pending_sla = dict(payload) if isinstance(payload, dict) else {}
    return context, pending_sla


def _append_decision_trace(context: dict, payload: dict) -> dict:
    trace = context.get("decision_trace")
    trace_list = trace if isinstance(trace, list) else []
    trace_list.append(payload)
    context["decision_trace"] = trace_list
    return context


def _reset_context_preserving_trace(conversation: Conversation) -> dict:
    existing = conversation.context if isinstance(conversation.context, dict) else {}
    if DECISION_TRACE_KEY in existing:
        preserved = {DECISION_TRACE_KEY: existing.get(DECISION_TRACE_KEY)}
    else:
        preserved = {}
    conversation.context = preserved
    return preserved


def _send_pending_user_message(
    db: Session,
    conversation: Conversation,
    *,
    text: str,
    decision_meta: dict,
) -> bool:
    user = db.query(User).filter(User.id == conversation.user_id).first()
    remote_jid = user.remote_jid if user else None
    if not remote_jid:
        return False
    ok = send_bot_response(
        db,
        conversation.client_id,
        remote_jid,
        text,
        branch_id=conversation.branch_id,
    )
    save_message(
        db,
        conversation_id=conversation.id,
        client_id=conversation.client_id,
        role="assistant",
        content=text,
        message_metadata={"decision_meta": decision_meta, "source": "reminder"},
    )
    conversation.last_message_at = datetime.now(timezone.utc)
    return ok


def process_pending_sla(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    results = {"pinged": 0, "auto_closed": 0, "items": []}

    open_handovers = db.query(Handover).filter(Handover.status.in_(["pending", "active"])).all()

    for handover in open_handovers:
        conversation = handover.conversation
        if not conversation or conversation.state != ConversationState.PENDING.value:
            continue

        escalated_at = conversation.escalated_at or handover.created_at
        if escalated_at and escalated_at.tzinfo is None:
            escalated_at = escalated_at.replace(tzinfo=timezone.utc)
        if not escalated_at:
            continue

        context, pending_sla = _get_pending_sla_context(conversation)
        auto_closed_at = pending_sla.get(PENDING_SLA_AUTO_CLOSE_KEY)
        ping_sent_at = pending_sla.get(PENDING_SLA_PING_SENT_KEY)

        auto_close_due = now - escalated_at >= timedelta(hours=PENDING_AUTO_CLOSE_HOURS)
        ping_due = now - escalated_at >= timedelta(minutes=PENDING_SLA_PING_MINUTES)

        if auto_close_due and not auto_closed_at:
            _send_pending_user_message(
                db,
                conversation,
                text=MSG_PENDING_AUTO_CLOSE,
                decision_meta={"pending_action": "auto_close"},
            )
            pending_sla[PENDING_SLA_AUTO_CLOSE_KEY] = now.isoformat()
            manager_resolve(db, conversation, handover, manager_id="system", manager_name="system")
            conversation.bot_status = "muted"
            conversation.bot_muted_until = None
            results["auto_closed"] += 1
            results["items"].append(
                {
                    "handover_id": str(handover.id),
                    "conversation_id": str(conversation.id),
                    "action": "auto_close",
                }
            )
            continue

        if ping_due and not ping_sent_at:
            _send_pending_user_message(
                db,
                conversation,
                text=MSG_PENDING_SLA_PING,
                decision_meta={"pending_sla_ping": True, "pending_action": "pending_sla_ping"},
            )
            pending_sla[PENDING_SLA_PING_SENT_KEY] = now.isoformat()
            context = _append_decision_trace(
                context,
                {
                    "stage": "pending_sla",
                    "decision": "ping",
                    "recorded_at": now.isoformat(),
                },
            )
            context[PENDING_SLA_CONTEXT_KEY] = pending_sla
            conversation.context = context
            results["pinged"] += 1
            results["items"].append(
                {
                    "handover_id": str(handover.id),
                    "conversation_id": str(conversation.id),
                    "action": "ping",
                }
            )

    return results


def auto_close_stale_handovers(db: Session) -> dict:
    """Auto-close stale handovers based on client_settings.auto_close_timeout."""
    now = datetime.now(timezone.utc)
    closed = []

    open_handovers = db.query(Handover).filter(Handover.status.in_(["pending", "active"])).all()

    for handover in open_handovers:
        settings = db.query(ClientSettings).filter(ClientSettings.client_id == handover.client_id).first()
        timeout_minutes = settings.auto_close_timeout if settings and settings.auto_close_timeout else 0
        if timeout_minutes <= 0:
            continue

        created_at = _ensure_timezone(handover.created_at)
        minutes_waiting = int((now - created_at).total_seconds() / 60)
        if minutes_waiting < timeout_minutes:
            continue

        handover.status = "resolved"
        handover.resolved_at = now
        handover.resolved_by_id = "system"
        handover.resolved_by_name = "system"
        handover.resolution_notes = f"Auto-closed after {minutes_waiting} min"
        if handover.created_at:
            handover.resolution_time_seconds = int((now - created_at).total_seconds())

        conversation = handover.conversation
        if conversation:
            transition = force_state(conversation, ConversationState.BOT_ACTIVE, reason="auto_close")
            conversation.bot_muted_until = None
            conversation.no_count = 0
            conversation.retry_offered_at = None
            context = _reset_context_preserving_trace(conversation)
            context = _append_decision_trace(
                context,
                {
                    "stage": "state_transition",
                    "decision": "forced",
                    "reason": "auto_close",
                    "meta": {
                        "from": transition["from_state"],
                        "to": transition["to_state"],
                        "violations": transition["violations"],
                    },
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            conversation.context = context

        closed.append(
            {
                "handover_id": str(handover.id),
                "conversation_id": str(handover.conversation_id),
                "minutes_waiting": minutes_waiting,
            }
        )

    if closed:
        logger.warning(f"Auto-closed handovers: {len(closed)}")

    return {"closed": len(closed), "items": closed}


def check_no_response_alerts(db: Session) -> dict:
    """Alert if user message waits too long without bot response in bot_active."""
    now = datetime.now(timezone.utc)
    threshold_minutes = _get_no_response_threshold_minutes()
    max_age_days = _get_no_response_max_age_days()
    alerted = []

    conversations = db.query(Conversation).filter(Conversation.state == ConversationState.BOT_ACTIVE.value).all()

    for conversation in conversations:
        if conversation.bot_status == "muted" or (
            conversation.bot_muted_until and conversation.bot_muted_until > now
        ):
            continue

        last_user = _get_last_message(db, conversation.id, "user")
        if not last_user:
            continue

        last_assistant = _get_last_message(db, conversation.id, "assistant")
        last_user_at = _ensure_timezone(last_user.created_at)
        if last_assistant and _ensure_timezone(last_assistant.created_at) >= last_user_at:
            continue

        minutes_waiting = int((now - last_user_at).total_seconds() / 60)
        if minutes_waiting < threshold_minutes:
            continue
        if max_age_days > 0 and now - last_user_at > timedelta(days=max_age_days):
            continue

        message_metadata = last_user.message_metadata if isinstance(last_user.message_metadata, dict) else {}
        inbound_message_id = message_metadata.get("messageId") or message_metadata.get("message_id")
        remote_jid = message_metadata.get("remoteJid") or message_metadata.get("remote_jid")
        if not inbound_message_id or not remote_jid:
            continue

        base_context = conversation.context if isinstance(conversation.context, dict) else {}
        decision_meta = message_metadata.get("decision_meta") or {}
        last_action = None
        if isinstance(decision_meta, dict):
            action = decision_meta.get("action")
            intent = decision_meta.get("intent")
            if action and intent:
                last_action = f"{action}:{intent}"
            else:
                last_action = action or intent

        trace = base_context.get("decision_trace")
        last_trace = trace[-1] if isinstance(trace, list) and trace else None
        if (isinstance(decision_meta, dict) and decision_meta.get("action") == "shield_drop") or (
            isinstance(last_trace, dict)
            and last_trace.get("stage") == "shield"
            and last_trace.get("decision") == "drop"
        ):
            logger.info(
                "Suppressed no_response alert due to shield_drop",
                extra={
                    "context": {
                        "conversation_id": str(conversation.id),
                        "message_id": str(last_user.id),
                    }
                },
            )
            continue

        raw_alerts = base_context.get("alerts")
        if isinstance(raw_alerts, dict) and raw_alerts.get("no_response_for") == str(last_user.id):
            continue

        context = dict(base_context)
        alerts = dict(raw_alerts) if isinstance(raw_alerts, dict) else {}
        alerts["no_response_for"] = str(last_user.id)
        alerts["no_response_at"] = now.isoformat()
        context["alerts"] = alerts
        conversation.context = context

        alert_warning(
            "No bot response for user message",
            {
                "conversation_id": str(conversation.id),
                "client_id": str(conversation.client_id),
                "minutes_waiting": minutes_waiting,
                "message": (last_user.content or "")[:200],
                "last_action": last_action or "unknown",
                "decision_trace": last_trace,
            },
        )
        db.add(
            AlertEvent(
                client_id=conversation.client_id,
                branch_id=conversation.branch_id,
                conversation_id=conversation.id,
                message_id=last_user.id,
                alert_type="no_response",
                alert_metadata={
                    "minutes_waiting": minutes_waiting,
                    "last_action": last_action or "unknown",
                },
            )
        )

        alerted.append(
            {
                "conversation_id": str(conversation.id),
                "minutes_waiting": minutes_waiting,
            }
        )

    return {"alerted": len(alerted), "items": alerted}

def get_pending_reminders(db: Session) -> List[ReminderItem]:
    """Get list of handovers that need reminders."""
    now = datetime.now(timezone.utc)
    reminders = []

    # Get all open handovers (pending + active)
    open_handovers = db.query(Handover).filter(Handover.status.in_(["pending", "active"])).all()

    for handover in open_handovers:
        topic_id = handover.conversation.telegram_topic_id if handover.conversation else None

        # Get client settings for timeouts
        settings = db.query(ClientSettings).filter(ClientSettings.client_id == handover.client_id).first()

        # Check if reminders enabled
        if settings and not settings.enable_reminders:
            continue

        timeout_1 = settings.reminder_timeout_1 if settings else 30
        timeout_2 = settings.reminder_timeout_2 if settings else 60
        telegram_chat_id = settings.telegram_chat_id if settings else None
        telegram_bot_token = settings.telegram_bot_token if settings else None
        owner_telegram_id = settings.owner_telegram_id if settings else None
        enable_owner_escalation = settings.enable_owner_escalation if settings else True

        # Calculate minutes waiting
        if handover.created_at.tzinfo is None:
            created_at = handover.created_at.replace(tzinfo=timezone.utc)
        else:
            created_at = handover.created_at

        minutes_waiting = int((now - created_at).total_seconds() / 60)

        # Check if reminder_1 needed
        if minutes_waiting >= timeout_1 and handover.reminder_1_sent_at is None:
            reminders.append(
                ReminderItem(
                    handover_id=handover.id,
                    conversation_id=handover.conversation_id,
                    client_id=handover.client_id,
                    reminder_type="reminder_1",
                    created_at=handover.created_at,
                    minutes_waiting=minutes_waiting,
                    telegram_chat_id=telegram_chat_id,
                    telegram_message_id=handover.telegram_message_id,
                    telegram_bot_token=telegram_bot_token,
                    channel_ref=str(topic_id) if topic_id else None,
                    context_summary=handover.context_summary,
                )
            )

        # Check if reminder_2 needed (only if reminder_1 was sent)
        elif (
            minutes_waiting >= timeout_2
            and handover.reminder_1_sent_at is not None
            and handover.reminder_2_sent_at is None
        ):
            reminders.append(
                ReminderItem(
                    handover_id=handover.id,
                    conversation_id=handover.conversation_id,
                    client_id=handover.client_id,
                    reminder_type="reminder_2",
                    created_at=handover.created_at,
                    minutes_waiting=minutes_waiting,
                    telegram_chat_id=telegram_chat_id,
                    telegram_message_id=handover.telegram_message_id,
                    telegram_bot_token=telegram_bot_token,
                    channel_ref=str(topic_id) if topic_id else None,
                    context_summary=handover.context_summary,
                    owner_telegram_id=owner_telegram_id if enable_owner_escalation else None,
                )
            )

    return reminders


def mark_reminder_sent(db: Session, handover_id: UUID, reminder_type: str) -> bool:
    """Mark reminder as sent."""
    handover = db.query(Handover).filter(Handover.id == handover_id).first()

    if not handover:
        return False

    now = datetime.now(timezone.utc)

    if reminder_type == "reminder_1":
        handover.reminder_1_sent_at = now
    elif reminder_type == "reminder_2":
        handover.reminder_2_sent_at = now
    else:
        return False

    return True


def process_reminders(db: Session) -> dict:
    """Process and send all pending reminders. Returns summary."""
    reminders = get_pending_reminders(db)

    results = {"total": len(reminders), "sent": 0, "failed": 0, "details": []}

    for reminder in reminders:
        if not reminder.telegram_bot_token or not reminder.telegram_chat_id:
            results["failed"] += 1
            results["details"].append(
                {"handover_id": str(reminder.handover_id), "error": "Missing telegram credentials"}
            )
            continue

        telegram = TelegramService(reminder.telegram_bot_token)
        topic_id = int(reminder.channel_ref) if reminder.channel_ref else None

        # Build message
        if reminder.reminder_type == "reminder_1":
            text = f"⏰ <b>Напоминание:</b> заявка открыта {reminder.minutes_waiting} мин"
        else:
            owner_tag = f"\n\n{reminder.owner_telegram_id}" if reminder.owner_telegram_id else ""
            text = f"🔴 <b>Срочно!</b> Заявка открыта {reminder.minutes_waiting} мин{owner_tag}"

        # Send to topic
        result = telegram.send_message(
            chat_id=reminder.telegram_chat_id,
            text=text,
            message_thread_id=topic_id,
            reply_to_message_id=reminder.telegram_message_id,
        )

        if result.get("ok"):
            message_id = result["result"]["message_id"]
            mark_reminder_sent(db, reminder.handover_id, reminder.reminder_type)
            results["sent"] += 1
            results["details"].append(
                {
                    "handover_id": str(reminder.handover_id),
                    "reminder_type": reminder.reminder_type,
                    "success": True,
                    "telegram_message_id": message_id,
                }
            )
        else:
            results["failed"] += 1
            results["details"].append(
                {
                    "handover_id": str(reminder.handover_id),
                    "error": "Failed to send telegram message",
                    "telegram_result": result,
                }
            )

    results["pending_sla"] = process_pending_sla(db)
    results["auto_close"] = auto_close_stale_handovers(db)
    results["no_response_alerts"] = check_no_response_alerts(db)
    return results
