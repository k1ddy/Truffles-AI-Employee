from pydantic import BaseModel
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime


class ReminderItem(BaseModel):
    handover_id: UUID
    conversation_id: UUID
    client_id: UUID
    reminder_type: Literal["reminder_1", "reminder_2"]
    created_at: datetime
    minutes_waiting: int
    telegram_chat_id: Optional[str] = None
    telegram_message_id: Optional[int] = None
    telegram_bot_token: Optional[str] = None
    channel_ref: Optional[str] = None
    context_summary: Optional[str] = None
    owner_telegram_id: Optional[str] = None


class RemindersResponse(BaseModel):
    count: int
    reminders: list[ReminderItem]


class ReminderSentRequest(BaseModel):
    reminder_type: Literal["reminder_1", "reminder_2"]


class ReminderSentResponse(BaseModel):
    success: bool
    handover_id: UUID
    reminder_type: str
    message: str
