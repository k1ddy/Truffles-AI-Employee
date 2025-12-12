from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class MessageRequest(BaseModel):
    client_id: UUID
    remote_jid: str
    content: str
    channel: str = "whatsapp"


class MessageResponse(BaseModel):
    success: bool
    conversation_id: UUID
    state: str
    intent: Optional[str] = None
    bot_response: Optional[str] = None
    message: Optional[str] = None
