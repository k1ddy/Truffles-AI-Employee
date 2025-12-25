from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class TelegramUser(BaseModel):
    id: int
    is_bot: bool = False
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None


class TelegramChat(BaseModel):
    id: int
    type: str  # private, group, supergroup, channel
    title: Optional[str] = None
    username: Optional[str] = None
    is_forum: Optional[bool] = None


class TelegramMessage(BaseModel):
    message_id: int
    date: int
    chat: TelegramChat
    from_user: Optional[TelegramUser] = None  # "from" is reserved in Python
    text: Optional[str] = None
    message_thread_id: Optional[int] = None  # Topic ID for forum groups
    reply_to_message: Optional[Any] = None
    sender_chat: Optional[TelegramChat] = None
    author_signature: Optional[str] = None

    class Config:
        # Allow "from" field from Telegram API
        populate_by_name = True

    def __init__(self, **data):
        # Handle "from" -> "from_user" mapping
        if "from" in data:
            data["from_user"] = data.pop("from")
        super().__init__(**data)


class TelegramCallbackQuery(BaseModel):
    id: str
    from_user: TelegramUser
    message: Optional[TelegramMessage] = None
    data: Optional[str] = None  # callback_data from button

    def __init__(self, **data):
        if "from" in data:
            data["from_user"] = data.pop("from")
        super().__init__(**data)


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None
    callback_query: Optional[TelegramCallbackQuery] = None


class TelegramWebhookResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    conversation_id: Optional[UUID] = None
