from pydantic import BaseModel
from typing import Optional, Literal
from uuid import UUID


class CallbackRequest(BaseModel):
    conversation_id: UUID
    action: Literal["take", "resolve", "skip", "return"]
    manager_id: str
    manager_name: Optional[str] = None


class CallbackResponse(BaseModel):
    success: bool
    conversation_id: UUID
    action: str
    old_state: str
    new_state: str
    message: Optional[str] = None
