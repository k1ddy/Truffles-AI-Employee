from typing import Any, Optional
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field


class WebhookMetadata(BaseModel):
    sender: Optional[str] = None
    timestamp: Optional[int] = None
    messageId: Optional[str] = None
    remoteJid: Optional[str] = None
    instanceId: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("instanceId", "instance_id", "instance"),
    )
    forwarded_to_telegram: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("forwarded_to_telegram", "forwardedToTelegram"),
    )


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
