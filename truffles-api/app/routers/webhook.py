import asyncio
import hmac
import os
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.logging_config import get_logger
from app.models import Client, ClientSettings, Conversation, Handover, Message
from app.schemas.webhook import WebhookRequest, WebhookResponse
from app.services.chatflow_service import send_bot_response
from app.services.conversation_service import (
    get_or_create_conversation,
    get_or_create_user,
)
from app.services.alert_service import alert_warning
from app.services.escalation_service import get_telegram_credentials, send_telegram_notification
from app.services.ai_service import (
    BOT_STATUS_RESPONSE,
    GREETING_RESPONSE,
    OUT_OF_DOMAIN_RESPONSE,
    THANKS_RESPONSE,
    classify_confirmation,
    is_acknowledgement_message,
    is_bot_status_question,
    is_greeting_message,
    is_low_signal_message,
    is_thanks_message,
)
from app.services.intent_service import (
    DomainIntent,
    Intent,
    classify_domain_with_scores,
    classify_intent,
    is_rejection,
    should_escalate,
)
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


WEBHOOK_SECRET_HEADER = "X-Webhook-Secret"
WEBHOOK_SECRET_QUERY_PARAM = "webhook_secret"
WEBHOOK_SECRET_QUERY_FALLBACK = "secret"

# Webhook auth (ChatFlow/n8n) quick guide:
# 1) Issue secret: `openssl rand -hex 16` -> store in client_settings.webhook_secret.
# 2) Configure webhook URL (n8n -> API):
#    - Preferred header: X-Webhook-Secret: <secret>
#    - Fallback URL: /webhook/<secret> OR /webhook?webhook_secret=<secret> (or ?secret=...)
# 3) Rotation: set new secret in DB, update ChatFlow/n8n config; old secret invalid immediately.


def _verify_webhook_secret(provided: str | None, expected: str | None) -> bool:
    if not expected or not provided:
        return False
    return hmac.compare_digest(provided, expected)


def _extract_webhook_secret(
    http_request: Request,
    *,
    path_secret: str | None,
    query_secret: str | None,
    query_webhook_secret: str | None,
) -> tuple[str | None, str]:
    header_secret = http_request.headers.get(WEBHOOK_SECRET_HEADER)
    if header_secret:
        return header_secret, "header"
    if query_webhook_secret:
        return query_webhook_secret, f"query:{WEBHOOK_SECRET_QUERY_PARAM}"
    if query_secret:
        return query_secret, f"query:{WEBHOOK_SECRET_QUERY_FALLBACK}"
    if path_secret:
        return path_secret, "path"
    return None, "missing"


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

    # Persistent dedup in DB (message_dedup) to survive restarts/retries.
    try:
        result = db.execute(
            text(
                """
                INSERT INTO message_dedup (client_id, message_id)
                VALUES (:client_id, :message_id)
                ON CONFLICT DO NOTHING
                """
            ),
            {"client_id": client_id, "message_id": message_id},
        )
        db.commit()
        if result.rowcount == 0:
            logger.info(
                "Duplicate message_id (DB)",
                extra={"context": {"client_id": str(client_id), "message_id": message_id}},
            )
            return True
    except Exception as e:
        logger.warning(
            "DB dedup check failed, falling back to messages table",
            extra={"context": {"client_id": str(client_id), "message_id": message_id, "error": str(e)}},
        )

    duplicate = (
        db.query(Message)
        .filter(
            Message.client_id == client_id,
            Message.message_metadata["message_id"].astext == message_id,
        )
        .first()
    )
    if duplicate:
        logger.info(
            "Duplicate message_id (messages table)",
            extra={"context": {"client_id": str(client_id), "message_id": message_id}},
        )
    return duplicate is not None

# Default values (can be overridden in client_settings)
DEFAULT_MUTE_DURATION_FIRST_MINUTES = 30
DEFAULT_MUTE_DURATION_SECOND_HOURS = 24
SESSION_TIMEOUT_HOURS = 24
LOW_CONFIDENCE_RETRY_WINDOW_MINUTES = 10
LOW_CONFIDENCE_MAX_RETRIES = 2
HANDOVER_CONFIRM_WINDOW_MINUTES = 15
MSG_ESCALATED = "Передал менеджеру. Могу чем-то помочь пока ждёте?"
MSG_MUTED_TEMP = "Хорошо, напишите если понадоблюсь."
MSG_MUTED_LONG = "Понял! Если ответа от менеджеров долго нет — лучше звоните напрямую: +7 775 984 19 26"
MSG_LOW_CONFIDENCE = "Хороший вопрос! Уточню у коллег и вернусь с ответом."
MSG_HANDOVER_CONFIRM = "Не уверен, что понял. Подключить менеджера? Ответьте 'да' или 'нет'."
MSG_HANDOVER_DECLINED = (
    "Ок. Напишите, что именно интересует по салону: цена/запись/адрес/мастер/жалоба."
)
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

MSG_BOOKING_ASK_SERVICE = "На какую услугу хотите записаться?"
MSG_BOOKING_ASK_DATETIME = "На какую дату и время вам удобно?"
MSG_BOOKING_ASK_NAME = "Как вас зовут?"
MSG_BOOKING_CANCELLED = "Хорошо, если передумаете — пишите."


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


BOOKING_REQUEST_KEYWORDS = [
    "запис",
    "запись",
    "запишите",
    "записаться",
    "бронь",
    "окошк",
    "свободн",
]

BOOKING_CANCEL_KEYWORDS = [
    "не надо запис",
    "не хочу запис",
    "передумал",
    "передумала",
    "не буду запис",
    "отмена записи",
]

SERVICE_KEYWORDS = [
    "маникюр",
    "педикюр",
    "стриж",
    "окраш",
    "мелирован",
    "кератин",
    "ботокс",
    "бров",
    "ресниц",
    "депиляц",
    "шугар",
    "воск",
    "чистк",
    "пилинг",
    "макияж",
    "укладк",
    "прическ",
    "наращив",
    "лак",
]

DATE_KEYWORDS = [
    "сегодня",
    "завтра",
    "послезавтра",
    "понедель",
    "вторник",
    "сред",
    "четверг",
    "пятниц",
    "суббот",
    "воскрес",
    "утром",
    "днем",
    "днём",
    "вечером",
]

TIME_PATTERN = re.compile(r"\b\d{1,2}[:.]\d{2}\b")
NAME_PATTERN = re.compile(r"\bменя зовут\s+([a-zа-яё-]{2,})", re.IGNORECASE)


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    normalized = text.strip().casefold()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _contains_any(normalized: str, keywords: list[str]) -> bool:
    return any(keyword in normalized for keyword in keywords)


def _is_booking_request(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    return _contains_any(normalized, BOOKING_REQUEST_KEYWORDS)


def _is_booking_cancel(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    return _contains_any(normalized, BOOKING_CANCEL_KEYWORDS)


def _extract_service(text: str) -> str | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None
    if _contains_any(normalized, SERVICE_KEYWORDS):
        return text.strip()
    return None


def _extract_datetime(text: str) -> str | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None
    if _contains_any(normalized, DATE_KEYWORDS) or TIME_PATTERN.search(text):
        return text.strip()
    return None


def _get_conversation_context(conversation: Conversation) -> dict:
    context = conversation.context or {}
    if isinstance(context, dict):
        return dict(context)
    return {}


def _set_conversation_context(conversation: Conversation, context: dict) -> None:
    conversation.context = context


def _get_low_confidence_retry_count(context: dict) -> int:
    value = context.get("low_confidence_retry_count", 0) if isinstance(context, dict) else 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _set_low_confidence_retry_count(context: dict, count: int) -> dict:
    context = dict(context)
    context["low_confidence_retry_count"] = max(0, int(count))
    return context


def _reset_low_confidence_retry(conversation: Conversation) -> None:
    context = _get_conversation_context(conversation)
    if context.get("low_confidence_retry_count"):
        context = _set_low_confidence_retry_count(context, 0)
        _set_conversation_context(conversation, context)
    conversation.retry_offered_at = None


def _get_handover_confirmation(context: dict) -> dict | None:
    confirmation = context.get("handover_confirmation") if isinstance(context, dict) else None
    if isinstance(confirmation, dict):
        return dict(confirmation)
    return None


def _set_handover_confirmation(context: dict, confirmation: dict | None) -> dict:
    context = dict(context)
    if confirmation:
        context["handover_confirmation"] = confirmation
    else:
        context.pop("handover_confirmation", None)
    return context


def _is_handover_confirmation_active(confirmation: dict, now: datetime) -> bool:
    asked_at_raw = confirmation.get("asked_at")
    if not asked_at_raw:
        return False
    try:
        asked_at = datetime.fromisoformat(asked_at_raw)
    except (TypeError, ValueError):
        return False
    if asked_at.tzinfo is None:
        asked_at = asked_at.replace(tzinfo=timezone.utc)
    return (now - asked_at) <= timedelta(minutes=HANDOVER_CONFIRM_WINDOW_MINUTES)


def _get_booking_context(context: dict) -> dict:
    booking = context.get("booking") if isinstance(context, dict) else None
    if isinstance(booking, dict):
        return dict(booking)
    return {}


def _set_booking_context(context: dict, booking: dict) -> dict:
    context = dict(context)
    context["booking"] = booking
    return context


def _update_booking_from_message(booking: dict, message_text: str) -> dict:
    booking = dict(booking)
    last_question = booking.get("last_question")

    if last_question == "service" and not booking.get("service"):
        if not is_low_signal_message(message_text):
            booking["service"] = message_text.strip()
    if last_question == "datetime" and not booking.get("datetime"):
        if not is_low_signal_message(message_text):
            booking["datetime"] = message_text.strip()
    if last_question == "name" and not booking.get("name"):
        booking["name"] = message_text.strip()

    if not booking.get("name"):
        name_match = NAME_PATTERN.search(message_text)
        if name_match:
            booking["name"] = name_match.group(1).strip()

    if not booking.get("service"):
        detected_service = _extract_service(message_text)
        if detected_service:
            booking["service"] = detected_service

    if not booking.get("datetime"):
        detected_datetime = _extract_datetime(message_text)
        if detected_datetime:
            booking["datetime"] = detected_datetime

    return booking


def _next_booking_prompt(booking: dict) -> tuple[dict, str | None]:
    booking = dict(booking)
    if not booking.get("service"):
        booking["last_question"] = "service"
        return booking, MSG_BOOKING_ASK_SERVICE
    if not booking.get("datetime"):
        booking["last_question"] = "datetime"
        return booking, MSG_BOOKING_ASK_DATETIME
    if not booking.get("name"):
        booking["last_question"] = "name"
        return booking, MSG_BOOKING_ASK_NAME
    booking["last_question"] = None
    return booking, None


def _build_booking_summary(booking: dict) -> str:
    service = booking.get("service") or "не указано"
    datetime_pref = booking.get("datetime") or "не указано"
    name = booking.get("name") or "не указано"
    return f"Запись: услуга={service}; дата/время={datetime_pref}; имя={name}."


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


@router.post("/webhook/{path_secret}", response_model=WebhookResponse)
async def handle_webhook_with_secret(
    path_secret: str,
    payload: WebhookRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    return await _handle_webhook(payload, http_request, db, path_secret=path_secret)


@router.post("/webhook", response_model=WebhookResponse)
async def handle_webhook(
    payload: WebhookRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    webhook_secret: str | None = None,
    secret: str | None = None,
):
    return await _handle_webhook(
        payload,
        http_request,
        db,
        webhook_secret=webhook_secret,
        secret=secret,
    )


async def _handle_webhook(
    payload: WebhookRequest,
    http_request: Request,
    db: Session,
    *,
    path_secret: str | None = None,
    secret: str | None = None,
    webhook_secret: str | None = None,
):
    """Handle raw webhook from n8n (same format as ChatFlow webhook)."""
    logger.info(f"Webhook received: client_slug={payload.client_slug}")

    body = payload.body
    # Get client by slug
    client = db.query(Client).filter(Client.name == payload.client_slug).first()
    if not client:
        return WebhookResponse(success=False, message=f"Client '{payload.client_slug}' not found")

    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client.id).first()
    expected_secret = settings.webhook_secret if settings else None
    provided_secret, secret_source = _extract_webhook_secret(
        http_request,
        path_secret=path_secret,
        query_secret=secret,
        query_webhook_secret=webhook_secret,
    )

    if not expected_secret:
        logger.warning(f"Webhook secret missing: client_slug={payload.client_slug} source={secret_source}")
        alert_warning("Webhook secret missing", {"client_slug": payload.client_slug})
    elif not _verify_webhook_secret(provided_secret, expected_secret):
        reason = "missing_secret" if not provided_secret else "invalid_secret"
        logger.warning(f"Webhook auth failed: client_slug={payload.client_slug} reason={reason} source={secret_source}")
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    metadata = body.metadata

    if not metadata or not metadata.remoteJid:
        return WebhookResponse(success=False, message="Missing metadata.remoteJid")

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
            conversation.context = {}
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
    append_user_message = True
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
            logger.info(
                "Debounced intermediate message",
                extra={"context": {"remote_jid": remote_jid, "message_id": message_id}},
            )
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
                logger.info(
                    "Debounce buffer drained",
                    extra={
                        "context": {
                            "remote_jid": remote_jid,
                            "message_id": message_id,
                            "buffered_count": len(buffered_messages),
                        }
                    },
                )
                message_text = " ".join(buffered_messages)
                append_user_message = False

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

    # 9.02 Pending handover confirmation before other flows.
    if conversation.state == ConversationState.BOT_ACTIVE.value:
        context = _get_conversation_context(conversation)
        confirmation = _get_handover_confirmation(context)
        if confirmation:
            if not _is_handover_confirmation_active(confirmation, now):
                context = _set_handover_confirmation(context, None)
                _set_conversation_context(conversation, context)
            else:
                decision = classify_confirmation(message_text)
                if decision == "yes":
                    context = _set_handover_confirmation(context, None)
                    _set_conversation_context(conversation, context)
                    _reset_low_confidence_retry(conversation)

                    escalation_message = confirmation.get("user_message") or message_text
                    esc_result = escalate_to_pending(
                        db=db,
                        conversation=conversation,
                        user_message=escalation_message,
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
                            message=escalation_message,
                        )
                        bot_response = MSG_ESCALATED
                        result_message = (
                            f"Handover confirmed, telegram={'sent' if telegram_sent else 'failed'}"
                        )
                    else:
                        bot_response = MSG_AI_ERROR
                        result_message = f"Handover confirm escalation failed: {esc_result.error}"

                    save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                    sent = send_bot_response(db, client.id, remote_jid, bot_response)
                    if not sent:
                        result_message = f"{result_message}; response_send=failed"
                    db.commit()
                    return WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    )

                if decision == "no":
                    context = _set_handover_confirmation(context, None)
                    _set_conversation_context(conversation, context)
                    _reset_low_confidence_retry(conversation)

                    bot_response = MSG_HANDOVER_DECLINED
                    save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                    sent = send_bot_response(db, client.id, remote_jid, bot_response)
                    result_message = "Handover declined, asked for salon details" if sent else "Handover decline send failed"
                    db.commit()
                    return WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    )

                context = _set_handover_confirmation(context, None)
                _set_conversation_context(conversation, context)

    # 9.05 Booking flow: collect slots before intent/LLM.
    if conversation.state == ConversationState.BOT_ACTIVE.value:
        context = _get_conversation_context(conversation)
        booking = _get_booking_context(context)
        booking_active = bool(booking.get("active"))

        if booking_active and _is_booking_cancel(message_text):
            booking = {"active": False}
            context = _set_booking_context(context, booking)
            _set_conversation_context(conversation, context)
            bot_response = MSG_BOOKING_CANCELLED
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = send_bot_response(db, client.id, remote_jid, bot_response)
            result_message = "Booking cancelled" if sent else "Booking cancel response failed"
            db.commit()
            return WebhookResponse(
                success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
            )

        if booking_active or _is_booking_request(message_text):
            if not booking_active:
                booking = dict(booking)
                booking["active"] = True
                booking["started_at"] = now.isoformat()

            booking = _update_booking_from_message(booking, message_text)
            booking, prompt = _next_booking_prompt(booking)
            context = _set_booking_context(context, booking)
            _set_conversation_context(conversation, context)

            if prompt:
                bot_response = prompt
                save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                sent = send_bot_response(db, client.id, remote_jid, bot_response)
                result_message = "Booking slot requested" if sent else "Booking slot response failed"
                db.commit()
                return WebhookResponse(
                    success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
                )

            booking_summary = _build_booking_summary(booking)
            result = escalate_to_pending(
                db=db,
                conversation=conversation,
                user_message=booking_summary,
                trigger_type="intent",
                trigger_value="booking",
            )

            if result.ok:
                handover = result.value
                telegram_sent = send_telegram_notification(
                    db=db,
                    handover=handover,
                    conversation=conversation,
                    user=user,
                    message=booking_summary,
                )
                bot_response = MSG_ESCALATED
                result_message = f"Booking escalation, telegram={'sent' if telegram_sent else 'failed'}"
            else:
                bot_response = MSG_AI_ERROR
                result_message = f"Booking escalation failed: {result.error}"

            context = _set_booking_context(context, {"active": False})
            _set_conversation_context(conversation, context)
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = send_bot_response(db, client.id, remote_jid, bot_response)
            if not sent:
                result_message = f"{result_message}; response_send=failed"
            db.commit()
            return WebhookResponse(
                success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
            )

    # 10. Classify intent (expensive). Protect against accidental escalations on short/noisy messages.
    is_greeting = is_greeting_message(message_text)
    is_thanks = is_thanks_message(message_text)
    is_ack = is_acknowledgement_message(message_text)
    is_low_signal = is_low_signal_message(message_text)
    is_status_question = is_bot_status_question(message_text)

    if is_greeting:
        intent = Intent.GREETING
        logger.info("Intent shortcut: greeting")
    elif is_thanks:
        intent = Intent.THANKS
        logger.info("Intent shortcut: thanks")
    elif is_ack or is_low_signal:
        intent = Intent.OTHER
        logger.info("Intent shortcut: acknowledgement/low-signal -> other")
    else:
        intent = classify_intent(message_text)
        logger.info(f"Intent classified: {intent.value}")

    domain_intent = DomainIntent.UNKNOWN
    domain_in_score = 0.0
    domain_out_score = 0.0
    domain_meta: dict = {}
    if (
        conversation.state == ConversationState.BOT_ACTIVE.value
        and not (is_greeting or is_thanks or is_ack or is_low_signal)
        and not is_status_question
    ):
        domain_intent, domain_in_score, domain_out_score, domain_meta = classify_domain_with_scores(
            message_text, client.config if client else None
        )
        log_scores = _is_env_enabled(os.environ.get("DOMAIN_ROUTER_LOG_SCORES"), default=False)
        if log_scores and (domain_intent != DomainIntent.UNKNOWN or max(domain_in_score, domain_out_score) >= 0.45):
            logger.info(
                "Domain scores",
                extra={
                    "context": {
                        "client_slug": request.client_slug,
                        "remote_jid": remote_jid,
                        "intent": intent.value,
                        "domain_intent": domain_intent.value,
                        "in_score": round(domain_in_score, 4),
                        "out_score": round(domain_out_score, 4),
                        "in_threshold": domain_meta.get("in_threshold"),
                        "out_threshold": domain_meta.get("out_threshold"),
                        "margin": domain_meta.get("margin"),
                        "anchors_in": domain_meta.get("anchors_in"),
                        "anchors_out": domain_meta.get("anchors_out"),
                        "message_len": len(message_text),
                        "message_preview": message_text[:80],
                    }
                },
            )

    # 10.1 Self-healing moved to health_service.check_and_heal_conversations()
    # Call POST /admin/heal periodically to fix broken states

    # 9.1 Greeting/thanks: always respond politely without escalation
    if intent in [Intent.GREETING, Intent.THANKS]:
        bot_response = GREETING_RESPONSE if intent == Intent.GREETING else THANKS_RESPONSE
        _reset_low_confidence_retry(conversation)
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

    # 9.3 Bot status questions: respond without escalation
    if is_status_question:
        bot_response = BOT_STATUS_RESPONSE
        _reset_low_confidence_retry(conversation)
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = send_bot_response(db, client.id, remote_jid, bot_response)
        result_message = "Bot status response sent" if sent else "Bot status response failed"
        db.commit()
        return WebhookResponse(
            success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
        )

    # 9.35 Domain routing: respond to off-topic messages without escalation
    if domain_intent == DomainIntent.OUT_OF_DOMAIN and conversation.state == ConversationState.BOT_ACTIVE.value:
        bot_response = OUT_OF_DOMAIN_RESPONSE
        _reset_low_confidence_retry(conversation)
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = send_bot_response(db, client.id, remote_jid, bot_response)
        result_message = "Domain out-of-domain response sent" if sent else "Domain out-of-domain response failed"
        db.commit()
        return WebhookResponse(
            success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
        )

    # 9.4 Out-of-domain: respond without escalation
    if intent == Intent.OUT_OF_DOMAIN and conversation.state == ConversationState.BOT_ACTIVE.value:
        bot_response = OUT_OF_DOMAIN_RESPONSE
        _reset_low_confidence_retry(conversation)
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = send_bot_response(db, client.id, remote_jid, bot_response)
        result_message = "Out-of-domain response sent" if sent else "Out-of-domain response failed"
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
            gen_result = generate_bot_response(
                db,
                conversation,
                message_text,
                request.client_slug,
                append_user_message=append_user_message,
            )
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
        gen_result = generate_bot_response(
            db,
            conversation,
            message_text,
            request.client_slug,
            append_user_message=append_user_message,
        )

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
                    # Low RAG confidence — ask clarifying question before escalation (up to a limit).
                    context = _get_conversation_context(conversation)
                    retry_count = _get_low_confidence_retry_count(context)
                    if should_offer_low_confidence_retry(conversation, now):
                        retry_count = 0

                    if retry_count < LOW_CONFIDENCE_MAX_RETRIES:
                        bot_response = MSG_LOW_CONFIDENCE_RETRY
                        conversation.retry_offered_at = now
                        context = _set_low_confidence_retry_count(context, retry_count + 1)
                        _set_conversation_context(conversation, context)
                        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                        sent = send_bot_response(db, client.id, remote_jid, bot_response)
                        result_message = "Low confidence: asked clarification before escalation"
                    else:
                        confirmation = {
                            "status": "pending",
                            "asked_at": now.isoformat(),
                            "trigger_type": "low_confidence",
                            "trigger_value": "low_confidence",
                            "user_message": message_text,
                        }
                        context = _set_handover_confirmation(context, confirmation)
                        _set_conversation_context(conversation, context)

                        bot_response = MSG_HANDOVER_CONFIRM
                        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                        sent = send_bot_response(db, client.id, remote_jid, bot_response)
                        result_message = (
                            "Low confidence: asked for handover confirmation"
                            if sent
                            else "Low confidence: handover confirmation send failed"
                        )

            elif confidence == "bot_inactive":
                result_message = f"Bot not active (state: {conversation.state})"

            elif response_text:
                bot_response = response_text
                logger.debug(f"bot_response: {bot_response[:100] if bot_response else 'None/Empty'}...")
                _reset_low_confidence_retry(conversation)
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
