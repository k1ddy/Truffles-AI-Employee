import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.logging_config import get_logger
from app.models import Agent, AgentIdentity, AgentLinkToken, Branch, ClientSettings, Conversation, Handover
from app.schemas.telegram import TelegramMessage, TelegramUpdate, TelegramWebhookResponse
from app.services.agent_link_service import consume_link_token, hash_link_token
from app.services.audit_service import record_audit_event
from app.services.manager_message_service import (
    notify_client_manager_status,
    process_manager_media,
    process_manager_message,
    resolve_linked_agent,
)
from app.services.state_service import manager_resolve as state_manager_resolve
from app.services.state_service import manager_take as state_manager_take
from app.services.telegram_service import TelegramService

logger = get_logger("telegram_webhook")

router = APIRouter()


def _is_simulation_handover(db: Session, handover: Handover | None) -> bool:
    if not handover:
        return False
    conversation = getattr(handover, "conversation", None)
    if not conversation:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == handover.conversation_id)
            .first()
        )
    if not conversation or not isinstance(conversation.context, dict):
        return False
    sim_context = conversation.context.get("simulation")
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


async def parse_telegram_update(request: Request) -> Optional[dict]:
    """
    Parse Telegram update with tolerant decoding to avoid utf-8 crashes.
    Returns dict or None.
    """
    try:
        return await request.json()
    except Exception as e:
        logger.warning(f"Standard request.json() failed: {e}, fallback decoding", exc_info=True)

    raw = await request.body()
    for enc in ("utf-8", "latin-1"):
        try:
            decoded = raw.decode(enc, errors="replace")
            return json.loads(decoded)
        except Exception:
            continue

    logger.error("Failed to decode Telegram webhook payload after fallbacks")
    return None


def _extract_start_token(text: str) -> Optional[str]:
    raw = (text or "").strip()
    if not raw.lower().startswith("/start"):
        return None
    token = raw[len("/start") :].strip()
    if token.startswith("="):
        token = token[1:].strip()
    return token or None


async def handle_link_command(update: TelegramUpdate, db: Session) -> TelegramWebhookResponse:
    message = update.message
    if not message or not message.text:
        return TelegramWebhookResponse(success=False, message="No start payload")

    token = _extract_start_token(message.text)
    if not token:
        return TelegramWebhookResponse(success=False, message="Missing link token")

    manager_id = message.from_user.id if message.from_user else None
    manager_username = message.from_user.username if message.from_user else None
    if not manager_id:
        return TelegramWebhookResponse(success=False, message="Missing user identity")

    try:
        link_record = consume_link_token(db, token)
    except ValueError as exc:
        reason = str(exc)
        token_hash = hash_link_token(token)
        record = (
            db.query(AgentLinkToken)
            .filter(AgentLinkToken.token_hash == token_hash)
            .first()
        )
        if record:
            agent = db.query(Agent).filter(Agent.id == record.agent_id).first()
            if agent:
                record_audit_event(
                    db,
                    actor_id=agent.id,
                    actor_name=agent.name,
                    client_id=agent.client_id,
                    branch_id=agent.branch_id,
                    event_type="telegram_link_failed",
                    entity_type="agent",
                    entity_id=agent.id,
                    payload={"reason": reason},
                )
                db.commit()
                settings = (
                    db.query(ClientSettings)
                    .filter(ClientSettings.client_id == agent.client_id)
                    .first()
                )
                if settings and settings.telegram_bot_token:
                    telegram = TelegramService(settings.telegram_bot_token)
                    telegram.send_message(
                        chat_id=str(message.chat.id),
                        text=f"❌ Ссылка недействительна: {reason}",
                    )
        return TelegramWebhookResponse(success=False, message=f"Token {reason}")

    agent = db.query(Agent).filter(Agent.id == link_record.agent_id).first()
    if not agent:
        return TelegramWebhookResponse(success=False, message="Agent not found")

    existing_identity = (
        db.query(AgentIdentity)
        .filter(
            AgentIdentity.channel == "telegram",
            AgentIdentity.external_id == str(manager_id),
        )
        .first()
    )
    if existing_identity and existing_identity.agent_id != agent.id:
        record_audit_event(
            db,
            actor_id=agent.id,
            actor_name=agent.name,
            client_id=agent.client_id,
            branch_id=agent.branch_id,
            event_type="telegram_link_failed",
            entity_type="agent",
            entity_id=agent.id,
            payload={"reason": "conflict"},
        )
        db.commit()
        settings = db.query(ClientSettings).filter(ClientSettings.client_id == agent.client_id).first()
        if settings and settings.telegram_bot_token:
            telegram = TelegramService(settings.telegram_bot_token)
            telegram.send_message(
                chat_id=str(message.chat.id),
                text="⛔ Этот Telegram уже связан с другим агентом.",
            )
        return TelegramWebhookResponse(success=False, message="Telegram already linked")

    now = datetime.now(timezone.utc)
    agent_identity = (
        db.query(AgentIdentity)
        .filter(
            AgentIdentity.agent_id == agent.id,
            AgentIdentity.channel == "telegram",
        )
        .first()
    )
    if agent_identity:
        agent_identity.external_id = str(manager_id)
        agent_identity.username = manager_username
        agent_identity.updated_at = now
        if not agent_identity.created_at:
            agent_identity.created_at = now
    else:
        agent_identity = AgentIdentity(
            agent_id=agent.id,
            channel="telegram",
            external_id=str(manager_id),
            username=manager_username,
            identity_metadata={"linked_from": "telegram_start"},
            created_at=now,
            updated_at=now,
        )
        db.add(agent_identity)

    link_record.used_at = now
    db.add(link_record)

    record_audit_event(
        db,
        actor_id=agent.id,
        actor_name=agent.name,
        client_id=agent.client_id,
        branch_id=agent.branch_id,
        event_type="telegram_linked",
        entity_type="agent",
        entity_id=agent.id,
        payload={
            "telegram_user_id": str(manager_id),
            "username": manager_username,
        },
    )

    db.commit()

    settings = db.query(ClientSettings).filter(ClientSettings.client_id == agent.client_id).first()
    if settings and settings.telegram_bot_token:
        telegram = TelegramService(settings.telegram_bot_token)
        telegram.send_message(
            chat_id=str(message.chat.id),
            text=f"✅ Telegram связан с агентом {agent.name or 'Truffles'}",
        )

    return TelegramWebhookResponse(success=True, message="Linked")


@router.post("/telegram-webhook", response_model=TelegramWebhookResponse)
async def handle_telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Handle Telegram webhook updates:
    - Text messages from managers -> forward to WhatsApp client
    - Callback queries (button clicks) -> process callback action
    """
    try:
        body = await parse_telegram_update(request)
        if body is None:
            return TelegramWebhookResponse(success=False, message="Invalid telegram payload")

        logger.debug(f"Telegram webhook received: {body}")

        update = TelegramUpdate(**body)

        # Handle callback query (button click)
        if update.callback_query:
            return await handle_callback_query(update, db)

        # Handle message from manager (media or text)
        if update.message:
            media_payload = _extract_media_payload(update.message)
            if media_payload:
                return await handle_manager_media(update, media_payload, db, background_tasks)
            if update.message.text:
                return await handle_manager_message(update, db)

        return TelegramWebhookResponse(success=True, message="No actionable content")

    except Exception as e:
        logger.error(f"Telegram webhook error: {e}", exc_info=True)
        return TelegramWebhookResponse(success=False, message=str(e))


# Backward-compatible alias used in ops docs
@router.post("/telegram-callback", response_model=TelegramWebhookResponse)
async def handle_telegram_callback(request: Request, db: Session = Depends(get_db)):
    return await handle_telegram_webhook(request, db)


async def handle_manager_message(update: TelegramUpdate, db: Session) -> TelegramWebhookResponse:
    """Handle text message from manager -> forward to WhatsApp client."""
    message = update.message
    logger.info(f"Manager message received: chat_id={message.chat.id}, from={message.from_user.id if message.from_user else 'unknown'}, text={message.text[:50] if message.text else 'none'}...")

    # Skip bot messages
    if message.from_user and message.from_user.is_bot:
        return TelegramWebhookResponse(success=True, message="Ignoring bot message")

    # Skip messages without text
    if not message.text:
        return TelegramWebhookResponse(success=True, message="No text in message")

    # Handle linking command
    if message.text.startswith("/start"):
        return await handle_link_command(update, db)

    # Skip other commands
    if message.text.startswith("/"):
        return TelegramWebhookResponse(success=True, message="Ignoring command")

    chat_id = message.chat.id
    message_thread_id = message.message_thread_id

    manager_name = "Unknown"
    manager_id = 0
    manager_username = None
    if message.from_user:
        manager_id = message.from_user.id
        manager_name = message.from_user.first_name
        if message.from_user.last_name:
            manager_name += f" {message.from_user.last_name}"
        manager_username = message.from_user.username
    elif message.sender_chat:
        manager_id = message.sender_chat.id
        manager_name = message.sender_chat.title or manager_name
        manager_username = message.sender_chat.username
        logger.warning(
            "Manager message missing from_user; using sender_chat identity",
            extra={
                "context": {
                    "sender_chat_id": message.sender_chat.id,
                    "sender_chat_title": message.sender_chat.title,
                }
            },
        )
    else:
        logger.warning("Manager message missing from_user and sender_chat; auto-learning disabled")

    success, result_message, took_handover, handover = process_manager_message(
        db=db,
        chat_id=chat_id,
        message_text=message.text,
        manager_telegram_id=manager_id,
        manager_name=manager_name,
        manager_username=manager_username,
        message_thread_id=message_thread_id,
    )

    db.commit()

    if _is_simulation_handover(db, handover):
        return TelegramWebhookResponse(success=success, message=result_message)

    bot_token = get_bot_token_by_chat(db, chat_id)
    if bot_token:
        telegram = TelegramService(bot_token)

        # If manager auto-took the handover, update buttons to [Решено]
        if success and took_handover and handover and handover.telegram_message_id:
            telegram._make_request(
                "editMessageReplyMarkup",
                {
                    "chat_id": chat_id,
                    "message_id": handover.telegram_message_id,
                    "reply_markup": {
                        "inline_keyboard": [[{"text": "Решено ✅", "callback_data": f"resolve_{handover.id}"}]]
                    },
                },
            )

            # Notify in the topic that the manager took the request (auto-take on first message)
            if message_thread_id:
                taken_name = handover.assigned_to_name or manager_name
                telegram.send_message(
                    chat_id=str(chat_id),
                    text=f"👤 <b>{taken_name}</b> взял заявку",
                    message_thread_id=message_thread_id,
                )

        # Only notify on failure
        if not success:
            error_text = "❌ Не доставлено"
            if result_message == "Access denied":
                error_text = "⛔ Нет доступа. Привяжите Telegram в Console."
            telegram.send_message(
                chat_id=str(chat_id),
                text=error_text,
                message_thread_id=message_thread_id,
                reply_to_message_id=message.message_id,
            )

    return TelegramWebhookResponse(success=success, message=result_message)


def _extract_media_payload(message: TelegramMessage) -> Optional[dict]:
    if message.photo:
        photo = message.photo[-1]
        return {
            "media_type": "photo",
            "file_id": photo.file_id,
            "file_name": None,
            "mime_type": "image/jpeg",
            "file_size": photo.file_size,
            "caption": message.caption,
            "telegram_message_id": message.message_id,
        }
    if message.document:
        doc = message.document
        return {
            "media_type": "document",
            "file_id": doc.file_id,
            "file_name": doc.file_name,
            "mime_type": doc.mime_type,
            "file_size": doc.file_size,
            "caption": message.caption,
            "telegram_message_id": message.message_id,
        }
    if message.audio:
        audio = message.audio
        return {
            "media_type": "audio",
            "file_id": audio.file_id,
            "file_name": audio.file_name,
            "mime_type": audio.mime_type,
            "file_size": audio.file_size,
            "caption": message.caption,
            "telegram_message_id": message.message_id,
        }
    if message.voice:
        voice = message.voice
        return {
            "media_type": "voice",
            "file_id": voice.file_id,
            "file_name": None,
            "mime_type": voice.mime_type,
            "file_size": voice.file_size,
            "caption": message.caption,
            "telegram_message_id": message.message_id,
        }
    if message.video:
        video = message.video
        return {
            "media_type": "video",
            "file_id": video.file_id,
            "file_name": None,
            "mime_type": video.mime_type,
            "file_size": video.file_size,
            "caption": message.caption,
            "telegram_message_id": message.message_id,
        }
    return None


def _process_manager_media_background(task: dict) -> None:
    db = SessionLocal()
    chat_id = task["chat_id"]
    message_thread_id = task.get("message_thread_id")
    manager_name = task.get("manager_name") or "Unknown"
    bot_token = task["bot_token"]
    reply_to_message_id = task.get("reply_to_message_id")

    try:
        success, result_message, took_handover, handover = process_manager_media(
            db=db,
            chat_id=chat_id,
            manager_telegram_id=task["manager_telegram_id"],
            manager_name=manager_name,
            media_type=task["media_type"],
            file_id=task["file_id"],
            bot_token=bot_token,
            caption=task.get("caption"),
            file_name=task.get("file_name"),
            mime_type=task.get("mime_type"),
            file_size=task.get("file_size"),
            manager_username=task.get("manager_username"),
            message_thread_id=message_thread_id,
            telegram_message_id=task.get("telegram_message_id"),
        )

        db.commit()

        telegram = TelegramService(bot_token)
        if success and took_handover and handover and handover.telegram_message_id:
            telegram._make_request(
                "editMessageReplyMarkup",
                {
                    "chat_id": chat_id,
                    "message_id": handover.telegram_message_id,
                    "reply_markup": {
                        "inline_keyboard": [[{"text": "Решено ✅", "callback_data": f"resolve_{handover.id}"}]]
                    },
                },
            )
            if message_thread_id:
                taken_name = handover.assigned_to_name or manager_name
                telegram.send_message(
                    chat_id=str(chat_id),
                    text=f"👤 <b>{taken_name}</b> взял заявку",
                    message_thread_id=message_thread_id,
                )

        if not success:
            logger.warning(
                "Manager media delivery failed",
                extra={
                    "context": {
                        "chat_id": chat_id,
                        "thread_id": message_thread_id,
                        "reason": result_message,
                    }
                },
            )
            error_text = "❌ Не доставлено"
            if result_message == "Access denied":
                error_text = "⛔ Нет доступа. Привяжите Telegram в Console."
            telegram.send_message(
                chat_id=str(chat_id),
                text=error_text,
                message_thread_id=message_thread_id,
                reply_to_message_id=reply_to_message_id,
            )
    except Exception as exc:
        logger.error(f"Manager media background error: {exc}", exc_info=True)
        try:
            telegram = TelegramService(bot_token)
            telegram.send_message(
                chat_id=str(chat_id),
                text="❌ Не доставлено",
                message_thread_id=message_thread_id,
                reply_to_message_id=reply_to_message_id,
            )
        except Exception:
            logger.error("Failed to notify manager about media failure", exc_info=True)
    finally:
        db.close()


async def handle_manager_media(
    update: TelegramUpdate,
    media_payload: dict,
    db: Session,
    background_tasks: BackgroundTasks,
) -> TelegramWebhookResponse:
    message = update.message
    if not message:
        return TelegramWebhookResponse(success=False, message="No message payload")

    logger.info(
        "Manager media received",
        extra={
            "context": {
                "chat_id": message.chat.id,
                "thread_id": message.message_thread_id,
                "media_type": media_payload.get("media_type"),
            }
        },
    )

    if message.from_user and message.from_user.is_bot:
        return TelegramWebhookResponse(success=True, message="Ignoring bot message")

    chat_id = message.chat.id
    message_thread_id = message.message_thread_id

    manager_name = "Unknown"
    manager_id = 0
    manager_username = None
    if message.from_user:
        manager_id = message.from_user.id
        manager_name = message.from_user.first_name
        if message.from_user.last_name:
            manager_name += f" {message.from_user.last_name}"
        manager_username = message.from_user.username
    elif message.sender_chat:
        manager_id = message.sender_chat.id
        manager_name = message.sender_chat.title or manager_name
        manager_username = message.sender_chat.username
        logger.warning(
            "Manager media missing from_user; using sender_chat identity",
            extra={
                "context": {
                    "sender_chat_id": message.sender_chat.id,
                    "sender_chat_title": message.sender_chat.title,
                }
            },
        )
    else:
        logger.warning("Manager media missing from_user and sender_chat; auto-learning disabled")

    bot_token = get_bot_token_by_chat(db, chat_id)
    if not bot_token:
        return TelegramWebhookResponse(success=False, message="Bot token not found")

    task = {
        "chat_id": chat_id,
        "message_thread_id": message_thread_id,
        "manager_telegram_id": manager_id,
        "manager_name": manager_name,
        "manager_username": manager_username,
        "media_type": media_payload.get("media_type") or "document",
        "file_id": media_payload.get("file_id") or "",
        "bot_token": bot_token,
        "caption": media_payload.get("caption"),
        "file_name": media_payload.get("file_name"),
        "mime_type": media_payload.get("mime_type"),
        "file_size": media_payload.get("file_size"),
        "telegram_message_id": media_payload.get("telegram_message_id"),
        "reply_to_message_id": message.message_id,
    }
    background_tasks.add_task(_process_manager_media_background, task)

    return TelegramWebhookResponse(success=True, message="Queued")


def get_bot_token_by_chat(db: Session, chat_id: int) -> Optional[str]:
    """Get bot token by telegram chat_id."""
    settings = db.query(ClientSettings).filter(ClientSettings.telegram_chat_id == str(chat_id)).first()
    if settings:
        return settings.telegram_bot_token
    branch = db.query(Branch).filter(Branch.telegram_chat_id == str(chat_id)).first()
    if not branch:
        return None
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == branch.client_id).first()
    return settings.telegram_bot_token if settings else None


async def handle_callback_query(update: TelegramUpdate, db: Session) -> TelegramWebhookResponse:
    """Handle callback query (button click): take, resolve, skip."""
    callback = update.callback_query

    # Dedup: prevent double processing of same callback
    from app.services.callback_dedup import is_callback_processed
    if is_callback_processed(callback.id):
        logger.info(f"Duplicate callback ignored: {callback.id}")
        return TelegramWebhookResponse(success=True, message="Already processed")

    if not callback.data:
        return TelegramWebhookResponse(success=False, message="No callback data")

    # Parse callback_data: "action_handover_id"
    try:
        first_underscore = callback.data.index("_")
        action = callback.data[:first_underscore]
        handover_id = callback.data[first_underscore + 1 :]
    except ValueError:
        return TelegramWebhookResponse(success=False, message=f"Invalid callback data: {callback.data}")

    logger.info(f"Callback: action={action}, handover_id={handover_id}")

    # Get manager info
    manager_telegram_id = callback.from_user.id
    manager_name = callback.from_user.first_name
    if callback.from_user.last_name:
        manager_name += f" {callback.from_user.last_name}"

    # Get chat info
    chat_id = callback.message.chat.id if callback.message else None
    message_id = callback.message.message_id if callback.message else None

    # Find handover
    handover = db.query(Handover).filter(Handover.id == handover_id).first()
    if not handover:
        bot_token = get_bot_token_by_chat(db, chat_id) if chat_id else None
        if bot_token:
            telegram = TelegramService(bot_token)
            telegram._make_request(
                "answerCallbackQuery", {"callback_query_id": callback.id, "text": "❌ Заявка не найдена"}
            )
        return TelegramWebhookResponse(success=False, message=f"Handover {handover_id} not found")

    # Get conversation
    conversation = db.query(Conversation).filter(Conversation.id == handover.conversation_id).first()
    if not conversation:
        telegram._make_request(
            "answerCallbackQuery", {"callback_query_id": callback.id, "text": "❌ Диалог не найден"}
        )
        return TelegramWebhookResponse(success=False, message="Conversation not found")

    linked_agent = resolve_linked_agent(
        db,
        telegram_user_id=manager_telegram_id,
        client_id=conversation.client_id,
        branch_id=conversation.branch_id,
    )
    if not linked_agent:
        telegram._make_request(
            "answerCallbackQuery",
            {"callback_query_id": callback.id, "text": "⛔ Нет доступа. Привяжите Telegram в Console"},
        )
        return TelegramWebhookResponse(success=False, message="Access denied")

    manager_id = str(linked_agent.id)
    manager_name = linked_agent.name or manager_name

    # Get topic_id for sending messages
    topic_id = conversation.telegram_topic_id

    if _is_simulation_handover(db, handover):
        if action == "take":
            result = state_manager_take(db, conversation, handover, manager_id, manager_name)
            if not result.ok:
                return TelegramWebhookResponse(success=False, message=result.error)
            db.commit()
            return TelegramWebhookResponse(success=True, message="Taken (simulation)", conversation_id=handover.conversation_id)
        if action in {"resolve", "return"}:
            result = state_manager_resolve(db, conversation, handover, manager_id, manager_name)
            if not result.ok:
                return TelegramWebhookResponse(success=False, message=result.error)
            db.commit()
            return TelegramWebhookResponse(success=True, message="Resolved (simulation)", conversation_id=handover.conversation_id)
        if action == "skip":
            return TelegramWebhookResponse(success=True, message="Skipped (simulation)")
        return TelegramWebhookResponse(success=False, message=f"Unknown action: {action}")

    # Get bot token
    bot_token = get_bot_token_by_chat(db, chat_id) if chat_id else None
    if not bot_token:
        return TelegramWebhookResponse(success=False, message="Bot token not found")

    telegram = TelegramService(bot_token)

    # Stale buttons protection: if handover already closed, don't error and remove buttons.
    if handover.status not in ["pending", "active"]:
        telegram._make_request(
            "answerCallbackQuery",
            {"callback_query_id": callback.id, "text": "✅ Заявка уже закрыта"},
        )

        if message_id:
            telegram._make_request(
                "editMessageReplyMarkup",
                {"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}},
            )
        pin_message_id = handover.telegram_message_id or message_id
        if pin_message_id:
            telegram.unpin_message(str(chat_id), pin_message_id)

        return TelegramWebhookResponse(success=True, message="Already closed", conversation_id=handover.conversation_id)

    if action in ("resolve", "return") and handover.status == "active":
        assigned_raw = str(handover.assigned_to or "").strip()
        if assigned_raw and assigned_raw != str(linked_agent.id) and linked_agent.role not in ("owner", "admin"):
            taken_by = handover.assigned_to_name or "менеджер"
            telegram._make_request(
                "answerCallbackQuery",
                {"callback_query_id": callback.id, "text": f"⚠️ Заявку ведет {taken_by}", "show_alert": True},
            )
            return TelegramWebhookResponse(success=False, message="Access denied")

    # Process action
    if action == "take":
        # Take using state_service
        result = state_manager_take(db, conversation, handover, manager_id, manager_name)

        if not result.ok:
            taken_by = handover.assigned_to_name or "Кто-то"
            telegram._make_request(
                "answerCallbackQuery",
                {"callback_query_id": callback.id, "text": f"⚠️ Заявку уже взял {taken_by}", "show_alert": True},
            )
            return TelegramWebhookResponse(success=False, message=result.error)

        record_audit_event(
            db,
            actor_id=linked_agent.id,
            actor_name=linked_agent.name,
            client_id=conversation.client_id,
            branch_id=conversation.branch_id,
            event_type="case_taken",
            entity_type="handover",
            entity_id=handover.id,
        )

        # Update buttons to [Решено]
        if message_id:
            telegram._make_request(
                "editMessageReplyMarkup",
                {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {
                        "inline_keyboard": [[{"text": "Решено ✅", "callback_data": f"resolve_{handover_id}"}]]
                    },
                },
            )

        # Send message to topic: who took the request
        if topic_id:
            telegram.send_message(
                chat_id=str(chat_id),
                text=f"👤 <b>{manager_name}</b> взял заявку",
                message_thread_id=topic_id,
            )

        telegram._make_request("answerCallbackQuery", {"callback_query_id": callback.id, "text": "✅ Вы взяли заявку"})

        db.commit()

        notify_ok, notify_detail = notify_client_manager_status(
            db,
            conversation=conversation,
            handover=handover,
            status="connected",
            manager_name=manager_name,
        )
        record_audit_event(
            db,
            actor_id=linked_agent.id,
            actor_name=linked_agent.name,
            client_id=conversation.client_id,
            branch_id=conversation.branch_id,
            event_type="manager_connected",
            entity_type="handover",
            entity_id=handover.id,
            payload={
                "client_notify_status": "ok" if notify_ok else "failed",
                "client_notify_detail": notify_detail,
            },
        )
        db.commit()
        return TelegramWebhookResponse(success=True, message="Taken", conversation_id=handover.conversation_id)

    elif action == "resolve":
        # Resolve using state_service
        result = state_manager_resolve(db, conversation, handover, manager_id, manager_name)

        if not result.ok:
            telegram._make_request(
                "answerCallbackQuery",
                {"callback_query_id": callback.id, "text": f"❌ Ошибка: {result.error}", "show_alert": True},
            )
            return TelegramWebhookResponse(success=False, message=result.error)

        record_audit_event(
            db,
            actor_id=linked_agent.id,
            actor_name=linked_agent.name,
            client_id=conversation.client_id,
            branch_id=conversation.branch_id,
            event_type="case_resolved",
            entity_type="handover",
            entity_id=handover.id,
        )

        # Remove buttons
        if message_id:
            telegram._make_request(
                "editMessageReplyMarkup",
                {"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}},
            )

        # Unpin pinned notification (prefer stored message_id).
        pin_message_id = handover.telegram_message_id or message_id
        if pin_message_id:
            telegram.unpin_message(str(chat_id), pin_message_id)

        telegram._make_request("answerCallbackQuery", {"callback_query_id": callback.id, "text": "✅ Заявка решена"})

        db.commit()

        notify_ok, notify_detail = notify_client_manager_status(
            db,
            conversation=conversation,
            handover=handover,
            status="disconnected",
            manager_name=manager_name,
        )
        record_audit_event(
            db,
            actor_id=linked_agent.id,
            actor_name=linked_agent.name,
            client_id=conversation.client_id,
            branch_id=conversation.branch_id,
            event_type="manager_disconnected",
            entity_type="handover",
            entity_id=handover.id,
            payload={
                "client_notify_status": "ok" if notify_ok else "failed",
                "client_notify_detail": notify_detail,
            },
        )
        db.commit()
        return TelegramWebhookResponse(success=True, message="Resolved", conversation_id=handover.conversation_id)

    elif action == "return":
        # Return bot: close handover and set state back to bot_active (even if it was pending)
        result = state_manager_resolve(
            db,
            conversation,
            handover,
            manager_id,
            manager_name,
            preserve_context=True,
        )

        if not result.ok:
            telegram._make_request(
                "answerCallbackQuery",
                {"callback_query_id": callback.id, "text": f"❌ Ошибка: {result.error}", "show_alert": True},
            )
            return TelegramWebhookResponse(success=False, message=result.error)

        handover.resolution_notes = "Returned to bot by manager"

        record_audit_event(
            db,
            actor_id=linked_agent.id,
            actor_name=linked_agent.name,
            client_id=conversation.client_id,
            branch_id=conversation.branch_id,
            event_type="case_returned",
            entity_type="handover",
            entity_id=handover.id,
        )

        # Remove buttons
        if message_id:
            telegram._make_request(
                "editMessageReplyMarkup",
                {"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}},
            )

        # Unpin pinned notification (prefer stored message_id).
        pin_message_id = handover.telegram_message_id or message_id
        if pin_message_id:
            telegram.unpin_message(str(chat_id), pin_message_id)

        # Notify in topic
        if topic_id:
            telegram.send_message(
                chat_id=str(chat_id),
                text=f"🤖 Заявка закрыта, бот снова отвечает (by {manager_name})",
                message_thread_id=topic_id,
            )

        telegram._make_request("answerCallbackQuery", {"callback_query_id": callback.id, "text": "✅ Возвращено боту"})

        db.commit()

        notify_ok, notify_detail = notify_client_manager_status(
            db,
            conversation=conversation,
            handover=handover,
            status="disconnected",
            manager_name=manager_name,
        )
        record_audit_event(
            db,
            actor_id=linked_agent.id,
            actor_name=linked_agent.name,
            client_id=conversation.client_id,
            branch_id=conversation.branch_id,
            event_type="manager_disconnected",
            entity_type="handover",
            entity_id=handover.id,
            payload={
                "client_notify_status": "ok" if notify_ok else "failed",
                "client_notify_detail": notify_detail,
            },
        )
        db.commit()
        return TelegramWebhookResponse(success=True, message="Returned to bot", conversation_id=handover.conversation_id)

    elif action == "skip":
        # Skip: just notification, no recording needed
        telegram._make_request("answerCallbackQuery", {"callback_query_id": callback.id, "text": "⏭️ Пропущено"})
        return TelegramWebhookResponse(success=True, message="Skipped")

    else:
        telegram._make_request(
            "answerCallbackQuery", {"callback_query_id": callback.id, "text": f"❓ Неизвестное действие: {action}"}
        )
        return TelegramWebhookResponse(success=False, message=f"Unknown action: {action}")
