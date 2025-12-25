import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.models import ClientSettings, Conversation, Handover
from app.schemas.telegram import TelegramUpdate, TelegramWebhookResponse
from app.services.manager_message_service import process_manager_message
from app.services.state_service import manager_resolve as state_manager_resolve
from app.services.state_service import manager_take as state_manager_take
from app.services.telegram_service import TelegramService

logger = get_logger("telegram_webhook")

router = APIRouter()


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


@router.post("/telegram-webhook", response_model=TelegramWebhookResponse)
async def handle_telegram_webhook(request: Request, db: Session = Depends(get_db)):
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

        # Handle text message from manager
        if update.message and update.message.text:
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

    # Skip commands
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
                telegram.send_message(
                    chat_id=str(chat_id),
                    text=f"👤 <b>{manager_name}</b> взял заявку",
                    message_thread_id=message_thread_id,
                )

        # Only notify on failure
        if not success:
            telegram.send_message(
                chat_id=str(chat_id),
                text="❌ Не доставлено",
                message_thread_id=message_thread_id,
                reply_to_message_id=message.message_id,
            )

    return TelegramWebhookResponse(success=success, message=result_message)


def get_bot_token_by_chat(db: Session, chat_id: int) -> Optional[str]:
    """Get bot token by telegram chat_id."""
    settings = db.query(ClientSettings).filter(ClientSettings.telegram_chat_id == str(chat_id)).first()
    return settings.telegram_bot_token if settings else None


async def handle_callback_query(update: TelegramUpdate, db: Session) -> TelegramWebhookResponse:
    """Handle callback query (button click): take, resolve, skip."""
    callback = update.callback_query

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
    manager_id = str(callback.from_user.id)
    manager_name = callback.from_user.first_name
    if callback.from_user.last_name:
        manager_name += f" {callback.from_user.last_name}"

    # Get chat info
    chat_id = callback.message.chat.id if callback.message else None
    message_id = callback.message.message_id if callback.message else None

    # Get bot token
    bot_token = get_bot_token_by_chat(db, chat_id) if chat_id else None
    if not bot_token:
        return TelegramWebhookResponse(success=False, message="Bot token not found")

    telegram = TelegramService(bot_token)

    # Find handover
    handover = db.query(Handover).filter(Handover.id == handover_id).first()
    if not handover:
        telegram._make_request(
            "answerCallbackQuery", {"callback_query_id": callback.id, "text": "❌ Заявка не найдена"}
        )
        return TelegramWebhookResponse(success=False, message=f"Handover {handover_id} not found")

    # Get conversation
    conversation = db.query(Conversation).filter(Conversation.id == handover.conversation_id).first()

    # Get topic_id for sending messages
    topic_id = conversation.telegram_topic_id if conversation else None

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
            telegram.unpin_message(str(chat_id), message_id)

        return TelegramWebhookResponse(success=True, message="Already closed", conversation_id=handover.conversation_id)

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

        # Remove buttons
        if message_id:
            telegram._make_request(
                "editMessageReplyMarkup",
                {"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}},
            )

        # Unpin
        if message_id:
            telegram.unpin_message(str(chat_id), message_id)

        telegram._make_request("answerCallbackQuery", {"callback_query_id": callback.id, "text": "✅ Заявка решена"})

        db.commit()
        return TelegramWebhookResponse(success=True, message="Resolved", conversation_id=handover.conversation_id)

    elif action == "return":
        # Return bot: close handover and set state back to bot_active (even if it was pending)
        result = state_manager_resolve(db, conversation, handover, manager_id, manager_name)

        if not result.ok:
            telegram._make_request(
                "answerCallbackQuery",
                {"callback_query_id": callback.id, "text": f"❌ Ошибка: {result.error}", "show_alert": True},
            )
            return TelegramWebhookResponse(success=False, message=result.error)

        handover.resolution_notes = "Returned to bot by manager"

        # Remove buttons
        if message_id:
            telegram._make_request(
                "editMessageReplyMarkup",
                {"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}},
            )

        # Unpin
        if message_id:
            telegram.unpin_message(str(chat_id), message_id)

        # Notify in topic
        if topic_id:
            telegram.send_message(
                chat_id=str(chat_id),
                text=f"🤖 Заявка закрыта, бот снова отвечает (by {manager_name})",
                message_thread_id=topic_id,
            )

        telegram._make_request("answerCallbackQuery", {"callback_query_id": callback.id, "text": "✅ Возвращено боту"})

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
