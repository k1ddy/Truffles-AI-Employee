from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import ClientSettings, Conversation, Handover, User
from app.services.chatflow_service import send_bot_response
from app.services.learning_service import add_to_knowledge, is_owner_response
from app.services.message_service import save_message

logger = get_logger("manager_message_service")

def is_probably_whatsapp_jid(value: Optional[str]) -> bool:
    if not value:
        return False
    return "@" in value


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
    settings = db.query(ClientSettings).filter(ClientSettings.telegram_chat_id == str(chat_id)).first()

    if not settings:
        logger.warning(f"No client found for telegram chat_id={chat_id}")
        return None

    # Preferred strategy: topic-based routing (avoid cross-client mix-ups)
    if message_thread_id:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.client_id == settings.client_id,
                Conversation.telegram_topic_id == message_thread_id,
            )
            .first()
        )

        if not conversation:
            logger.warning(
                f"No conversation found for client={settings.client_id}, topic_id={message_thread_id}"
            )
            return None

        handover = (
            db.query(Handover)
            .filter(
                Handover.conversation_id == conversation.id,
                Handover.status.in_(["pending", "active"]),
            )
            .order_by(Handover.created_at.desc())
            .first()
        )

        if not handover:
            logger.warning(f"No active handover for conversation {conversation.id} in topic {message_thread_id}")
            return None

        return conversation, handover

    # Fallback strategy (no topic): pick latest active handover for this client
    handover = (
        db.query(Handover)
        .filter(
            Handover.client_id == settings.client_id,
            Handover.status.in_(["pending", "active"]),
        )
        .order_by(Handover.created_at.desc())
        .first()
    )

    if not handover:
        logger.debug(f"No active handover for client {settings.client_id}")
        return None

    conversation = db.query(Conversation).filter(Conversation.id == handover.conversation_id).first()

    if not conversation:
        logger.warning(f"Conversation not found for handover {handover.id}")
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
    manager_username: Optional[str] = None,
    message_thread_id: Optional[int] = None,
) -> Tuple[bool, str, bool, Optional[Handover]]:
    """
    Process message from manager in Telegram and forward to client.

    Returns: (success, message, took_handover, handover)
    """
    logger.info(f"process_manager_message: chat_id={chat_id}, manager={manager_telegram_id}, thread={message_thread_id}")

    # 1. Find conversation
    result = find_conversation_by_telegram(db, chat_id, message_thread_id)
    if not result:
        logger.warning(f"No conversation found for chat_id={chat_id}, thread={message_thread_id}")
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

    # Auto-learn from owner responses
    if is_owner_response(db, handover.client_id, manager_telegram_id, manager_username):
        logger.info("Owner response detected, auto-adding to knowledge base")
        point_id = add_to_knowledge(db, handover, source="owner")
        if point_id:
            logger.info(f"Successfully added to knowledge: {point_id}")

    # 4. Get user's WhatsApp JID (authoritative source: user.remote_jid)
    user_remote_jid = get_user_remote_jid(db, conversation.user_id)
    remote_jid = user_remote_jid

    # Fallback for legacy/broken data
    if not is_probably_whatsapp_jid(remote_jid):
        remote_jid = handover.channel_ref if is_probably_whatsapp_jid(handover.channel_ref) else None

    # Self-heal mismatch: never trust channel_ref if it points to another WhatsApp JID
    if is_probably_whatsapp_jid(user_remote_jid) and handover.channel_ref != user_remote_jid:
        if is_probably_whatsapp_jid(handover.channel_ref):
            logger.warning(
                "handover.channel_ref mismatch: "
                f"'{handover.channel_ref}' != user.remote_jid '{user_remote_jid}', fixing"
            )
        handover.channel_ref = user_remote_jid

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
