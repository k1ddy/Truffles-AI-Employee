from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import ClientSettings, Conversation, Handover, User
from app.services.alert_service import alert_error
from app.services.telegram_service import TelegramService, build_handover_buttons, format_handover_message

logger = get_logger("escalation_service")


def get_telegram_credentials(db: Session, client_id: UUID) -> Tuple[Optional[str], Optional[str]]:
    """Get Telegram bot_token and chat_id for client."""
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client_id).first()

    if settings and settings.telegram_bot_token and settings.telegram_chat_id:
        return settings.telegram_bot_token, settings.telegram_chat_id

    return None, None


def create_handover(
    db: Session,
    conversation: Conversation,
    user: User,
    trigger_type: str,
    trigger_value: Optional[str] = None,
    user_message: Optional[str] = None,
) -> Handover:
    """Create handover record in database."""
    now = datetime.now(timezone.utc)

    handover = Handover(
        conversation_id=conversation.id,
        client_id=conversation.client_id,
        trigger_type=trigger_type,
        trigger_value=trigger_value,
        status="pending",
        user_message=user_message,
        created_at=now,
        adapter_type="telegram",
        channel="telegram",
    )
    db.add(handover)
    db.flush()  # Get ID before commit

    return handover


def get_or_create_topic(
    db: Session,
    telegram: TelegramService,
    chat_id: str,
    conversation: Conversation,
    user: User,
) -> Optional[int]:
    """Get existing topic or create new one. Returns topic_id."""
    # Check if topic already exists
    if conversation.telegram_topic_id:
        return conversation.telegram_topic_id

    # Create topic name: "77015705555 Жанбол [Truffles]"
    phone = user.phone or "Unknown"
    name = user.name or "Клиент"
    topic_name = f"{phone} {name}"

    # Create topic
    topic_id = telegram.create_forum_topic(chat_id, topic_name)

    if topic_id:
        # Save to conversation
        conversation.telegram_topic_id = topic_id
        db.flush()
        logger.info(f"Created topic {topic_id} for conversation {conversation.id}")
    else:
        logger.warning(f"Failed to create topic for conversation {conversation.id}")

    return topic_id


def send_telegram_notification(
    db: Session,
    handover: Handover,
    conversation: Conversation,
    user: User,
    message: str,
) -> bool:
    """Send handover notification to Telegram topic with buttons and pin."""
    bot_token, chat_id = get_telegram_credentials(db, handover.client_id)

    if not bot_token or not chat_id:
        logger.warning(f"No Telegram credentials for client {handover.client_id}")
        return False

    telegram = TelegramService(bot_token)

    # 1. Get or create topic
    topic_id = get_or_create_topic(db, telegram, chat_id, conversation, user)

    # 2. Format message
    text = format_handover_message(
        user_name=user.name,
        user_phone=user.phone,
        message=message,
        trigger_type=handover.trigger_value or handover.trigger_type,
    )

    # 3. Build buttons
    buttons = build_handover_buttons(handover.id)

    # 4. Send message to topic
    result = telegram.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=buttons,
        message_thread_id=topic_id,
    )

    # 4.1 If topic not found - reset and create new
    if not result.get("ok"):
        error_desc = result.get("description", "")
        if "thread not found" in error_desc.lower() or "message_thread_id" in error_desc.lower():
            logger.warning(f"Topic {topic_id} not found, creating new one...")
            # Reset topic_id
            conversation.telegram_topic_id = None
            db.flush()
            # Create new topic
            topic_id = get_or_create_topic(db, telegram, chat_id, conversation, user)
            if topic_id:
                # Retry send
                result = telegram.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=buttons,
                    message_thread_id=topic_id,
                )

    if result.get("ok"):
        message_id = result["result"]["message_id"]

        # 5. Save telegram_message_id and channel_ref
        handover.telegram_message_id = message_id
        handover.channel_ref = str(topic_id) if topic_id else None
        handover.notified_at = datetime.now(timezone.utc)

        # 6. Pin message
        telegram.pin_message(chat_id, message_id)

        logger.info(f"Sent to Telegram: topic={topic_id}, message_id={message_id}")
        return True
    else:
        logger.error(f"Telegram send error: {result}")
        alert_error("Telegram notification failed", {"handover_id": str(handover.id), "result": str(result)})
        return False


def escalate_conversation(
    db: Session,
    conversation: Conversation,
    user: User,
    trigger_type: str,
    trigger_value: Optional[str] = None,
    user_message: Optional[str] = None,
) -> Tuple[Handover, bool]:
    """
    Full escalation flow:
    1. Create handover in DB
    2. Send Telegram notification with buttons
    3. Pin message

    Returns: (handover, telegram_sent)
    """
    # 1. Create handover
    handover = create_handover(
        db=db,
        conversation=conversation,
        user=user,
        trigger_type=trigger_type,
        trigger_value=trigger_value,
        user_message=user_message,
    )

    # 2. Send to Telegram (with topic)
    telegram_sent = send_telegram_notification(
        db=db,
        handover=handover,
        conversation=conversation,
        user=user,
        message=user_message or "",
    )

    return handover, telegram_sent
