import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Conversation, Handover, Message, User
from app.services.escalation_service import get_or_create_topic, resolve_telegram_routing
from app.services.result import Result
from app.services.state_machine import ConversationState, is_transition_allowed
from app.services.telegram_service import TelegramService

logger = get_logger("state_service")

PENDING_RESUME_KEY = "pending_resume"
DECISION_TRACE_KEY = "decision_trace"
SIMULATION_CONTEXT_KEY = "simulation"
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
HANDOVER_REOPEN_WINDOW_SECONDS = 4 * 60 * 60


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


def _get_latest_user_message(db: Session, conversation_id: uuid.UUID) -> Message | None:
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id, Message.role == "user")
        .order_by(Message.created_at.desc())
        .first()
    )


def _reset_context_preserving_trace(conversation: Conversation) -> None:
    existing = conversation.context if isinstance(conversation.context, dict) else {}
    preserved: dict = {}
    if DECISION_TRACE_KEY in existing:
        preserved[DECISION_TRACE_KEY] = existing.get(DECISION_TRACE_KEY)
    if SIMULATION_CONTEXT_KEY in existing:
        preserved[SIMULATION_CONTEXT_KEY] = existing.get(SIMULATION_CONTEXT_KEY)
    if "memory_profile" in existing:
        preserved["memory_profile"] = existing.get("memory_profile")
    if "memory_pending" in existing:
        preserved["memory_pending"] = existing.get("memory_pending")
    conversation.context = preserved or {}


def _extract_simulation_meta(metadata) -> dict | None:
    if not metadata:
        return None
    sim_mode = getattr(metadata, "simulation_mode", None)
    sim_id = getattr(metadata, "simulation_id", None)
    sim_llm = getattr(metadata, "simulation_llm", None)
    sim_time = getattr(metadata, "simulation_time", None)
    if sim_mode is None and sim_id is None and sim_llm is None and sim_time is None:
        return None
    if sim_mode is None:
        sim_mode = True
    payload = {"mode": bool(sim_mode), "id": sim_id}
    if sim_llm is not None:
        payload["llm_allowed"] = bool(sim_llm)
    if sim_time is not None:
        payload["time"] = sim_time
    return payload


def build_simulation_context(metadata) -> dict | None:
    return _extract_simulation_meta(metadata)


def _get_simulation_context(value) -> dict | None:
    if hasattr(value, "context"):
        context = value.context
    else:
        context = value
    if not isinstance(context, dict):
        return None
    sim_context = context.get(SIMULATION_CONTEXT_KEY)
    if isinstance(sim_context, dict):
        if sim_context.get("mode") is None:
            sim_context = dict(sim_context)
            sim_context["mode"] = True
        if sim_context.get("time") is None and sim_context.get("simulation_time") is not None:
            sim_context = dict(sim_context)
            sim_context["time"] = sim_context.get("simulation_time")
        return sim_context
    sim_mode = context.get("simulation_mode")
    sim_id = context.get("simulation_id")
    sim_llm = context.get("simulation_llm")
    sim_time = context.get("simulation_time")
    if sim_mode is None and sim_id is None and sim_llm is None and sim_time is None:
        return None
    if sim_mode is None:
        sim_mode = True
    payload = {"mode": bool(sim_mode), "id": sim_id}
    if sim_llm is not None:
        payload["llm_allowed"] = bool(sim_llm)
    if sim_time is not None:
        payload["time"] = sim_time
    return payload


def apply_simulation_context(conversation: Conversation, metadata) -> dict | None:
    sim_meta = _extract_simulation_meta(metadata)
    if not sim_meta:
        return None
    context = conversation.context if isinstance(conversation.context, dict) else {}
    updated = dict(context)
    sim_context = dict(updated.get(SIMULATION_CONTEXT_KEY) or {})
    if sim_meta.get("id") and not sim_context.get("id"):
        sim_context["id"] = sim_meta["id"]
    if "mode" in sim_meta:
        sim_context["mode"] = sim_meta["mode"]
    if "llm_allowed" in sim_meta:
        sim_context["llm_allowed"] = sim_meta["llm_allowed"]
    if "time" in sim_meta:
        sim_context["time"] = sim_meta["time"]
    sim_context.setdefault("source", "webhook_metadata")
    sim_context["updated_at"] = datetime.now(timezone.utc).isoformat()
    updated[SIMULATION_CONTEXT_KEY] = sim_context
    conversation.context = updated
    return sim_context


def is_simulation_context(value) -> bool:
    sim_context = _get_simulation_context(value)
    if not sim_context:
        return False
    if sim_context.get("mode") is not None:
        return bool(sim_context.get("mode"))
    return True


def _parse_simulation_time(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            raw = f"{raw[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def get_simulation_time(value) -> datetime | None:
    sim_context = _get_simulation_context(value)
    if not sim_context:
        return None
    return _parse_simulation_time(sim_context.get("time") or sim_context.get("simulation_time"))


def _build_simulated_topic_id(conversation: Conversation, user: User | None) -> int:
    seed = f"sim:{conversation.id}:{getattr(user, 'id', '')}"
    digest = uuid.uuid5(uuid.NAMESPACE_DNS, seed).int
    return 1000 + (digest % 2147480000)


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


def _find_recent_resolved_handover(
    db: Session,
    conversation: Conversation,
    *,
    now: datetime,
) -> Handover | None:
    cutoff = now - timedelta(seconds=HANDOVER_REOPEN_WINDOW_SECONDS)
    last_activity = func.coalesce(Handover.resolved_at, Handover.created_at)
    return (
        db.query(Handover)
        .filter(
            Handover.conversation_id == conversation.id,
            Handover.client_id == conversation.client_id,
            Handover.status == "resolved",
            last_activity >= cutoff,
        )
        .order_by(last_activity.desc())
        .first()
    )


def _reopen_handover(
    handover: Handover,
    *,
    now: datetime,
    trigger_type: str,
    trigger_value: str | None,
    user_message: str | None,
    channel_ref: str | None,
    trigger_message_id: uuid.UUID | None = None,
    meta: dict | None = None,
) -> None:
    handover.status = "pending"
    handover.trigger_type = trigger_type
    handover.trigger_value = trigger_value
    handover.user_message = user_message
    handover.created_at = now
    handover.context_summary = None
    handover.notified_at = None
    handover.first_response_at = None
    handover.resolved_at = None
    handover.resolved_by_id = None
    handover.resolved_by_name = None
    handover.resolution_time_seconds = None
    handover.resolution_type = None
    handover.resolution_notes = None
    handover.manager_response = None
    handover.manager_id = None
    handover.assigned_to = None
    handover.assigned_to_name = None
    handover.telegram_message_id = None
    handover.reminder_1_sent_at = None
    handover.reminder_2_sent_at = None
    handover.skipped_by = []
    if trigger_message_id:
        handover.trigger_message_id = trigger_message_id
    if meta:
        handover.meta = meta
    if channel_ref:
        handover.channel_ref = channel_ref
    handover._reopened = True


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
        if is_simulation_context(conversation):
            conversation.context = _capture_pending_resume_context(conversation.context)
            now = datetime.now(timezone.utc)
            user = db.query(User).filter(User.id == conversation.user_id).first()
            remote_jid = user.remote_jid if user else None
            topic_id = _build_simulated_topic_id(conversation, user)
            trigger_message = _get_latest_user_message(db, conversation.id)
            handover_meta = _build_handover_meta(conversation, trigger_message, user)

            handover = _find_recent_resolved_handover(db, conversation, now=now)
            if handover:
                _reopen_handover(
                    handover,
                    now=now,
                    trigger_type=trigger_type,
                    trigger_value=trigger_value,
                    user_message=user_message,
                    channel_ref=remote_jid,
                    trigger_message_id=trigger_message.id if trigger_message else None,
                    meta=handover_meta,
                )
            else:
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
                    trigger_message_id=trigger_message.id if trigger_message else None,
                    meta=handover_meta,
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
            if user:
                user.telegram_topic_id = topic_id
            conversation.escalated_at = now
            conversation.retry_offered_at = None

            db.flush()

            logger.info(
                "Escalated conversation %s to pending (simulation), topic=%s, reopened=%s",
                conversation.id,
                topic_id,
                bool(getattr(handover, "_reopened", False)),
            )
            return Result.success(handover)

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
        trigger_message = _get_latest_user_message(db, conversation.id)
        handover_meta = _build_handover_meta(conversation, trigger_message, user)

        topic_id = get_or_create_topic(db, telegram, chat_id, conversation, user)
        if not topic_id:
            return Result.failure("Failed to create topic", "topic_error")

        now = datetime.now(timezone.utc)
        handover = _find_recent_resolved_handover(db, conversation, now=now)
        if handover:
            _reopen_handover(
                handover,
                now=now,
                trigger_type=trigger_type,
                trigger_value=trigger_value,
                user_message=user_message,
                channel_ref=remote_jid,
                trigger_message_id=trigger_message.id if trigger_message else None,
                meta=handover_meta,
            )
        else:
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
                trigger_message_id=trigger_message.id if trigger_message else None,
                meta=handover_meta,
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

        logger.info(
            "Escalated conversation %s to pending, topic=%s, reopened=%s",
            conversation.id,
            topic_id,
            bool(getattr(handover, "_reopened", False)),
        )
        return Result.success(handover)

    except Exception as e:
        try:
            db.rollback()
        except Exception as rollback_exc:
            logger.warning(
                "Escalation rollback failed",
                extra={"context": {"error": str(rollback_exc)}},
            )
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


def manager_return(
    db: Session,
    conversation: Conversation,
    handover: Handover,
    manager_id: str,
    manager_name: str,
    *,
    preserve_context: bool = True,
) -> Result[bool]:
    """Атомарный переход manager_active/pending → bot_active без закрытия handover."""

    if conversation.state not in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]:
        return Result.failure(f"Cannot return from state {conversation.state}", "invalid_state")

    try:
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

        handover.status = "bot_handling"
        handover.resolved_at = None
        handover.resolved_by_id = None
        handover.resolved_by_name = None
        handover.resolution_time_seconds = None
        handover.resolution_type = None
        handover.resolution_notes = None
        handover.assigned_to = None
        handover.assigned_to_name = None

        db.flush()

        logger.info(f"Manager {manager_name} returned conversation {conversation.id} to bot")
        return Result.success(True)

    except Exception as e:
        logger.error(f"Manager return failed: {e}")
        return Result.failure(str(e), "return_error")


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
