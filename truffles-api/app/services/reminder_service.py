from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from uuid import UUID
from datetime import datetime, timezone, timedelta
from typing import List, Tuple

from app.models import Handover, ClientSettings
from app.schemas.reminder import ReminderItem


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
        
        timeout_1 = settings.reminder_timeout_1 if settings else 30
        timeout_2 = settings.reminder_timeout_2 if settings else 60
        telegram_chat_id = settings.telegram_chat_id if settings else None
        
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
                context_summary=handover.context_summary,
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
