from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Conversation
from app.routers.public_entrypoint_contract import (
    PublicEntrypointMaterializationMode,
    handle_public_webhook_payload,
)
from app.schemas.message import MessageRequest, MessageResponse
from app.schemas.webhook import WebhookBody, WebhookMetadata, WebhookRequest
from app.services.learning_service import get_client_slug

router = APIRouter()



@router.post("/message", response_model=MessageResponse)
async def handle_message(request: MessageRequest, db: Session = Depends(get_db)):
    """Handle incoming message through the shared webhook pipeline."""
    client_slug = get_client_slug(db, request.client_id)
    if not client_slug:
        raise HTTPException(status_code=404, detail="Client not found")

    metadata = WebhookMetadata(
        remoteJid=request.remote_jid,
        messageId=f"message-{uuid4()}",
        timestamp=int(datetime.now(timezone.utc).timestamp()),
    )
    payload = WebhookRequest(
        client_slug=client_slug,
        body=WebhookBody(
            message=request.content,
            messageType="text",
            metadata=metadata,
        ),
        tenant_context={
            "client_id": str(request.client_id),
            "client_slug": client_slug,
            "source": "message_api",
        },
    )

    response = await handle_public_webhook_payload(
        payload,
        db,
        entrypoint_name="Message",
        materialization_mode=PublicEntrypointMaterializationMode.REQUIRE_CONVERSATION,
        provided_secret=None,
        enforce_secret=False,
    )

    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == response.conversation_id)
        .first()
    )
    state = conversation.state if conversation else "unknown"

    return MessageResponse(
        success=response.success,
        conversation_id=response.conversation_id,
        state=state,
        intent=None,
        bot_response=response.bot_response,
        message=response.message,
    )
