import asyncio
import os
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.requests import ClientDisconnect

from app.database import get_db
from app.logging_config import get_logger
from app.models import Branch, Client, ClientSettings, Conversation, Handover, Message, User
from app.schemas.webhook import WebhookRequest, WebhookResponse
from app.services.ai_service import (
    BOT_STATUS_RESPONSE,
    GREETING_RESPONSE,
    OUT_OF_DOMAIN_RESPONSE,
    THANKS_RESPONSE,
    classify_confirmation,
    get_rag_confidence,
    is_acknowledgement_message,
    is_bot_status_question,
    is_greeting_message,
    is_low_signal_message,
    is_thanks_message,
)
from app.services.alert_service import alert_warning
from app.services.chatflow_service import send_bot_response
from app.services.conversation_service import (
    get_or_create_conversation,
    get_or_create_user,
)
from app.services.demo_salon_knowledge import get_demo_salon_decision
from app.services.escalation_service import get_telegram_credentials, send_telegram_notification
from app.services.intent_service import (
    DomainIntent,
    Intent,
    classify_domain_with_scores,
    classify_intent,
    is_rejection,
    is_strong_out_of_domain,
    should_escalate,
)
from app.services.message_service import generate_bot_response, save_message, select_handover_user_message
from app.services.outbox_service import build_inbound_message_id, enqueue_outbox_message, mark_outbox_status
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


def _coerce_remote_jid(value) -> str | None:
    if not value or isinstance(value, (dict, list, tuple)):
        return None
    text = str(value).strip()
    if not text:
        return None
    if "@" in text:
        return text
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    return f"{digits}@s.whatsapp.net"


def _normalize_chatflow_payload(payload: dict, client_slug: str | None) -> tuple[dict, str]:
    body = payload.get("body")
    if not isinstance(body, dict):
        body = payload

    body = dict(body)
    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}

    candidate = payload
    remote_jid = metadata.get("remoteJid")
    if not remote_jid:
        for key in ("remoteJid", "remote_jid", "jid", "from", "chatId", "session_id", "user_id", "phone"):
            remote_jid = candidate.get(key)
            if remote_jid:
                break
    remote_jid = _coerce_remote_jid(remote_jid)
    if remote_jid:
        metadata.setdefault("remoteJid", remote_jid)

    message_id = metadata.get("messageId")
    if not message_id:
        for key in ("messageId", "message_id", "id"):
            message_id = candidate.get(key)
            if message_id:
                break

    msg_obj = candidate.get("message") if isinstance(candidate.get("message"), dict) else None
    if not message_id and msg_obj:
        message_id = msg_obj.get("id") or msg_obj.get("messageId")
    if message_id:
        metadata.setdefault("messageId", message_id)

    timestamp = metadata.get("timestamp")
    if not timestamp:
        for key in ("timestamp", "t", "time"):
            timestamp = candidate.get(key)
            if timestamp:
                break
    if timestamp:
        metadata.setdefault("timestamp", timestamp)

    sender = metadata.get("sender")
    if not sender:
        for key in ("sender", "pushName", "name"):
            sender = candidate.get(key)
            if sender:
                break
    if sender:
        metadata.setdefault("sender", sender)

    instance_id = metadata.get("instanceId") or metadata.get("instance_id")
    if not instance_id:
        for key in ("instanceId", "instance_id", "instance", "whatsapp_instance_id"):
            instance_id = candidate.get(key)
            if instance_id:
                break
    if not instance_id:
        node_data = candidate.get("nodeData") or body.get("nodeData")
        if isinstance(node_data, dict):
            for key in ("instanceId", "instance_id", "instance", "whatsapp_instance_id"):
                instance_id = node_data.get(key)
                if instance_id:
                    break
    if instance_id:
        metadata.setdefault("instanceId", instance_id)

    message = body.get("message")
    if not isinstance(message, str) or not message.strip():
        message = None
        for key in ("text", "body", "message_text", "content"):
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                message = value
                break
        if not message and msg_obj:
            for key in ("text", "body", "message", "content"):
                value = msg_obj.get(key)
                if isinstance(value, str) and value.strip():
                    message = value
                    break
    if message:
        body["message"] = message

    body["metadata"] = metadata
    slug = client_slug or payload.get("client_slug") or "truffles"
    return body, slug


async def _parse_webhook_request(
    request: Request,
    *,
    client_slug: str | None = None,
) -> WebhookRequest | WebhookResponse:
    try:
        payload = await request.json()
    except ClientDisconnect:
        logger.info("Webhook client disconnected during read", extra={"context": {"client_slug": client_slug}})
        return WebhookResponse(success=True, message="Client disconnected")
    except Exception as exc:
        try:
            raw = await request.body()
        except ClientDisconnect:
            logger.info("Webhook client disconnected during body read", extra={"context": {"client_slug": client_slug}})
            return WebhookResponse(success=True, message="Client disconnected")
        if not raw or not raw.strip():
            logger.info("Webhook probe with empty body", extra={"context": {"client_slug": client_slug}})
            return WebhookResponse(success=True, message="Empty payload")

        logger.warning(
            "Webhook payload is not valid JSON",
            extra={
                "context": {
                    "error": str(exc),
                    "body_preview": raw[:200].decode("utf-8", "ignore"),
                }
            },
        )
        return WebhookResponse(success=False, message="Invalid JSON payload")

    if not isinstance(payload, dict):
        return WebhookResponse(success=False, message="Invalid payload format")

    body, slug = _normalize_chatflow_payload(payload, client_slug)

    query_instance_id = (
        request.query_params.get("instanceId")
        or request.query_params.get("instance_id")
        or request.query_params.get("instance")
    )
    if query_instance_id:
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
        metadata.setdefault("instanceId", query_instance_id)
        body["metadata"] = metadata

    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
    if not metadata.get("remoteJid") or not body.get("message"):
        logger.info(
            "Webhook payload missing expected fields",
            extra={
                "context": {
                    "client_slug": slug,
                    "payload_keys": list(payload.keys())[:20],
                    "body_keys": list(body.keys())[:20],
                    "metadata_keys": list(metadata.keys())[:20],
                    "has_message": bool(body.get("message")),
                }
            },
        )

    try:
        return WebhookRequest(body=body, client_slug=slug)
    except Exception as exc:
        logger.warning("Webhook payload validation failed", extra={"context": {"error": str(exc)}})
        return WebhookResponse(success=False, message="Invalid webhook payload")


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


BRANCH_SELECTION_KEY = "branch_selection"
BRANCH_CONTEXT_KEY = "branch_id"
MSG_BRANCH_SELECTED = "Отлично, выбрали филиал {branch_name}. Чем могу помочь?"


def _coerce_uuid(value) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _get_branch_selection(context: dict) -> dict | None:
    selection = context.get(BRANCH_SELECTION_KEY) if isinstance(context, dict) else None
    if isinstance(selection, dict):
        return dict(selection)
    return None


def _set_branch_selection(context: dict, selection: dict | None) -> dict:
    context = dict(context)
    if selection:
        context[BRANCH_SELECTION_KEY] = selection
    else:
        context.pop(BRANCH_SELECTION_KEY, None)
    return context


def _get_user_metadata(user: User) -> dict:
    metadata = user.user_metadata if isinstance(user.user_metadata, dict) else {}
    return dict(metadata)


def _get_user_branch_preference(user: User) -> UUID | None:
    metadata = _get_user_metadata(user)
    return _coerce_uuid(metadata.get(BRANCH_CONTEXT_KEY))


def _set_user_branch_preference(user: User, branch_id: UUID) -> None:
    metadata = _get_user_metadata(user)
    metadata[BRANCH_CONTEXT_KEY] = str(branch_id)
    user.user_metadata = metadata


def _get_active_branches(db: Session, client_id) -> list[Branch]:
    return (
        db.query(Branch)
        .filter(Branch.client_id == client_id, Branch.is_active == True)
        .order_by(Branch.name.asc())
        .all()
    )


def _build_branch_prompt(branches: list[Branch]) -> str:
    lines = ["Пожалуйста, выберите филиал:"]
    for idx, branch in enumerate(branches, start=1):
        label = branch.name or branch.slug or f"Филиал {idx}"
        lines.append(f"{idx}) {label}")
    lines.append("Ответьте номером или названием филиала.")
    return "\n".join(lines)


def _build_branch_selection(branches: list[Branch], now: datetime) -> dict:
    return {
        "options": [str(branch.id) for branch in branches],
        "asked_at": now.isoformat(),
    }


def _match_branch_choice(
    message_text: str,
    branches: list[Branch],
    selection: dict | None,
) -> tuple[Branch | None, bool]:
    normalized = _normalize_text(message_text)
    if not normalized:
        return None, False

    if normalized.isdigit():
        index = int(normalized)
        options = selection.get("options") if isinstance(selection, dict) else None
        if isinstance(options, list) and 1 <= index <= len(options):
            target_id = _coerce_uuid(options[index - 1])
            if target_id:
                for branch in branches:
                    if branch.id == target_id:
                        return branch, True
        if 1 <= index <= len(branches):
            return branches[index - 1], True

    for branch in branches:
        name_norm = _normalize_text(branch.name or "")
        slug_norm = _normalize_text(branch.slug or "")
        if name_norm and name_norm in normalized:
            return branch, False
        if slug_norm and slug_norm in normalized:
            return branch, False
    return None, False


def _is_branch_only_message(message_text: str, branch: Branch, selected_by_index: bool) -> bool:
    normalized = _normalize_text(message_text)
    if not normalized:
        return False
    if selected_by_index and normalized.isdigit():
        return True
    if branch.name and normalized == _normalize_text(branch.name):
        return True
    if branch.slug and normalized == _normalize_text(branch.slug):
        return True
    return False


def _apply_branch_selection(
    *,
    conversation: Conversation,
    user: User,
    branch: Branch,
    context: dict,
    remember_branch: bool,
) -> None:
    updated_context = dict(context)
    updated_context[BRANCH_CONTEXT_KEY] = str(branch.id)
    updated_context.pop(BRANCH_SELECTION_KEY, None)
    _set_conversation_context(conversation, updated_context)
    conversation.branch_id = branch.id
    if remember_branch:
        _set_user_branch_preference(user, branch.id)


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


def _get_client_webhook_secret(settings: ClientSettings | None) -> str | None:
    if not settings:
        return None
    secret = getattr(settings, "webhook_secret", None)
    if not secret:
        return None
    cleaned = str(secret).strip()
    return cleaned or None


def _get_request_webhook_secret(request: Request) -> str | None:
    header_secret = request.headers.get("X-Webhook-Secret")
    if header_secret:
        return header_secret.strip()
    query_secret = request.query_params.get("webhook_secret")
    if query_secret:
        return query_secret.strip()
    return None


async def _process_outbox_rows(
    db: Session,
    rows: list[dict],
    *,
    max_attempts: int,
    retry_backoff_seconds: float,
) -> dict[str, int]:
    results = {"claimed": len(rows), "sent": 0, "failed": 0, "retry_scheduled": 0}
    if not rows:
        return results

    batches: dict[str, list[dict]] = {}
    for row in rows:
        conversation_id = row.get("conversation_id")
        if not conversation_id:
            continue
        batches.setdefault(str(conversation_id), []).append(row)

    for conversation_id, batch in batches.items():
        batch_sorted = sorted(
            batch,
            key=lambda r: r.get("created_at")
            if isinstance(r.get("created_at"), datetime)
            else datetime.min.replace(tzinfo=timezone.utc),
        )
        outbox_ids = [row.get("id") for row in batch_sorted]
        message_texts = []
        for row in batch_sorted:
            payload_json = row.get("payload_json") or {}
            try:
                payload = WebhookRequest.model_validate(payload_json)
            except Exception:
                continue
            text = payload.body.message or ""
            if text.strip():
                message_texts.append(text.strip())

        base_payload = WebhookRequest.model_validate(batch_sorted[-1].get("payload_json") or {})
        combined_text = " ".join(message_texts).strip()
        if combined_text:
            base_payload.body.message = combined_text

        logger.info(
            "Outbox processing start",
            extra={
                "context": {
                    "outbox_ids": [str(oid) for oid in outbox_ids if oid],
                    "conversation_id": conversation_id,
                    "attempts": batch_sorted[-1].get("attempts"),
                    "coalesced_count": len(batch_sorted),
                }
            },
        )

        try:
            response = await _handle_webhook_payload(
                base_payload,
                db,
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=UUID(conversation_id),
            )
            if not response.success:
                raise RuntimeError(response.message)
            for outbox_id in outbox_ids:
                if outbox_id:
                    mark_outbox_status(
                        db,
                        outbox_id=outbox_id,
                        status="SENT",
                        last_error=None,
                        next_attempt_at=None,
                    )
            results["sent"] += len(outbox_ids)
            logger.info(
                "Outbox processed",
                extra={"context": {"conversation_id": conversation_id, "coalesced_count": len(batch_sorted)}},
            )
        except Exception as exc:
            now = datetime.now(timezone.utc)
            for row in batch_sorted:
                outbox_id = row.get("id")
                if not outbox_id:
                    continue
                attempts = int(row.get("attempts") or 0)
                if attempts >= max_attempts:
                    mark_outbox_status(
                        db,
                        outbox_id=outbox_id,
                        status="FAILED",
                        last_error=str(exc)[:500],
                        next_attempt_at=None,
                    )
                    results["failed"] += 1
                    continue
                backoff = retry_backoff_seconds * (2 ** max(attempts - 1, 0))
                next_attempt_at = now + timedelta(seconds=backoff)
                mark_outbox_status(
                    db,
                    outbox_id=outbox_id,
                    status="PENDING",
                    last_error=str(exc)[:500],
                    next_attempt_at=next_attempt_at,
                )
                results["retry_scheduled"] += 1
            logger.error(
                "Outbox processing failed",
                extra={
                    "context": {
                        "conversation_id": conversation_id,
                        "error": str(exc),
                        "coalesced_count": len(batch_sorted),
                    }
                },
            )

    return results


@router.post("/webhook/debug")
async def debug_webhook(request: Request):
    """Debug endpoint to see raw request."""
    body = await request.json()
    logger.debug(f"DEBUG webhook body: {body}")
    return {"received": body}


@router.post("/webhook/{client_slug}", response_model=WebhookResponse)
async def handle_webhook_direct(client_slug: str, request: Request, db: Session = Depends(get_db)):
    """Handle direct ChatFlow webhook without wrapper."""
    parsed = await _parse_webhook_request(request, client_slug=client_slug)
    if isinstance(parsed, WebhookResponse):
        return parsed

    provided_secret = _get_request_webhook_secret(request)
    client = db.query(Client).filter(Client.name == parsed.client_slug).first()
    if not client:
        return WebhookResponse(success=False, message=f"Client '{parsed.client_slug}' not found")

    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client.id).first()
    expected_secret = _get_client_webhook_secret(settings)
    if expected_secret:
        if not provided_secret or provided_secret != expected_secret:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")
    elif not provided_secret:
        alert_warning("Webhook secret missing", {"client_slug": parsed.client_slug})

    return await _handle_webhook_payload(
        parsed,
        db,
        provided_secret=provided_secret,
        enforce_secret=False,
        enqueue_only=True,
    )


@router.get("/webhook/{client_slug}")
async def handle_webhook_probe(client_slug: str):
    """Health probe for ChatFlow UI checks; real webhooks must use POST."""
    return {"ok": True, "message": "Use POST with JSON payload", "client_slug": client_slug}


@router.post("/webhook", response_model=WebhookResponse)
async def handle_webhook(payload: WebhookRequest, http_request: Request, db: Session = Depends(get_db)):
    """Handle legacy webhook wrapper (same format as ChatFlow webhook)."""
    provided_secret = _get_request_webhook_secret(http_request)
    return await _handle_webhook_payload(
        payload,
        db,
        provided_secret=provided_secret,
        enforce_secret=True,
        enqueue_only=True,
    )


async def _handle_webhook_payload(
    payload: WebhookRequest,
    db: Session,
    *,
    provided_secret: str | None,
    enforce_secret: bool,
    enqueue_only: bool = False,
    skip_persist: bool = False,
    conversation_id: UUID | None = None,
) -> WebhookResponse:
    """Shared webhook processing for inbound ChatFlow payloads."""
    logger.info(f"Webhook received: client_slug={payload.client_slug}")

    # Get client by slug
    client = db.query(Client).filter(Client.name == payload.client_slug).first()
    if not client:
        return WebhookResponse(success=False, message=f"Client '{payload.client_slug}' not found")

    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client.id).first()
    if enforce_secret:
        expected_secret = _get_client_webhook_secret(settings)
        if expected_secret:
            if not provided_secret or provided_secret != expected_secret:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")
        elif not provided_secret:
            alert_warning("Webhook secret missing", {"client_slug": payload.client_slug})

    body = payload.body
    metadata = body.metadata

    if not metadata or not metadata.remoteJid:
        return WebhookResponse(success=False, message="Missing metadata.remoteJid")

    remote_jid = metadata.remoteJid
    message_text = body.message or ""
    message_id = metadata.messageId

    if not message_text:
        return WebhookResponse(success=False, message="Empty message")

    outbound_idempotency_key = message_id or build_inbound_message_id(
        message_id,
        remote_jid,
        metadata.timestamp if metadata else None,
        message_text,
    )

    def _send_response(text: str) -> bool:
        return send_bot_response(
            db,
            client.id,
            remote_jid,
            text,
            idempotency_key=outbound_idempotency_key,
            raise_on_fail=skip_persist,
        )

    if skip_persist:
        if not conversation_id:
            return WebhookResponse(success=False, message="Missing conversation_id")
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            return WebhookResponse(success=False, message="Conversation not found")
        user = db.query(User).filter(User.id == conversation.user_id).first()
        if not user:
            return WebhookResponse(success=False, message="User not found")
    else:
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

        if enqueue_only:
            inbound_message_id = build_inbound_message_id(
                message_id, remote_jid, metadata.timestamp if metadata else None, message_text
            )
            payload_json = payload.model_dump(exclude_none=True)
            enqueued = enqueue_outbox_message(
                db,
                client_id=client.id,
                conversation_id=conversation.id,
                inbound_message_id=inbound_message_id,
                payload_json=payload_json,
            )
            if enqueued:
                logger.info(
                    "Outbox enqueued",
                    extra={
                        "context": {
                            "client_slug": payload.client_slug,
                            "conversation_id": str(conversation.id),
                            "inbound_message_id": inbound_message_id,
                        }
                    },
                )
            else:
                logger.info(
                    "Outbox duplicate skipped",
                    extra={
                        "context": {
                            "client_slug": payload.client_slug,
                            "conversation_id": str(conversation.id),
                            "inbound_message_id": inbound_message_id,
                        }
                    },
                )
            db.commit()
            return WebhookResponse(success=True, message="Accepted", conversation_id=conversation.id, bot_response=None)

    # 4. Update last_message_at (keep previous for session timeout check)
    now = datetime.now(timezone.utc)
    previous_last_message_at = conversation.last_message_at
    conversation.last_message_at = now

    # 4.5 Branch routing (instance_id -> branch, or ask user)
    branch_mode = (
        settings.branch_resolution_mode if settings and settings.branch_resolution_mode else "hybrid"
    )
    remember_branch = (
        settings.remember_branch_preference
        if settings and settings.remember_branch_preference is not None
        else True
    )
    context = _get_conversation_context(conversation)
    branch_id = conversation.branch_id or _coerce_uuid(context.get(BRANCH_CONTEXT_KEY))
    if not branch_id and remember_branch:
        branch_id = _get_user_branch_preference(user)

    if branch_id:
        if conversation.branch_id != branch_id:
            conversation.branch_id = branch_id
        if context.get(BRANCH_CONTEXT_KEY) != str(branch_id):
            context[BRANCH_CONTEXT_KEY] = str(branch_id)
            _set_conversation_context(conversation, context)
        if remember_branch and _get_user_branch_preference(user) != branch_id:
            _set_user_branch_preference(user, branch_id)
    else:
        instance_id = metadata.instanceId if metadata else None
        if branch_mode in {"by_instance", "hybrid"} and instance_id:
            branch = (
                db.query(Branch)
                .filter(
                    Branch.client_id == client.id,
                    Branch.instance_id == instance_id,
                    Branch.is_active == True,
                )
                .first()
            )
            if branch:
                _apply_branch_selection(
                    conversation=conversation,
                    user=user,
                    branch=branch,
                    context=context,
                    remember_branch=remember_branch,
                )

        if not conversation.branch_id and branch_mode in {"ask_user", "hybrid"}:
            branches = _get_active_branches(db, client.id)
            if len(branches) == 1:
                _apply_branch_selection(
                    conversation=conversation,
                    user=user,
                    branch=branches[0],
                    context=context,
                    remember_branch=remember_branch,
                )
            elif len(branches) > 1 and conversation.state == ConversationState.BOT_ACTIVE.value:
                selection = _get_branch_selection(context)
                if selection:
                    matched_branch, selected_by_index = _match_branch_choice(
                        message_text, branches, selection
                    )
                    if matched_branch:
                        _apply_branch_selection(
                            conversation=conversation,
                            user=user,
                            branch=matched_branch,
                            context=context,
                            remember_branch=remember_branch,
                        )
                        if _is_branch_only_message(message_text, matched_branch, selected_by_index):
                            bot_response = MSG_BRANCH_SELECTED.format(
                                branch_name=matched_branch.name
                                or matched_branch.slug
                                or "филиал"
                            )
                            save_message(
                                db, conversation.id, client.id, role="assistant", content=bot_response
                            )
                            sent = _send_response(bot_response)
                            result_message = (
                                "Branch selected (prompted)" if sent else "Branch selection response failed"
                            )
                            db.commit()
                            return WebhookResponse(
                                success=True,
                                message=result_message,
                                conversation_id=conversation.id,
                                bot_response=bot_response,
                            )
                    else:
                        prompt = _build_branch_prompt(branches)
                        context = _set_branch_selection(
                            context, _build_branch_selection(branches, now)
                        )
                        _set_conversation_context(conversation, context)
                        save_message(db, conversation.id, client.id, role="assistant", content=prompt)
                        sent = _send_response(prompt)
                        result_message = (
                            "Branch selection requested (retry)"
                            if sent
                            else "Branch selection prompt failed"
                        )
                        db.commit()
                        return WebhookResponse(
                            success=True,
                            message=result_message,
                            conversation_id=conversation.id,
                            bot_response=prompt,
                        )
                else:
                    prompt = _build_branch_prompt(branches)
                    context = _set_branch_selection(context, _build_branch_selection(branches, now))
                    _set_conversation_context(conversation, context)
                    save_message(db, conversation.id, client.id, role="assistant", content=prompt)
                    sent = _send_response(prompt)
                    result_message = (
                        "Branch selection requested" if sent else "Branch selection prompt failed"
                    )
                    db.commit()
                    return WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=prompt,
                    )

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
                    sent = _send_response(bot_response)
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
                    sent = _send_response(bot_response)
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

    # 9.03 Demo salon policy/truth gate (before booking/RAG).
    if payload.client_slug == "demo_salon" and conversation.state in [
        ConversationState.BOT_ACTIVE.value,
        ConversationState.PENDING.value,
    ]:
        decision = get_demo_salon_decision(message_text)
        if decision:
            bot_response = decision.response
            _reset_low_confidence_retry(conversation)

            result_message = "Demo salon reply sent"
            if decision.action == "escalate":
                if conversation.state == ConversationState.BOT_ACTIVE.value:
                    result = escalate_to_pending(
                        db=db,
                        conversation=conversation,
                        user_message=message_text,
                        trigger_type="policy",
                        trigger_value=decision.intent or "policy",
                    )
                    if result.ok:
                        handover = result.value
                        telegram_sent = send_telegram_notification(
                            db=db,
                            handover=handover,
                            conversation=conversation,
                            user=user,
                            message=message_text,
                        )
                        result_message = (
                            f"Demo salon policy escalation, telegram={'sent' if telegram_sent else 'failed'}"
                        )
                    else:
                        result_message = f"Demo salon policy escalation failed: {result.error}"
                else:
                    result_message = "Demo salon policy escalation skipped (already pending)"

            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
            if not sent:
                result_message = f"{result_message}; response_send=failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )

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
            sent = _send_response(bot_response)
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
                sent = _send_response(bot_response)
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
            sent = _send_response(bot_response)
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
    strong_domain_out = False
    strong_domain_meta: dict = {}
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
                        "client_slug": payload.client_slug,
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
        if domain_intent == DomainIntent.OUT_OF_DOMAIN:
            strong_domain_out, strong_domain_meta = is_strong_out_of_domain(
                message_text,
                domain_intent,
                domain_in_score,
                domain_out_score,
                client.config if client else None,
            )

    out_of_domain_signal = False
    if strong_domain_out:
        out_of_domain_signal = True
    elif intent == Intent.OUT_OF_DOMAIN and domain_intent != DomainIntent.IN_DOMAIN:
        out_of_domain_signal = True

    rag_confident = False
    rag_score = 0.0
    if conversation.state == ConversationState.BOT_ACTIVE.value and out_of_domain_signal:
        rag_confident, rag_score = get_rag_confidence(
            db=db,
            conversation_id=conversation.id,
            client_slug=payload.client_slug,
            user_message=message_text,
        )
        log_scores = _is_env_enabled(os.environ.get("DOMAIN_ROUTER_LOG_SCORES"), default=False)
        if log_scores:
            logger.info(
                "Domain out-of-domain gate",
                extra={
                    "context": {
                        "client_slug": payload.client_slug,
                        "remote_jid": remote_jid,
                        "intent": intent.value,
                        "domain_intent": domain_intent.value,
                        "strong_domain_out": strong_domain_out,
                        "rag_confident": rag_confident,
                        "rag_score": round(rag_score, 4),
                        "in_score": round(domain_in_score, 4),
                        "out_score": round(domain_out_score, 4),
                        "strict_out_threshold": strong_domain_meta.get("strict_out_threshold"),
                        "strong_out_threshold": strong_domain_meta.get("strong_out_threshold"),
                        "strict_margin": strong_domain_meta.get("strict_margin"),
                        "strong_margin": strong_domain_meta.get("strong_margin"),
                        "strict_in_max": strong_domain_meta.get("strict_in_max"),
                        "strong_in_max": strong_domain_meta.get("strong_in_max"),
                        "strict_min_len": strong_domain_meta.get("strict_min_len"),
                        "message_len": strong_domain_meta.get("message_len"),
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
        sent = _send_response(bot_response)
        result_message = "Greeting response sent" if sent else "Greeting response failed"
        db.commit()
        return WebhookResponse(
            success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
        )

    # 9.2 Pending: answer status questions without AI/escalation
    if conversation.state == ConversationState.PENDING.value and is_handover_status_question(message_text):
        bot_response = MSG_PENDING_STATUS
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = _send_response(bot_response)
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
        sent = _send_response(bot_response)
        result_message = "Bot status response sent" if sent else "Bot status response failed"
        db.commit()
        return WebhookResponse(
            success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
        )

    # 9.35 Out-of-domain: respond without escalation only when RAG has no confident match
    if conversation.state == ConversationState.BOT_ACTIVE.value and out_of_domain_signal and not rag_confident:
        bot_response = OUT_OF_DOMAIN_RESPONSE
        _reset_low_confidence_retry(conversation)
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = _send_response(bot_response)
        result_message = "Out-of-domain response sent" if sent else "Out-of-domain response failed"
        db.commit()
        return WebhookResponse(
            success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
        )

    # 10. Handle based on intent and state
    if conversation.state == ConversationState.BOT_ACTIVE.value and should_escalate(intent):
        handover_message = message_text
        if intent == Intent.HUMAN_REQUEST:
            handover_message = select_handover_user_message(db, conversation.id, message_text)

        # Escalate using state_service (atomic transition)
        result = escalate_to_pending(
            db=db,
            conversation=conversation,
            user_message=handover_message,
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
                message=handover_message,
            )
            bot_response = MSG_ESCALATED
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
            result_message = f"Escalated ({intent.value}), telegram={'sent' if telegram_sent else 'failed'}"
        else:
            logger.error(f"Escalation failed: {result.error}")
            # Fallback: respond normally
            gen_result = generate_bot_response(
                db,
                conversation,
                message_text,
                payload.client_slug,
                append_user_message=append_user_message,
            )
            if gen_result.ok and gen_result.value[0]:
                bot_response = gen_result.value[0]
                save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                sent = _send_response(bot_response)
            result_message = f"Escalation failed ({result.error_code}), responded normally"

    elif is_rejection(intent):
        # Client rejects help
        if conversation.state in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]:
            handover = get_active_handover(db, conversation.id)
            if handover:
                manager_resolve(db, conversation, handover, manager_id="system", manager_name="system")
            bot_response = MSG_MUTED_TEMP
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
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
            sent = _send_response(bot_response)
            result_message = f"Muted (rejection #{conversation.no_count})"

    elif conversation.state in [ConversationState.BOT_ACTIVE.value, ConversationState.PENDING.value]:
        # Bot responds: normal mode OR pending (bot helps while waiting)
        gen_result = generate_bot_response(
            db,
            conversation,
            message_text,
            payload.client_slug,
            append_user_message=append_user_message,
        )

        if not gen_result.ok:
            # AI error — fallback response
            bot_response = MSG_AI_ERROR
            save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
            sent = _send_response(bot_response)
            result_message = f"AI error: {gen_result.error}"
        else:
            response_text, confidence = gen_result.value

            if confidence == "low_confidence":
                if conversation.state == ConversationState.PENDING.value:
                    # Already escalated: respond but don't re-escalate
                    bot_response = MSG_PENDING_LOW_CONFIDENCE
                    save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
                    sent = _send_response(bot_response)
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
                        sent = _send_response(bot_response)
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
                        sent = _send_response(bot_response)
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
                sent = _send_response(bot_response)
                result_message = "Message sent" if sent else "Failed to send"
            else:
                result_message = "No response generated"
    else:
        result_message = f"Unknown state: {conversation.state}"

    db.commit()

    return WebhookResponse(
        success=True, message=result_message, conversation_id=conversation.id, bot_response=bot_response
    )
