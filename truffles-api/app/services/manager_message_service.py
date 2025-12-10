from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional, Tuple

from app.models import Conversation, Handover, User, ClientSettings
from app.services.message_service import save_message
from app.services.chatflow_service import send_bot_response
from app.services.telegram_service import TelegramService


def find_conversation_by_telegram(
    db: Session,
    chat_id: int,
    message_thread_id: Optional[int] = None,
) -> Optional[Tuple[Conversation, Handover]]:
    """
    Find conversation by Telegram chat_id and optional topic_id.
    
    Strategy:
    1. If message_thread_id exists - find handover by telegram_message_id in that thread
    2. Otherwise find by chat_id in client_settings + active handover
    """
    # Find client by telegram_chat_id
    settings = db.query(ClientSettings).filter(
        ClientSettings.telegram_chat_id == str(chat_id)
    ).first()
    
    if not settings:
        print(f"No client found for telegram chat_id={chat_id}")
        return None
    
    # Find active handover for this client
    handover = db.query(Handover).filter(
        Handover.client_id == settings.client_id,
        Handover.status.in_(["pending", "active"]),
    ).order_by(Handover.created_at.desc()).first()
    
    if not handover:
        print(f"No active handover for client {settings.client_id}")
        return None
    
    conversation = db.query(Conversation).filter(
        Conversation.id == handover.conversation_id
    ).first()
    
    if not conversation:
        print(f"Conversation not found for handover {handover.id}")
        return None
    
    return conversation, handover


def get_user_remote_jid(db: Session, user_id: UUID) -> Optional[str]:
    """Get user's WhatsApp remote_jid."""
    user = db.query(User).filter(User.id == user_id).first()
    return user.remote_jid if user else None


def process_manager_message(
    db: Session,
    chat_id: int,
    message_text: str,
    manager_telegram_id: int,
    manager_name: str,
    message_thread_id: Optional[int] = None,
) -> Tuple[bool, str, bool, Optional[Handover]]:
    """
    Process message from manager in Telegram and forward to client.
    
    Returns: (success, message, took_handover, handover)
    """
    # 1. Find conversation
    result = find_conversation_by_telegram(db, chat_id, message_thread_id)
    if not result:
        return False, "No active conversation found for this chat", False, None
    
    conversation, handover = result
    
    # 2. Update handover status if pending (auto-take when manager writes)
    took_handover = False
    if handover.status == "pending":
        handover.status = "active"
        handover.first_response_at = datetime.now(timezone.utc)
        handover.assigned_to = str(manager_telegram_id)
        handover.assigned_to_name = manager_name
        took_handover = True
        
        # Update conversation state
        conversation.state = "manager_active"
    
    # 3. Save manager message
    save_message(
        db=db,
        conversation_id=conversation.id,
        client_id=conversation.client_id,
        role="manager",
        content=message_text,
    )
    
    # Update handover with manager response
    handover.manager_response = message_text
    
    # 4. Get user's WhatsApp JID
    remote_jid = get_user_remote_jid(db, conversation.user_id)
    if not remote_jid:
        return False, "User remote_jid not found", took_handover, handover
    
    # 5. Send to WhatsApp
    sent = send_bot_response(
        db=db,
        client_id=conversation.client_id,
        remote_jid=remote_jid,
        message=message_text,
    )
    
    if sent:
        return True, f"Message forwarded to client (conversation {conversation.id})", took_handover, handover
    else:
        return False, "Failed to send message to WhatsApp", took_handover, handover
