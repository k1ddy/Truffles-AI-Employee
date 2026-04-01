from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class MessageRequest(BaseModel):
    client_id: UUID
    remote_jid: str
    content: str = Field(..., min_length=1)
    channel: str = "whatsapp"

    @field_validator("content", mode="before")
    @classmethod
    def _normalize_content(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class MessageResponse(BaseModel):
    success: bool
    conversation_id: UUID
    state: str
    intent: Optional[str] = None
    bot_response: Optional[str] = None
    message: Optional[str] = None
