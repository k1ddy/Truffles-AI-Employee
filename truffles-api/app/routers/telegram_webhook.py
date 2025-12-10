from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional

from app.database import get_db
from app.schemas.telegram import TelegramUpdate, TelegramWebhookResponse
from app.services.manager_message_service import process_manager_message
from app.models import Handover, Conversation, ClientSettings
from app.services.telegram_service import TelegramService

router = APIRouter()


@router.post("/telegram-webhook", response_model=TelegramWebhookResponse)
async def handle_telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Telegram webhook updates:
    - Text messages from managers -> forward to WhatsApp client
    - Callback queries (button clicks) -> process callback action
    """
    try:
        body = await request.json()
        print(f"Telegram webhook received: {body}")
        
        update = TelegramUpdate(**body)
        
        # Handle callback query (button click)
        if update.callback_query:
            return await handle_callback_query(update, db)
        
        # Handle text message from manager
        if update.message and update.message.text:
            return await handle_manager_message(update, db)
        
        return TelegramWebhookResponse(
            success=True,
            message="No actionable content"
        )
        
    except Exception as e:
        print(f"Telegram webhook error: {e}")
        import traceback
        traceback.print_exc()
        return TelegramWebhookResponse(
            success=False,
            message=str(e)
        )


async def handle_manager_message(update: TelegramUpdate, db: Session) -> TelegramWebhookResponse:
    """Handle text message from manager -> forward to WhatsApp client."""
    message = update.message
    
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
    if message.from_user:
        manager_id = message.from_user.id
        manager_name = message.from_user.first_name
        if message.from_user.last_name:
            manager_name += f" {message.from_user.last_name}"
    
    success, result_message, took_handover, handover = process_manager_message(
        db=db,
        chat_id=chat_id,
        message_text=message.text,
        manager_telegram_id=manager_id,
        manager_name=manager_name,
        message_thread_id=message_thread_id,
    )
    
    db.commit()
    
    bot_token = get_bot_token_by_chat(db, chat_id)
    if bot_token:
        telegram = TelegramService(bot_token)
        
        # If manager auto-took the handover, update buttons to [Решено]
        if success and took_handover and handover and handover.telegram_message_id:
            telegram._make_request("editMessageReplyMarkup", {
                "chat_id": chat_id,
                "message_id": handover.telegram_message_id,
                "reply_markup": {
                    "inline_keyboard": [[
                        {"text": "Решено ✅", "callback_data": f"resolve_{handover.id}"}
                    ]]
                }
            })
        
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
    settings = db.query(ClientSettings).filter(
        ClientSettings.telegram_chat_id == str(chat_id)
    ).first()
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
        handover_id = callback.data[first_underscore + 1:]
    except ValueError:
        return TelegramWebhookResponse(success=False, message=f"Invalid callback data: {callback.data}")
    
    print(f"Callback: action={action}, handover_id={handover_id}")
    
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
        telegram._make_request("answerCallbackQuery", {
            "callback_query_id": callback.id,
            "text": "❌ Заявка не найдена"
        })
        return TelegramWebhookResponse(success=False, message=f"Handover {handover_id} not found")
    
    # Get conversation
    conversation = db.query(Conversation).filter(Conversation.id == handover.conversation_id).first()
    
    # Get topic_id for sending messages
    topic_id = conversation.telegram_topic_id if conversation else None
    
    # Process action
    if action == "take":
        # Take: status='active', update buttons to [Решено]
        if handover.status != "pending":
            # Show who already took it
            taken_by = handover.assigned_to_name or "Кто-то"
            telegram._make_request("answerCallbackQuery", {
                "callback_query_id": callback.id,
                "text": f"⚠️ Заявку уже взял {taken_by}",
                "show_alert": True
            })
            return TelegramWebhookResponse(success=False, message="Handover not pending")
        
        handover.status = "active"
        handover.assigned_to = manager_id
        handover.assigned_to_name = manager_name
        handover.first_response_at = datetime.now(timezone.utc)
        
        if conversation:
            conversation.state = "manager_active"
        
        # Update buttons to [Решено]
        if message_id:
            telegram._make_request("editMessageReplyMarkup", {
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": {
                    "inline_keyboard": [[
                        {"text": "Решено ✅", "callback_data": f"resolve_{handover_id}"}
                    ]]
                }
            })
        
        # Send message to topic: who took the request
        if topic_id:
            telegram.send_message(
                chat_id=str(chat_id),
                text=f"👤 <b>{manager_name}</b> взял заявку",
                message_thread_id=topic_id,
            )
        
        telegram._make_request("answerCallbackQuery", {
            "callback_query_id": callback.id,
            "text": "✅ Вы взяли заявку"
        })
        
        db.commit()
        return TelegramWebhookResponse(success=True, message="Taken", conversation_id=handover.conversation_id)
    
    elif action == "resolve":
        # Resolve: status='resolved', unmute bot, unpin
        handover.status = "resolved"
        handover.resolved_at = datetime.now(timezone.utc)
        handover.resolved_by_id = manager_id
        handover.resolved_by_name = manager_name
        
        if conversation:
            # Unmute bot
            conversation.state = "bot_active"
            conversation.bot_status = "active"
            conversation.bot_muted_until = None
            conversation.no_count = 0
        
        # Remove buttons
        if message_id:
            telegram._make_request("editMessageReplyMarkup", {
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": {"inline_keyboard": []}
            })
        
        # Unpin
        if message_id:
            telegram.unpin_message(str(chat_id), message_id)
        
        telegram._make_request("answerCallbackQuery", {
            "callback_query_id": callback.id,
            "text": "✅ Заявка решена"
        })
        
        db.commit()
        return TelegramWebhookResponse(success=True, message="Resolved", conversation_id=handover.conversation_id)
    
    elif action == "skip":
        # Skip: just notification, no recording needed
        telegram._make_request("answerCallbackQuery", {
            "callback_query_id": callback.id,
            "text": "⏭️ Пропущено"
        })
        return TelegramWebhookResponse(success=True, message="Skipped")
    
    else:
        telegram._make_request("answerCallbackQuery", {
            "callback_query_id": callback.id,
            "text": f"❓ Неизвестное действие: {action}"
        })
        return TelegramWebhookResponse(success=False, message=f"Unknown action: {action}")
