from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Conversation, Handover
from app.services.state_machine import ConversationState

logger = get_logger("health_service")


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
        old_state = conv.state
        conv.state = ConversationState.BOT_ACTIVE.value

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
            healed.append(
                {
                    "conversation_id": str(conv.id),
                    "issue": f"{old_state}_no_handover",
                    "action": "reset_to_bot_active",
                }
            )
            logger.warning(f"Healed conversation {conv.id}: {old_state} without active handover")

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
