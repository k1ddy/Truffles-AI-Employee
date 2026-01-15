from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Conversation, Handover, User
from app.services.escalation_service import get_or_create_topic, resolve_telegram_routing
from app.services.result import Result
from app.services.state_machine import ConversationState, is_transition_allowed
from app.services.telegram_service import TelegramService

logger = get_logger("state_service")

PENDING_RESUME_KEY = "pending_resume"
DECISION_TRACE_KEY = "decision_trace"
PENDING_RESUME_SNAPSHOT_KEYS = {
    "context_manager",
    "expected_reply_type",
    "intent_queue",
    "booking",
    "session_memory",
    "last_service_hint",
    "last_service_hint_at",
}
PENDING_RESUME_CLEAR_KEYS = {
    "context_manager",
    "expected_reply_type",
    "intent_queue",
    "booking",
    "session_memory",
    "last_service_hint",
    "last_service_hint_at",
}


def _reset_context_preserving_trace(conversation: Conversation) -> None:
    existing = conversation.context if isinstance(conversation.context, dict) else {}
    if DECISION_TRACE_KEY in existing:
        conversation.context = {DECISION_TRACE_KEY: existing.get(DECISION_TRACE_KEY)}
    else:
        conversation.context = {}


def _capture_pending_resume_context(context: dict | None) -> dict:
    if not isinstance(context, dict):
        return {}
    if PENDING_RESUME_KEY in context:
        return context
    resume_payload = {key: context.get(key) for key in PENDING_RESUME_SNAPSHOT_KEYS if key in context}
    if not resume_payload:
        return context
    updated = dict(context)
    updated[PENDING_RESUME_KEY] = resume_payload
    for key in PENDING_RESUME_CLEAR_KEYS:
        updated.pop(key, None)
    return updated


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
        conversation.context = _capture_pending_resume_context(conversation.context)
        routing_meta = resolve_telegram_routing(
            db,
            conversation=conversation,
            client_id=conversation.client_id,
        )
        bot_token = routing_meta.get("bot_token")
        chat_id = routing_meta.get("chat_id")
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

        transition_state(
            conversation,
            ConversationState.PENDING,
            allow_same=False,
            enforce=True,
            handover=handover,
        )
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

        transition_state(
            conversation,
            ConversationState.MANAGER_ACTIVE,
            allow_same=False,
            enforce=True,
            handover=handover,
        )
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
    *,
    preserve_context: bool = False,
) -> Result[bool]:
    """Атомарный переход manager_active/pending → bot_active."""

    if conversation.state not in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]:
        return Result.failure(f"Cannot resolve from state {conversation.state}", "invalid_state")

    try:
        now = datetime.now(timezone.utc)

        transition_state(
            conversation,
            ConversationState.BOT_ACTIVE,
            allow_same=False,
            enforce=True,
            handover=handover,
        )
        conversation.bot_muted_until = None
        conversation.no_count = 0
        conversation.retry_offered_at = None
        if not preserve_context:
            _reset_context_preserving_trace(conversation)
        elif not isinstance(conversation.context, dict):
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


def _coerce_state(value: str | ConversationState | None) -> ConversationState | None:
    if isinstance(value, ConversationState):
        return value
    if value is None:
        return None
    try:
        return ConversationState(value)
    except ValueError:
        return None


def transition_state(
    conversation: Conversation,
    to_state: ConversationState,
    *,
    allow_same: bool = False,
    enforce: bool = True,
    handover: Handover = None,
) -> dict:
    """Централизованный переход состояния с проверкой инвариантов."""
    from_state_value = conversation.state
    to_state_value = to_state.value
    from_state = _coerce_state(from_state_value)

    invalid_transition = False
    if from_state is None:
        invalid_transition = True
    else:
        invalid_transition = not is_transition_allowed(from_state, to_state, allow_same=allow_same)

    if not invalid_transition or not enforce:
        conversation.state = to_state_value

    violations = check_invariants(conversation, handover)

    return {
        "from_state": from_state_value,
        "to_state": to_state_value,
        "invalid_transition": invalid_transition,
        "violations": violations,
    }


def force_state(
    conversation: Conversation,
    to_state: ConversationState,
    *,
    reason: str | None = None,
    handover: Handover = None,
) -> dict:
    """Принудительный переход состояния (heal/cron)."""
    from_state_value = conversation.state
    to_state_value = to_state.value
    conversation.state = to_state_value

    violations = check_invariants(conversation, handover)
    logger.warning(
        "Forced state transition",
        extra={
            "from_state": from_state_value,
            "to_state": to_state_value,
            "reason": reason,
            "violations": violations,
        },
    )

    return {
        "from_state": from_state_value,
        "to_state": to_state_value,
        "invalid_transition": False,
        "violations": violations,
        "forced": True,
    }
