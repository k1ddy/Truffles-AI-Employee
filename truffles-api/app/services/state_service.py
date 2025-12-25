from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Conversation, Handover, User
from app.services.escalation_service import get_or_create_topic, get_telegram_credentials
from app.services.result import Result
from app.services.state_machine import ConversationState
from app.services.telegram_service import TelegramService

logger = get_logger("state_service")


def escalate_to_pending(
    db: Session,
    conversation: Conversation,
    user_message: str,
    trigger_type: str,
    trigger_value: str = None,
) -> Result[Handover]:
    """Атомарный переход bot_active → pending с созданием handover и topic."""

    if conversation.state != ConversationState.BOT_ACTIVE.value:
        return Result.failure(f"Cannot escalate from state {conversation.state}", "invalid_state")

    try:
        bot_token, chat_id = get_telegram_credentials(db, conversation.client_id)
        if not bot_token or not chat_id:
            return Result.failure("No Telegram credentials", "no_telegram")

        telegram = TelegramService(bot_token)
        user = db.query(User).filter(User.id == conversation.user_id).first()
        remote_jid = user.remote_jid if user else None

        topic_id = get_or_create_topic(db, telegram, chat_id, conversation, user)
        if not topic_id:
            return Result.failure("Failed to create topic", "topic_error")

        now = datetime.now(timezone.utc)

        handover = Handover(
            conversation_id=conversation.id,
            client_id=conversation.client_id,
            trigger_type=trigger_type,
            trigger_value=trigger_value,
            user_message=user_message,
            status="pending",
            created_at=now,
            channel="telegram",
            channel_ref=remote_jid,
        )
        db.add(handover)

        conversation.state = ConversationState.PENDING.value
        conversation.telegram_topic_id = topic_id
        conversation.escalated_at = now
        conversation.retry_offered_at = None

        db.flush()

        logger.info(f"Escalated conversation {conversation.id} to pending, topic={topic_id}")
        return Result.success(handover)

    except Exception as e:
        logger.error(f"Escalation failed: {e}")
        return Result.failure(str(e), "escalation_error")


def manager_take(
    db: Session,
    conversation: Conversation,
    handover: Handover,
    manager_id: str,
    manager_name: str,
) -> Result[bool]:
    """Атомарный переход pending → manager_active."""

    if conversation.state != ConversationState.PENDING.value:
        return Result.failure(f"Cannot take from state {conversation.state}", "invalid_state")

    if handover.status != "pending":
        return Result.failure(f"Handover status is {handover.status}", "invalid_handover")

    try:
        now = datetime.now(timezone.utc)

        conversation.state = ConversationState.MANAGER_ACTIVE.value
        handover.status = "active"
        handover.assigned_to = manager_id
        handover.assigned_to_name = manager_name
        handover.first_response_at = now

        db.flush()

        logger.info(f"Manager {manager_name} took conversation {conversation.id}")
        return Result.success(True)

    except Exception as e:
        logger.error(f"Manager take failed: {e}")
        return Result.failure(str(e), "take_error")


def manager_resolve(
    db: Session,
    conversation: Conversation,
    handover: Handover,
    manager_id: str,
    manager_name: str,
) -> Result[bool]:
    """Атомарный переход manager_active/pending → bot_active."""

    if conversation.state not in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]:
        return Result.failure(f"Cannot resolve from state {conversation.state}", "invalid_state")

    try:
        now = datetime.now(timezone.utc)

        conversation.state = ConversationState.BOT_ACTIVE.value
        conversation.bot_muted_until = None
        conversation.no_count = 0
        conversation.retry_offered_at = None
        conversation.context = {}

        handover.status = "resolved"
        handover.resolved_at = now
        handover.resolved_by_id = manager_id
        handover.resolved_by_name = manager_name

        if handover.created_at:
            handover.resolution_time_seconds = int((now - handover.created_at).total_seconds())

        db.flush()

        logger.info(f"Manager {manager_name} resolved conversation {conversation.id}")
        return Result.success(True)

    except Exception as e:
        logger.error(f"Manager resolve failed: {e}")
        return Result.failure(str(e), "resolve_error")


def check_invariants(conversation: Conversation, handover: Handover = None) -> list[str]:
    """Проверить инварианты состояния. Возвращает список нарушений."""
    violations = []

    if conversation.state == ConversationState.MANAGER_ACTIVE.value:
        if not conversation.telegram_topic_id:
            violations.append("manager_active_no_topic")

    if conversation.state == ConversationState.PENDING.value:
        if not conversation.telegram_topic_id:
            violations.append("pending_no_topic")

    if conversation.state in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]:
        if handover is None or handover.status not in ["pending", "active"]:
            violations.append("no_active_handover")

    return violations
