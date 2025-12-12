from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.models import Client, ClientSettings, Handover
from app.schemas.webhook import WebhookRequest, WebhookResponse
from app.services.chatflow_service import send_bot_response
from app.services.conversation_service import (
    get_or_create_conversation,
    get_or_create_user,
)
from app.services.escalation_service import escalate_conversation, get_telegram_credentials
from app.services.intent_service import classify_intent, is_rejection, should_escalate
from app.services.message_service import generate_bot_response, save_message
from app.services.state_machine import ConversationState, escalate
from app.services.telegram_service import TelegramService

logger = get_logger("webhook")

router = APIRouter()

# Default values (can be overridden in client_settings)
DEFAULT_MUTE_DURATION_FIRST_MINUTES = 30
DEFAULT_MUTE_DURATION_SECOND_HOURS = 24
SESSION_TIMEOUT_HOURS = 24
MSG_ESCALATED = "Передал менеджеру. Могу чем-то помочь пока ждёте?"
MSG_MUTED_TEMP = "Хорошо, напишите если понадоблюсь."
MSG_MUTED_LONG = "Понял! Если ответа от менеджеров долго нет — лучше звоните напрямую: +7 775 984 19 26"


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

    if not message_text:
        return WebhookResponse(success=False, message="Empty message")

    # 1. Get or create user
    user = get_or_create_user(db, client.id, remote_jid)

    # 2. Get or create conversation
    conversation = get_or_create_conversation(db, client.id, user.id, "whatsapp")

    # 3. Save user message
    save_message(db, conversation.id, client.id, role="user", content=message_text)

    # 4. Update last_message_at
    conversation.last_message_at = datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)

    # 5. Check session timeout - reset mute if no messages for 24h+
    bot_response = None
    sent = False
    result_message = None
    intent = None

    # Reset mute if new session (no messages for 24h+)
    if conversation.last_message_at:
        time_since_last = now - conversation.last_message_at
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

    # 6. Classify intent
    intent = classify_intent(message_text)
    logger.info(f"Intent classified: {intent.value}")

    # 6.1 FIX: If state=manager_active/pending but no topic — reset to bot_active
    # Without topic, manager can't respond, so return bot to active state
    if conversation.state in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]:
        if not conversation.telegram_topic_id:
            logger.warning(f"state={conversation.state} but no telegram_topic_id. Resetting to bot_active.")
            conversation.state = ConversationState.BOT_ACTIVE.value
            # Close any open handovers for this conversation
            open_handovers = (
                db.query(Handover)
                .filter(Handover.conversation_id == conversation.id, Handover.status.in_(["pending", "active"]))
                .all()
            )
            for h in open_handovers:
                h.status = "resolved"
                h.resolved_at = now
                logger.info(f"Auto-closed handover {h.id} due to missing topic")

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

    # 8. If muted - don't respond, just forward
    if is_muted:
        db.commit()
        return WebhookResponse(
            success=True,
            message="Bot muted, forwarded to topic" if conversation.telegram_topic_id else "Bot muted",
            conversation_id=conversation.id,
            bot_response=None,
        )

    # 9. Handle based on intent and state
    if conversation.state == ConversationState.BOT_ACTIVE.value and should_escalate(intent):
        # Escalate to pending + create handover + notify Telegram
        new_state = escalate(ConversationState(conversation.state))
        conversation.state = new_state.value
        conversation.escalated_at = now

        # Create handover and send to Telegram
        handover, telegram_sent = escalate_conversation(
            db=db,
            conversation=conversation,
            user=user,
            trigger_type="intent",
            trigger_value=intent.value,
            user_message=message_text,
        )

        bot_response = MSG_ESCALATED
        save_message(db, conversation.id, client.id, role="assistant", content=bot_response)
        sent = send_bot_response(db, client.id, remote_jid, bot_response)
        result_message = f"Escalated ({intent.value}), telegram={'sent' if telegram_sent else 'failed'}"

    elif is_rejection(intent):
        # Client rejects bot help
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

    elif conversation.state == ConversationState.MANAGER_ACTIVE.value:
        # Manager is active - bot stays silent, message already forwarded above
        result_message = "Manager active, message forwarded"

    elif conversation.state in [ConversationState.BOT_ACTIVE.value, ConversationState.PENDING.value]:
        # Bot responds: normal mode OR pending (bot helps while waiting)
        bot_response = generate_bot_response(db, conversation, message_text, request.client_slug)
        logger.debug(f"bot_response: {bot_response[:100] if bot_response else 'None/Empty'}...")
        if bot_response:
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
