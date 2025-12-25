from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Conversation, Handover, User
from app.services.state_machine import ConversationState

logger = get_logger("health_service")

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
        conv.state = ConversationState.BOT_ACTIVE.value
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
            conv.state = ConversationState.BOT_ACTIVE.value
            conv.retry_offered_at = None
            healed.append(
                {
                    "conversation_id": str(conv.id),
                    "issue": f"{old_state}_no_handover",
                    "action": "reset_to_bot_active",
                }
            )
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


def get_system_health(db: Session) -> dict:
    """Получить общее состояние системы."""

    bot_active = db.query(Conversation).filter(Conversation.state == ConversationState.BOT_ACTIVE.value).count()

    pending = db.query(Conversation).filter(Conversation.state == ConversationState.PENDING.value).count()

    manager_active = db.query(Conversation).filter(Conversation.state == ConversationState.MANAGER_ACTIVE.value).count()

    pending_handovers = db.query(Handover).filter(Handover.status == "pending").count()

    active_handovers = db.query(Handover).filter(Handover.status == "active").count()

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
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
