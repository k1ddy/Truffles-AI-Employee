from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class WebhookMetadata(BaseModel):
    sender: Optional[str] = None
    timestamp: Optional[int] = None
    messageId: Optional[str] = None
    remoteJid: Optional[str] = None


class WebhookBody(BaseModel):
    messageType: Optional[str] = "text"
    message: Optional[str] = None
    metadata: Optional[WebhookMetadata] = None
    mediaData: Optional[Any] = None


class WebhookRequest(BaseModel):
    body: WebhookBody
    client_slug: Optional[str] = "truffles"


class WebhookResponse(BaseModel):
    success: bool
    message: str
    conversation_id: Optional[UUID] = None
    bot_response: Optional[str] = None
