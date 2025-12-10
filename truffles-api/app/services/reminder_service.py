from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from uuid import UUID
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional

from app.models import Handover, ClientSettings
from app.schemas.reminder import ReminderItem
from app.services.telegram_service import TelegramService


def get_pending_reminders(db: Session) -> List[ReminderItem]:
    """Get list of handovers that need reminders."""
    now = datetime.now(timezone.utc)
    reminders = []
    
    # Get all pending handovers
    pending_handovers = db.query(Handover).filter(
        Handover.status == "pending"
    ).all()
    
    for handover in pending_handovers:
        # Get client settings for timeouts
        settings = db.query(ClientSettings).filter(
            ClientSettings.client_id == handover.client_id
        ).first()
        
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
        if (minutes_waiting >= timeout_1 
            and handover.reminder_1_sent_at is None):
            reminders.append(ReminderItem(
                handover_id=handover.id,
                conversation_id=handover.conversation_id,
                client_id=handover.client_id,
                reminder_type="reminder_1",
                created_at=handover.created_at,
                minutes_waiting=minutes_waiting,
                telegram_chat_id=telegram_chat_id,
                telegram_message_id=handover.telegram_message_id,
                telegram_bot_token=telegram_bot_token,
                channel_ref=handover.channel_ref,
                context_summary=handover.context_summary,
            ))
        
        # Check if reminder_2 needed (only if reminder_1 was sent)
        elif (minutes_waiting >= timeout_2 
              and handover.reminder_1_sent_at is not None
              and handover.reminder_2_sent_at is None):
            reminders.append(ReminderItem(
                handover_id=handover.id,
                conversation_id=handover.conversation_id,
                client_id=handover.client_id,
                reminder_type="reminder_2",
                created_at=handover.created_at,
                minutes_waiting=minutes_waiting,
                telegram_chat_id=telegram_chat_id,
                telegram_message_id=handover.telegram_message_id,
                telegram_bot_token=telegram_bot_token,
                channel_ref=handover.channel_ref,
                context_summary=handover.context_summary,
                owner_telegram_id=owner_telegram_id if enable_owner_escalation else None,
            ))
    
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
    
    results = {
        "total": len(reminders),
        "sent": 0,
        "failed": 0,
        "details": []
    }
    
    for reminder in reminders:
        if not reminder.telegram_bot_token or not reminder.telegram_chat_id:
            results["failed"] += 1
            results["details"].append({
                "handover_id": str(reminder.handover_id),
                "error": "Missing telegram credentials"
            })
            continue
        
        telegram = TelegramService(reminder.telegram_bot_token)
        topic_id = int(reminder.channel_ref) if reminder.channel_ref else None
        
        # Build message
        if reminder.reminder_type == "reminder_1":
            text = f"⏰ <b>Напоминание:</b> заявка ждёт {reminder.minutes_waiting} мин"
        else:
            owner_tag = f"\n\n{reminder.owner_telegram_id}" if reminder.owner_telegram_id else ""
            text = f"🔴 <b>Срочно!</b> Заявка ждёт {reminder.minutes_waiting} мин{owner_tag}"
        
        # Send to topic
        message_id = telegram.send_message(
            chat_id=reminder.telegram_chat_id,
            text=text,
            message_thread_id=topic_id,
            reply_to_message_id=reminder.telegram_message_id,
        )
        
        if message_id:
            mark_reminder_sent(db, reminder.handover_id, reminder.reminder_type)
            results["sent"] += 1
            results["details"].append({
                "handover_id": str(reminder.handover_id),
                "reminder_type": reminder.reminder_type,
                "success": True
            })
        else:
            results["failed"] += 1
            results["details"].append({
                "handover_id": str(reminder.handover_id),
                "error": "Failed to send telegram message"
            })
    
    return results
