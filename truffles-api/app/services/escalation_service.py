import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Branch, ClientSettings, Conversation, Handover, Message, User
from app.services.alert_service import alert_error
from app.services.state_machine import ConversationState
from app.services.telegram_service import TelegramService, build_handover_buttons, format_handover_message

logger = get_logger("escalation_service")

SIMULATION_CONTEXT_KEY = "simulation"


def _normalize_slot_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _extract_decision_meta(message: Message | None) -> dict:
    if not message or not isinstance(message.message_metadata, dict):
        return {}
    decision_meta = message.message_metadata.get("decision_meta")
    return decision_meta if isinstance(decision_meta, dict) else {}


def _build_handover_meta(conversation: Conversation, message: Message | None, user: User | None) -> dict | None:
    decision_meta = _extract_decision_meta(message)
    meta: dict = {}
    intent = decision_meta.get("intent")
    if isinstance(intent, str) and intent.strip():
        meta["intent"] = intent.strip()
    info_sections = decision_meta.get("info_sections")
    if isinstance(info_sections, list):
        cleaned_sections = [item.strip() for item in info_sections if isinstance(item, str) and item.strip()]
        if cleaned_sections:
            meta["info_sections"] = cleaned_sections

    slots: dict[str, str] = {}
    raw_slots = decision_meta.get("slots")
    if isinstance(raw_slots, dict):
        for key in ("service", "datetime", "name", "phone"):
            value = _normalize_slot_value(raw_slots.get(key))
            if value:
                slots[key] = value

    context = conversation.context if isinstance(conversation.context, dict) else {}
    booking = context.get("booking") if isinstance(context, dict) else None
    if isinstance(booking, dict):
        for key in ("service", "datetime", "name", "phone"):
            if key in slots:
                continue
            value = _normalize_slot_value(booking.get(key))
            if value:
                slots[key] = value

    if user:
        if "name" not in slots:
            name = _normalize_slot_value(getattr(user, "name", None))
            if name:
                slots["name"] = name
        if "phone" not in slots:
            phone = _normalize_slot_value(getattr(user, "phone", None))
            if phone:
                slots["phone"] = phone

    if slots:
        meta["slots"] = slots

    return meta or None


def _get_latest_user_message(db: Session, conversation_id: UUID) -> Message | None:
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id, Message.role == "user")
        .order_by(Message.created_at.desc())
        .first()
    )


def _is_simulation_context(conversation: Conversation | None) -> bool:
    if not conversation or not isinstance(conversation.context, dict):
        return False
    sim_context = conversation.context.get(SIMULATION_CONTEXT_KEY)
    if isinstance(sim_context, dict):
        if sim_context.get("mode") is not None:
            return bool(sim_context.get("mode"))
        if sim_context.get("id"):
            return True
    if conversation.context.get("simulation_mode") is True:
        return True
    if conversation.context.get("simulation_id"):
        return True
    return False


def _build_simulated_topic_id(conversation: Conversation, user: User | None) -> int:
    seed = f"sim:{conversation.id}:{getattr(user, 'id', '')}"
    digest = uuid.uuid5(uuid.NAMESPACE_DNS, seed).int
    return 1000 + (digest % 2147480000)


def get_telegram_credentials(db: Session, client_id: UUID) -> Tuple[Optional[str], Optional[str]]:
    """Get Telegram bot_token and chat_id for client."""
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client_id).first()

    if settings and settings.telegram_bot_token and settings.telegram_chat_id:
        return settings.telegram_bot_token, settings.telegram_chat_id

    return None, None


def resolve_telegram_routing(
    db: Session,
    *,
    conversation: Conversation,
    client_id: UUID,
) -> dict:
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client_id).first()
    manager_scope = getattr(settings, "manager_scope", None) or "branch"
    bot_token = getattr(settings, "telegram_bot_token", None)
    chat_id = getattr(settings, "telegram_chat_id", None)
    routing_source = "client"
    branch_chat_id = None
    branch_id = conversation.branch_id if conversation else None

    if manager_scope == "branch" and branch_id:
        branch = (
            db.query(Branch)
            .filter(Branch.id == branch_id, Branch.client_id == client_id)
            .first()
        )
        if branch and branch.telegram_chat_id:
            branch_chat_id = branch.telegram_chat_id
            chat_id = branch_chat_id
            routing_source = "branch"
        else:
            routing_source = "branch_fallback"

    return {
        "bot_token": bot_token,
        "chat_id": chat_id,
        "routing_source": routing_source,
        "manager_scope": manager_scope,
        "branch_id": str(branch_id) if branch_id else None,
        "branch_chat_id": branch_chat_id,
    }


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
    trigger_message = _get_latest_user_message(db, conversation.id)
    handover_meta = _build_handover_meta(conversation, trigger_message, user)

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
        channel_ref=user.remote_jid if user else None,
        trigger_message_id=trigger_message.id if trigger_message else None,
        meta=handover_meta,
    )
    db.add(handover)
    db.flush()  # Get ID before commit

    return handover


def get_active_handover(db: Session, conversation_id: UUID) -> Optional[Handover]:
    """Get latest pending/active handover for conversation."""
    return (
        db.query(Handover)
        .filter(
            Handover.conversation_id == conversation_id,
            Handover.status.in_(["pending", "active"]),
        )
        .order_by(Handover.created_at.desc())
        .first()
    )


def get_or_create_topic(
    db: Session,
    telegram: TelegramService | None,
    chat_id: str,
    conversation: Conversation,
    user: User,
) -> Optional[int]:
    """Get existing topic or create new one. Returns topic_id."""
    if not user:
        logger.warning(f"Cannot resolve topic: user missing for conversation {conversation.id}")
        return None

    # Check if topic already exists (canonical: user.telegram_topic_id)
    topic_id = user.telegram_topic_id or conversation.telegram_topic_id
    if topic_id:
        if not user.telegram_topic_id:
            user.telegram_topic_id = topic_id
        if conversation.telegram_topic_id != topic_id:
            conversation.telegram_topic_id = topic_id
        db.flush()
        return topic_id

    if _is_simulation_context(conversation):
        topic_id = _build_simulated_topic_id(conversation, user)
        user.telegram_topic_id = topic_id
        conversation.telegram_topic_id = topic_id
        db.flush()
        logger.info("Simulation topic assigned %s for conversation %s", topic_id, conversation.id)
        return topic_id

    # Create topic name: "77015705555 Жанбол [Truffles]"
    phone = user.phone or "Unknown"
    name = user.name or "Клиент"
    topic_name = f"{phone} {name}"

    # Create topic
    topic_id = telegram.create_forum_topic(chat_id, topic_name)

    if topic_id:
        # Save to user (canonical) + conversation copy
        user.telegram_topic_id = topic_id
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
    routing_meta: dict | None = None,
) -> bool:
    """Send handover notification to Telegram topic with buttons and pin."""
    if _is_simulation_context(conversation):
        topic_id = get_or_create_topic(db, None, "", conversation, user)
        handover.notified_at = datetime.now(timezone.utc)
        if topic_id and not handover.telegram_message_id:
            handover.telegram_message_id = -abs(int(topic_id))
        db.flush()
        logger.info(
            "Simulation mode: skipping telegram notification for handover %s",
            handover.id,
        )
        return True

    routing_meta = routing_meta or resolve_telegram_routing(
        db,
        conversation=conversation,
        client_id=handover.client_id,
    )
    bot_token = routing_meta.get("bot_token")
    chat_id = routing_meta.get("chat_id")

    if not bot_token or not chat_id:
        logger.warning(f"No Telegram credentials for client {handover.client_id}")
        return False

    telegram = TelegramService(bot_token)

    # 1. Get or create topic
    topic_id = get_or_create_topic(db, telegram, chat_id, conversation, user)
    if not topic_id:
        logger.warning(f"No topic_id for conversation {conversation.id}")
        return False

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
            if user:
                user.telegram_topic_id = None
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

        # 5. Save telegram_message_id
        handover.telegram_message_id = message_id
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
    from app.services.state_service import transition_state

    existing_handover = get_active_handover(db, conversation.id)
    if existing_handover:
        if conversation.state == ConversationState.BOT_ACTIVE.value:
            target_state = (
                ConversationState.MANAGER_ACTIVE
                if existing_handover.status == "active"
                else ConversationState.PENDING
            )
            transition_state(
                conversation,
                target_state,
                allow_same=True,
                enforce=False,
                handover=existing_handover,
            )
            conversation.escalated_at = datetime.now(timezone.utc)
        telegram_sent = send_telegram_notification(
            db=db,
            handover=existing_handover,
            conversation=conversation,
            user=user,
            message=user_message or "",
        )
        return existing_handover, telegram_sent

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
