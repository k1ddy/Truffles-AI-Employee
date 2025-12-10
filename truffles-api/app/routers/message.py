from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.database import get_db
from app.schemas.message import MessageRequest, MessageResponse
from app.services.conversation_service import (
    get_or_create_user,
    get_or_create_conversation,
)
from app.services.message_service import save_message, generate_bot_response
from app.services.chatflow_service import send_bot_response
from app.services.intent_service import classify_intent, should_escalate, is_rejection
from app.services.state_machine import ConversationState, escalate
from app.services.escalation_service import escalate_conversation

router = APIRouter()

MUTE_DURATION_MINUTES = 30
MSG_ESCALATED = "Передал менеджеру. Могу чем-то помочь пока ждёте?"
MSG_MUTED_TEMP = "Хорошо, напишите если понадоблюсь."
MSG_MUTED_FULL = "Понял, не буду беспокоить."


@router.post("/message", response_model=MessageResponse)
def handle_message(request: MessageRequest, db: Session = Depends(get_db)):
    """Handle incoming message from client."""
    
    # 1. Get or create user
    user = get_or_create_user(db, request.client_id, request.remote_jid)
    
    # 2. Get or create conversation
    conversation = get_or_create_conversation(
        db, 
        request.client_id, 
        user.id, 
        request.channel
    )
    
    # 3. Save user message
    save_message(
        db,
        conversation.id,
        request.client_id,
        role="user",
        content=request.content
    )
    
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
            message="Bot is permanently muted"
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
            message=f"Bot muted until {conversation.bot_muted_until}"
        )
    
    # 6. Classify intent
    intent = classify_intent(request.content)
    
    # 7. Handle based on intent and state
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
            trigger_type="intent",  # DB constraint allows only: intent, keyword, manual, timeout
            trigger_value=intent.value,  # Store actual intent here
            user_message=request.content,
        )
        
        # Send response to client
        bot_response = MSG_ESCALATED
        save_message(db, conversation.id, request.client_id, role="assistant", content=bot_response)
        sent = send_bot_response(db, request.client_id, request.remote_jid, bot_response)
        message = f"Escalated, handover created, telegram={'sent' if telegram_sent else 'failed'}"
        
    elif is_rejection(intent):
        # Client rejects bot help
        if conversation.no_count == 0:
            # First rejection: mute for 30 min
            conversation.bot_muted_until = now + timedelta(minutes=MUTE_DURATION_MINUTES)
            conversation.no_count = 1
            bot_response = MSG_MUTED_TEMP
            save_message(db, conversation.id, request.client_id, role="assistant", content=bot_response)
            sent = send_bot_response(db, request.client_id, request.remote_jid, bot_response)
            message = f"Muted for {MUTE_DURATION_MINUTES} min (first rejection)"
        else:
            # Second+ rejection: permanent mute
            conversation.bot_status = "muted"
            conversation.no_count += 1
            bot_response = MSG_MUTED_FULL
            save_message(db, conversation.id, request.client_id, role="assistant", content=bot_response)
            sent = send_bot_response(db, request.client_id, request.remote_jid, bot_response)
            message = "Permanently muted (repeated rejection)"
            
    elif conversation.state == ConversationState.BOT_ACTIVE.value:
        # Normal flow: generate AI response
        bot_response = generate_bot_response(db, conversation, request.content)
        if bot_response:
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
        message=message
    )
