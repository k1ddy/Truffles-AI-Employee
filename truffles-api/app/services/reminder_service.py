import os
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import ClientSettings, Conversation, Handover, Message
from app.schemas.reminder import ReminderItem
from app.services.alert_service import alert_warning
from app.services.state_machine import ConversationState
from app.services.telegram_service import TelegramService

logger = get_logger("reminder_service")


def _get_no_response_threshold_minutes() -> int:
    try:
        return int(float(os.environ.get("NO_RESPONSE_ALERT_MINUTES", "3")))
    except ValueError:
        return 3


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
            conversation.state = ConversationState.BOT_ACTIVE.value
            conversation.bot_muted_until = None
            conversation.no_count = 0
            conversation.retry_offered_at = None
            conversation.context = {}

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

        context = conversation.context if isinstance(conversation.context, dict) else {}
        alerts = context.get("alerts") if isinstance(context.get("alerts"), dict) else {}
        if alerts.get("no_response_for") == str(last_user.id):
            continue

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
            },
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

    results["auto_close"] = auto_close_stale_handovers(db)
    results["no_response_alerts"] = check_no_response_alerts(db)
    return results
