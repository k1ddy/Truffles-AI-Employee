import asyncio
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.models import Client, ClientSettings, Conversation, Handover, Message
from app.schemas.webhook import WebhookRequest, WebhookResponse
from app.services.chatflow_service import send_bot_response
from app.services.conversation_service import (
    get_or_create_conversation,
    get_or_create_user,
)
from app.services.escalation_service import get_telegram_credentials, send_telegram_notification
from app.services.ai_service import is_acknowledgement_message, is_low_signal_message
from app.services.intent_service import Intent, classify_intent, is_rejection, should_escalate
from app.services.message_service import generate_bot_response, save_message
from app.services.state_machine import ConversationState
from app.services.state_service import escalate_to_pending, manager_resolve
from app.services.telegram_service import TelegramService

logger = get_logger("webhook")

router = APIRouter()

# Optional Redis-based debounce for bursty WhatsApp messages.
try:
    import redis.asyncio as redis_async  # type: ignore
except Exception:  # pragma: no cover
    redis_async = None


_debounce_redis_client = None
_debounce_redis_url = None


def _is_env_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _get_debounce_settings() -> tuple[bool, float, int, str, float]:
    enabled = _is_env_enabled(os.environ.get("DEBOUNCE_ENABLED"), default=True)
    inactivity_seconds = float(os.environ.get("DEBOUNCE_INACTIVITY_SECONDS", "1.5"))
    ttl_seconds = int(float(os.environ.get("DEBOUNCE_TTL_SECONDS", "30")))
    redis_url = os.environ.get("REDIS_URL", "redis://truffles_redis_1:6379/0")
    socket_timeout_seconds = float(os.environ.get("DEBOUNCE_SOCKET_TIMEOUT_SECONDS", "0.3"))
    return enabled, inactivity_seconds, ttl_seconds, redis_url, socket_timeout_seconds


def _get_message_buffer_settings() -> tuple[bool, int]:
    enabled = _is_env_enabled(os.environ.get("DEBOUNCE_ENABLED"), default=True)
    max_messages = int(float(os.environ.get("DEBOUNCE_MAX_BUFFER_MESSAGES", "8")))
    return enabled, max_messages


def _get_dedup_settings() -> tuple[int, str, float]:
    ttl_seconds = int(float(os.environ.get("DEDUP_TTL_SECONDS", "86400")))
    redis_url = os.environ.get("REDIS_URL", "redis://truffles_redis_1:6379/0")
    socket_timeout_seconds = float(os.environ.get("DEDUP_SOCKET_TIMEOUT_SECONDS", "0.3"))
    return ttl_seconds, redis_url, socket_timeout_seconds


def _get_debounce_redis(redis_url: str, socket_timeout_seconds: float):
    global _debounce_redis_client, _debounce_redis_url

    if redis_async is None:
        return None

    if _debounce_redis_client is None or _debounce_redis_url != redis_url:
        _debounce_redis_url = redis_url
        _debounce_redis_client = redis_async.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=socket_timeout_seconds,
            socket_timeout=socket_timeout_seconds,
        )

    return _debounce_redis_client


async def should_process_debounced_message(
    *,
    client_id: str,
    remote_jid: str,
    message_id: str | None,
    sleep_func=asyncio.sleep,
    redis_client=None,
) -> bool:
    """
    Debounce bursty user messages: only the latest message in a short window triggers AI/escalation.

    Strategy: store a per-user token in Redis and check after a short pause whether it's still the last one.
    If Redis is unavailable, falls back to current behavior (process immediately).
    """
    enabled, inactivity_seconds, ttl_seconds, redis_url, socket_timeout_seconds = _get_debounce_settings()
    if not enabled:
        return True

    token = message_id or uuid4().hex
    key = f"truffles:debounce:{client_id}:{remote_jid}"

    redis_client = redis_client or _get_debounce_redis(redis_url, socket_timeout_seconds)
    if not redis_client:
        return True

    try:
        await redis_client.set(key, token, ex=ttl_seconds)
        await sleep_func(inactivity_seconds)
        last_token = await redis_client.get(key)
        return last_token == token
    except Exception as e:
        logger.warning(f"Debounce unavailable, proceeding without it: {e}")
        return True


async def _buffer_user_message(
    *,
    redis_client,
    client_id: str,
    remote_jid: str,
    message_text: str,
    ttl_seconds: int,
    max_messages: int,
) -> None:
    if not redis_client:
        return

    key = f"truffles:buffer:{client_id}:{remote_jid}"
    try:
        await redis_client.rpush(key, message_text)
        await redis_client.ltrim(key, -max_messages, -1)
        await redis_client.expire(key, ttl_seconds)
    except Exception as e:
        logger.warning(f"Message buffer unavailable: {e}")


async def _drain_buffered_messages(*, redis_client, client_id: str, remote_jid: str) -> list[str]:
    if not redis_client:
        return []

    key = f"truffles:buffer:{client_id}:{remote_jid}"
    try:
        messages = await redis_client.lrange(key, 0, -1)
        await redis_client.delete(key)
    except Exception as e:
        logger.warning(f"Message buffer drain failed: {e}")
        return []

    cleaned: list[str] = []
    for msg in messages or []:
        if not msg:
            continue
        text = msg.strip()
        if text:
            cleaned.append(text)
    return cleaned


async def is_duplicate_message_id(
    *,
    db: Session,
    client_id,
    message_id: str | None,
    redis_client=None,
) -> bool:
    if not message_id:
        return False

    ttl_seconds, redis_url, socket_timeout_seconds = _get_dedup_settings()
    key = f"truffles:dedup:{client_id}:{message_id}"

    redis_client = redis_client or _get_debounce_redis(redis_url, socket_timeout_seconds)
    if redis_client:
        try:
            was_set = await redis_client.set(key, "1", ex=ttl_seconds, nx=True)
            if not was_set:
                return True
        except Exception as e:
            logger.warning(f"Dedup redis unavailable, falling back to DB: {e}")

    duplicate = (
        db.query(Message)
        .filter(
            Message.client_id == client_id,
            Message.message_metadata["message_id"].astext == message_id,
        )
        .first()
    )
    return duplicate is not None

# Default values (can be overridden in client_settings)
DEFAULT_MUTE_DURATION_FIRST_MINUTES = 30
DEFAULT_MUTE_DURATION_SECOND_HOURS = 24
SESSION_TIMEOUT_HOURS = 24
LOW_CONFIDENCE_RETRY_WINDOW_MINUTES = 10
MSG_ESCALATED = "Передал менеджеру. Могу чем-то помочь пока ждёте?"
MSG_MUTED_TEMP = "Хорошо, напишите если понадоблюсь."
MSG_MUTED_LONG = "Понял! Если ответа от менеджеров долго нет — лучше звоните напрямую: +7 775 984 19 26"
MSG_LOW_CONFIDENCE = "Хороший вопрос! Уточню у коллег и вернусь с ответом."
MSG_LOW_CONFIDENCE_RETRY = (
    "Не совсем понял. Напишите, пожалуйста, что именно нужно по салону: "
    "цена/длительность/запись/адрес/мастер или жалоба."
)
MSG_PENDING_LOW_CONFIDENCE = (
    "Я уже передал менеджеру — он скоро подключится. "
    "Пока ждём, уточните, пожалуйста, что нужно (цена/время/запись/адрес/мастер или жалоба)."
)
MSG_PENDING_STATUS = "Да, я передал. Сейчас менеджер ещё не взял заявку. Как только возьмёт — ответит здесь. Пока ждём, могу помочь: уточните, что нужно?"
MSG_AI_ERROR = "Извините, произошла ошибка. Попробуйте позже."
GREETING_RESPONSE = "Здравствуйте! Чем могу помочь?"
THANKS_RESPONSE = "Рад помочь. Если нужно что-то ещё — пишите."


def is_handover_status_question(text: str) -> bool:
    """Detect 'did you forward / when manager replies' questions in pending state."""
    if not text:
        return False

    normalized = text.strip().casefold()
    keywords = [
        "передал",
        "передали",
        "передано",
        "заявк",
        "менеджер",
        "админ",
        "администратор",
        "когда ответ",
        "когда ответит",
        "не отвеч",
        "не отвечает",
        "почему не отвеч",
        "почему молч",
        "молч",
        "тишин",
        "сколько ждать",
        "ждать",
        "ответит",
        "взял",
        "взяли",
        "беру",
    ]
    return any(k in normalized for k in keywords)


def find_active_conversation_by_channel_ref(db: Session, client_id, remote_jid: str) -> Conversation | None:
    """Reuse conversation if there is an active handover for this remote_jid."""
    handover = (
        db.query(Handover)
        .filter(
            Handover.client_id == client_id,
            Handover.channel_ref == remote_jid,
            Handover.status.in_(["pending", "active"]),
        )
        .order_by(Handover.created_at.desc())
        .first()
    )
    if handover:
        return db.query(Conversation).filter(Conversation.id == handover.conversation_id).first()
    return None


def get_mute_settings(db: Session, client_id) -> tuple[int, int]:
    """Get mute durations from client_settings or use defaults."""
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client_id).first()

    if settings:
        mute_first = settings.mute_duration_first_minutes or DEFAULT_MUTE_DURATION_FIRST_MINUTES
        mute_second = settings.mute_duration_second_hours or DEFAULT_MUTE_DURATION_SECOND_HOURS
    else:
        mute_first = DEFAULT_MUTE_DURATION_FIRST_MINUTES
        mute_second = DEFAULT_MUTE_DURATION_SECOND_HOURS

    return mute_first, mute_second


def get_active_handover(db: Session, conversation_id) -> Handover | None:
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


def should_offer_low_confidence_retry(conversation: Conversation, now: datetime) -> bool:
    """One clarifying question before creating a handover on low confidence."""
    offered_at = conversation.retry_offered_at
    if not offered_at:
        return True

    if offered_at.tzinfo is None:
        offered_at = offered_at.replace(tzinfo=timezone.utc)

    return (now - offered_at) > timedelta(minutes=LOW_CONFIDENCE_RETRY_WINDOW_MINUTES)


@router.post("/webhook/debug")
async def debug_webhook(request: Request):
    """Debug endpoint to see raw request."""
    body = await request.json()
    logger.debug(f"DEBUG webhook body: {body}")
    return {"received": body}


@router.post("/webhook", response_model=WebhookResponse)
async def handle_webhook(request: WebhookRequest, db: Session = Depends(get_db)):
    """Handle raw webhook from n8n (same format as ChatFlow webhook)."""
    logger.info(f"Webhook received: client_slug={request.client_slug}")

    body = request.body
    metadata = body.metadata

    if not metadata or not metadata.remoteJid:
        return WebhookResponse(success=False, message="Missing metadata.remoteJid")

    # Get client by slug
    client = db.query(Client).filter(Client.name == request.client_slug).first()
    if not client:
        return WebhookResponse(success=False, message=f"Client '{request.client_slug}' not found")

    remote_jid = metadata.remoteJid
    message_text = body.message or ""
    message_id = metadata.messageId

    if not message_text:
        return WebhookResponse(success=False, message="Empty message")

    if await is_duplicate_message_id(db=db, client_id=client.id, message_id=message_id):
        logger.info(f"Duplicate message_id skipped: {message_id}")
        return WebhookResponse(success=True, message="Duplicate message_id", conversation_id=None, bot_response=None)

    # 1. Get or create user
    user = get_or_create_user(db, client.id, remote_jid)

    # 2. Find existing conversation by handover.channel_ref or create new
    conversation = find_active_conversation_by_channel_ref(db, client.id, remote_jid)
    if not conversation:
        conversation = get_or_create_conversation(db, client.id, user.id, "whatsapp")

    # 3. Save user message (keep message_id for dedup)
    message_metadata = metadata.model_dump(exclude_none=True) if metadata else {}
    if message_id:
        message_metadata["message_id"] = message_id
    save_message(
        db,
        conversation.id,
        client.id,
        role="user",
        content=message_text,
        message_metadata=message_metadata,
    )

    # 4. Update last_message_at (keep previous for session timeout check)
    now = datetime.now(timezone.utc)
    previous_last_message_at = conversation.last_message_at
    conversation.last_message_at = now

    # 5. Check session timeout - reset mute if no messages for 24h+
    bot_response = None
    sent = False
    result_message = None
    intent = None

    # Reset mute if new session (no messages for 24h+)
    if previous_last_message_at:
        last_seen = previous_last_message_at
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        time_since_last = now - last_seen
        if time_since_last > timedelta(hours=SESSION_TIMEOUT_HOURS):
            # New session - reset mute
            conversation.bot_status = "active"
            conversation.bot_muted_until = None
            conversation.no_count = 0
            logger.info(f"Session reset: {time_since_last} since last message")

    # 6. Check if bot is muted - but still forward to topic
    is_muted = False
    if conversation.bot_status == "muted" or (conversation.bot_muted_until and conversation.bot_muted_until > now):
        is_muted = True

    # 7. Forward to topic if pending/manager_active (always, even if muted)
    if conversation.state in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]:
        if conversation.telegram_topic_id:
            bot_token, chat_id = get_telegram_credentials(db, client.id)
            if bot_token and chat_id:
                telegram = TelegramService(bot_token)
                telegram.send_message(
                    chat_id=chat_id,
                    text=f"👤 <b>Клиент:</b> {message_text}",
                    message_thread_id=conversation.telegram_topic_id,
                )

    # 8. Manager active → bot must stay silent (only forwarding above)
    if conversation.state == ConversationState.MANAGER_ACTIVE.value:
        db.commit()
        return WebhookResponse(
            success=True,
            message="Manager active, message forwarded",
            conversation_id=conversation.id,
            bot_response=None,
        )

    # 9. If muted - don't respond, just forward
    if is_muted:
        db.commit()
        return WebhookResponse(
            success=True,
            message="Bot muted, forwarded to topic" if conversation.telegram_topic_id else "Bot muted",
            conversation_id=conversation.id,
            bot_response=None,
        )

    # 9.0 Debounce bursty inputs: only the latest message triggers bot logic.
    if conversation.state in [ConversationState.BOT_ACTIVE.value, ConversationState.PENDING.value]:
        # Persist user message + last_message_at before waiting.
        db.commit()

        debounce_enabled, _, ttl_seconds, redis_url, socket_timeout_seconds = _get_debounce_settings()
        buffer_enabled, max_buffer_messages = _get_message_buffer_settings()
        redis_client = _get_debounce_redis(redis_url, socket_timeout_seconds)

        if debounce_enabled and buffer_enabled and redis_client:
            await _buffer_user_message(
                redis_client=redis_client,
                client_id=str(client.id),
                remote_jid=remote_jid,
                message_text=message_text,
                ttl_seconds=ttl_seconds,
                max_messages=max_buffer_messages,
            )

        should_process = await should_process_debounced_message(
            client_id=str(client.id),
            remote_jid=remote_jid,
            message_id=message_id,
            redis_client=redis_client,
        )
        if not should_process:
            return WebhookResponse(
                success=True,
                message="Debounced: skipped intermediate message",
                conversation_id=conversation.id,
                bot_response=None,
            )

        if debounce_enabled and buffer_enabled and redis_client:
            buffered_messages = await _drain_buffered_messages(
                redis_client=redis_client,
                client_id=str(client.id),
                remote_jid=remote_jid,
            )
            if buffered_messages:
                message_text = " ".join(buffered_messages)

        # Re-check state after waiting: manager could take the request during debounce pause.
        db.refresh(conversation)
        now = datetime.now(timezone.utc)
        if conversation.state == ConversationState.MANAGER_ACTIVE.value:
            return WebhookResponse(
                success=True,
                message="Manager active (after debounce), message forwarded",
                conversation_id=conversation.id,
                bot_response=None,
            )
        if conversation.bot_status == "muted" or (conversation.bot_muted_until and conversation.bot_muted_until > now):
            return WebhookResponse(
                success=True,
                message="Bot muted (after debounce), forwarded to topic"
                if conversation.telegram_topic_id
                else "Bot muted (after debounce)",
                conversation_id=conversation.id,
                bot_response=None,
            )

    # 10. Classify intent (expensive). Protect against accidental escalations on short/noisy messages.
    if is_acknowledgement_message(message_text) or is_low_signal_message(message_text):
        intent = Intent.OTHER
        logger.info("Intent shortcut: acknowledgement/low-signal -> other")
    else:
        intent = classify_intent(message_text)
        logger.info(f"Intent classified: {intent.value}")

    # 10.1 Self-healing moved to health_service.check_and_heal_conversations()
    # Call POST /admin/heal periodically to fix broken states

    # 9.1 Greeting/thanks: always respond politely without escalation
    if intent in [Intent.GREETING, Intent.THANKS]:
        bot_response = GREETING_RESPONSE if intent == Intent.GREETING else THANKS_RESPONSE
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = send_bot_response(db, client.id, remote_jid, bot_response)
        result_message = "Greeting response sent" if sent else "Greeting response failed"
        db.commit()
        return WebhookResponse(
            success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
        )

    # 9.2 Pending: answer status questions without AI/escalation
    if conversation.state == ConversationState.PENDING.value and is_handover_status_question(message_text):
        bot_response = MSG_PENDING_STATUS
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = send_bot_response(db, client.id, remote_jid, bot_response)
        result_message = "Pending status response sent" if sent else "Pending status response failed"
        db.commit()
        return WebhookResponse(
            success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
        )

    # 10. Handle based on intent and state
    if conversation.state == ConversationState.BOT_ACTIVE.value and should_escalate(intent):
        # Escalate using state_service (atomic transition)
        result = escalate_to_pending(
            db=db,
            conversation=conversation,
            user_message=message_text,
            trigger_type="intent",
            trigger_value=intent.value,
        )

        if result.ok:
            handover = result.value
            # Send notification to Telegram
            telegram_sent = send_telegram_notification(
                db=db,
                handover=handover,
                conversation=conversation,
                user=user,
                message=message_text,
            )
            bot_response = MSG_ESCALATED
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = send_bot_response(db, client.id, remote_jid, bot_response)
            result_message = f"Escalated ({intent.value}), telegram={'sent' if telegram_sent else 'failed'}"
        else:
            logger.error(f"Escalation failed: {result.error}")
            # Fallback: respond normally
            gen_result = generate_bot_response(db, conversation, message_text, request.client_slug)
            if gen_result.ok and gen_result.value[0]:
                bot_response = gen_result.value[0]
                save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                sent = send_bot_response(db, client.id, remote_jid, bot_response)
            result_message = f"Escalation failed ({result.error_code}), responded normally"

    elif is_rejection(intent):
        # Client rejects help
        if conversation.state in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]:
            handover = get_active_handover(db, conversation.id)
            if handover:
                manager_resolve(db, conversation, handover, manager_id="system", manager_name="system")
            bot_response = MSG_MUTED_TEMP
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = send_bot_response(db, client.id, remote_jid, bot_response)
            result_message = "Request cancelled, bot reactivated"
        else:
            mute_first, mute_second = get_mute_settings(db, client.id)
            if conversation.no_count == 0:
                # First rejection: mute (default 30 min)
                conversation.bot_muted_until = now + timedelta(minutes=mute_first)
                conversation.no_count = 1
                bot_response = MSG_MUTED_TEMP
            else:
                # Second rejection: mute (default 24 hours)
                conversation.bot_muted_until = now + timedelta(hours=mute_second)
                conversation.no_count += 1
                bot_response = MSG_MUTED_LONG

            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = send_bot_response(db, client.id, remote_jid, bot_response)
            result_message = f"Muted (rejection #{conversation.no_count})"

    elif conversation.state in [ConversationState.BOT_ACTIVE.value, ConversationState.PENDING.value]:
        # Bot responds: normal mode OR pending (bot helps while waiting)
        gen_result = generate_bot_response(db, conversation, message_text, request.client_slug)

        if not gen_result.ok:
            # AI error — fallback response
            bot_response = MSG_AI_ERROR
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = send_bot_response(db, client.id, remote_jid, bot_response)
            result_message = f"AI error: {gen_result.error}"
        else:
            response_text, confidence = gen_result.value

            if confidence == "low_confidence":
                if conversation.state == ConversationState.PENDING.value:
                    # Already escalated: respond but don't re-escalate
                    bot_response = MSG_PENDING_LOW_CONFIDENCE
                    save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                    sent = send_bot_response(db, client.id, remote_jid, bot_response)
                    result_message = "Low confidence while pending, responded without re-escalation"
                else:
                    # Low RAG confidence — first ask clarifying question, only then create a handover.
                    if should_offer_low_confidence_retry(conversation, now):
                        bot_response = MSG_LOW_CONFIDENCE_RETRY
                        conversation.retry_offered_at = now
                        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                        sent = send_bot_response(db, client.id, remote_jid, bot_response)
                        result_message = "Low confidence: asked clarification before escalation"
                    else:
                        esc_result = escalate_to_pending(
                            db=db,
                            conversation=conversation,
                            user_message=message_text,
                            trigger_type="intent",
                            trigger_value="low_confidence",
                        )

                        if esc_result.ok:
                            handover = esc_result.value
                            telegram_sent = send_telegram_notification(
                                db=db,
                                handover=handover,
                                conversation=conversation,
                                user=user,
                                message=message_text,
                            )
                            bot_response = MSG_LOW_CONFIDENCE
                            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                            sent = send_bot_response(db, client.id, remote_jid, bot_response)
                            result_message = (
                                f"Low confidence escalation, telegram={'sent' if telegram_sent else 'failed'}"
                            )
                        else:
                            bot_response = MSG_LOW_CONFIDENCE
                            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                            sent = send_bot_response(db, client.id, remote_jid, bot_response)
                            result_message = f"Low confidence, escalation failed: {esc_result.error}"

            elif confidence == "bot_inactive":
                result_message = f"Bot not active (state: {conversation.state})"

            elif response_text:
                bot_response = response_text
                logger.debug(f"bot_response: {bot_response[:100] if bot_response else 'None/Empty'}...")
                conversation.retry_offered_at = None
                save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                sent = send_bot_response(db, client.id, remote_jid, bot_response)
                result_message = "Message sent" if sent else "Failed to send"
            else:
                result_message = "No response generated"
    else:
        result_message = f"Unknown state: {conversation.state}"

    db.commit()

    return WebhookResponse(
        success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
    )
