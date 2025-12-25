from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ClientSettings
from app.schemas.message import MessageRequest, MessageResponse
from app.services.chatflow_service import send_bot_response
from app.services.conversation_service import (
    get_or_create_conversation,
    get_or_create_user,
)
from app.services.escalation_service import escalate_conversation
from app.services.intent_service import Intent, classify_intent, is_rejection, should_escalate
from app.services.message_service import (
    generate_bot_response,
    save_message,
    select_handover_user_message,
)
from app.services.state_machine import ConversationState, escalate

router = APIRouter()

DEFAULT_MUTE_DURATION_FIRST_MINUTES = 30
DEFAULT_MUTE_DURATION_SECOND_HOURS = 24
MSG_ESCALATED = "Передал менеджеру. Могу чем-то помочь пока ждёте?"
MSG_MUTED_TEMP = "Хорошо, напишите если понадоблюсь."
MSG_MUTED_LONG = "Понял! Если ответа от менеджеров долго нет — лучше звоните напрямую: +7 775 984 19 26"
MSG_LOW_CONFIDENCE = "Хороший вопрос! Уточню у коллег и вернусь с ответом."
MSG_AI_ERROR = "Извините, произошла ошибка. Попробуйте позже."


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


@router.post("/message", response_model=MessageResponse)
def handle_message(request: MessageRequest, db: Session = Depends(get_db)):
    """Handle incoming message from client."""

    # 1. Get or create user
    user = get_or_create_user(db, request.client_id, request.remote_jid)

    # 2. Get or create conversation
    conversation = get_or_create_conversation(db, request.client_id, user.id, request.channel)

    # 3. Save user message
    save_message(db, conversation.id, request.client_id, role="user", content=request.content)

    # 4. Update last_message_at
    conversation.last_message_at = datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)

    # 5. Check if bot is muted
    bot_response = None
    sent = False
    message = None
    intent = None

    # Полностью замьючен
    if conversation.bot_status == "muted":
        db.commit()
        return MessageResponse(
            success=True,
            conversation_id=conversation.id,
            state=conversation.state,
            intent=None,
            bot_response=None,
            message="Bot is permanently muted",
        )

    # Временно замьючен
    if conversation.bot_muted_until and conversation.bot_muted_until > now:
        db.commit()
        return MessageResponse(
            success=True,
            conversation_id=conversation.id,
            state=conversation.state,
            intent=None,
            bot_response=None,
            message=f"Bot muted until {conversation.bot_muted_until}",
        )

    # 6. Classify intent
    intent = classify_intent(request.content)

    # 7. Handle based on intent and state
    if conversation.state == ConversationState.BOT_ACTIVE.value and should_escalate(intent):
        handover_message = request.content
        if intent == Intent.HUMAN_REQUEST:
            handover_message = select_handover_user_message(db, conversation.id, request.content)

        # Escalate to pending + create handover + notify Telegram
        new_state = escalate(ConversationState(conversation.state))
        conversation.state = new_state.value
        conversation.escalated_at = now

        # Create handover and send to Telegram
        handover, telegram_sent = escalate_conversation(
            db=db,
            conversation=conversation,
            user=user,
            trigger_type="intent",  # DB constraint allows only: intent, keyword, manual, timeout
            trigger_value=intent.value,  # Store actual intent here
            user_message=handover_message,
        )

        # Send response to client
        bot_response = MSG_ESCALATED
        save_message(db, conversation.id, request.client_id, role="assistant", content=bot_response)
        sent = send_bot_response(db, request.client_id, request.remote_jid, bot_response)
        message = f"Escalated, handover created, telegram={'sent' if telegram_sent else 'failed'}"

    elif is_rejection(intent):
        # Client rejects bot help
        mute_first, mute_second = get_mute_settings(db, request.client_id)
        if conversation.no_count == 0:
            # First rejection: mute (default 30 min)
            conversation.bot_muted_until = now + timedelta(minutes=mute_first)
            conversation.no_count = 1
            bot_response = MSG_MUTED_TEMP
            save_message(db, conversation.id, request.client_id, role="assistant", content=bot_response)
            sent = send_bot_response(db, request.client_id, request.remote_jid, bot_response)
            message = f"Muted for {mute_first} min (first rejection)"
        else:
            # Second+ rejection: mute (default 24 hours)
            conversation.bot_muted_until = now + timedelta(hours=mute_second)
            conversation.no_count += 1
            bot_response = MSG_MUTED_LONG
            save_message(db, conversation.id, request.client_id, role="assistant", content=bot_response)
            sent = send_bot_response(db, request.client_id, request.remote_jid, bot_response)
            message = f"Muted for {mute_second}h (repeated rejection)"

    elif conversation.state == ConversationState.BOT_ACTIVE.value:
        # Normal flow: generate AI response
        result = generate_bot_response(db, conversation, request.content)

        if not result.ok:
            # AI error — fallback response
            bot_response = MSG_AI_ERROR
            save_message(db, conversation.id, request.client_id, role="assistant", content=bot_response)
            sent = send_bot_response(db, request.client_id, request.remote_jid, bot_response)
            message = f"AI error: {result.error}"
        else:
            response_text, confidence = result.value

            if confidence == "low_confidence":
                # Low RAG confidence — escalate
                new_state = escalate(ConversationState(conversation.state))
                conversation.state = new_state.value
                conversation.escalated_at = now

                handover, telegram_sent = escalate_conversation(
                    db=db,
                    conversation=conversation,
                    user=user,
                    trigger_type="intent",
                    trigger_value="low_confidence",
                    user_message=request.content,
                )

                bot_response = MSG_LOW_CONFIDENCE
                save_message(db, conversation.id, request.client_id, role="assistant", content=bot_response)
                sent = send_bot_response(db, request.client_id, request.remote_jid, bot_response)
                message = f"Low confidence escalation, telegram={'sent' if telegram_sent else 'failed'}"

            elif confidence == "bot_inactive":
                message = f"Bot not active (state: {conversation.state})"

            elif response_text:
                # Normal response
                bot_response = response_text
                save_message(db, conversation.id, request.client_id, role="assistant", content=bot_response)
                sent = send_bot_response(db, request.client_id, request.remote_jid, bot_response)
                message = "Message sent" if sent else "Failed to send"
            else:
                message = "No response generated"
    else:
        message = f"Bot not active (state: {conversation.state})"

    db.commit()

    return MessageResponse(
        success=True,
        conversation_id=conversation.id,
        state=conversation.state,
        intent=intent.value if intent else None,
        bot_response=bot_response,
        message=message,
    )
