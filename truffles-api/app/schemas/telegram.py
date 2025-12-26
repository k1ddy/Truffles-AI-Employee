from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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


class TelegramPhotoSize(BaseModel):
    file_id: str
    file_unique_id: str
    width: int
    height: int
    file_size: Optional[int] = None


class TelegramDocument(BaseModel):
    file_id: str
    file_unique_id: str
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None


class TelegramAudio(BaseModel):
    file_id: str
    file_unique_id: str
    duration: int
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None


class TelegramVoice(BaseModel):
    file_id: str
    file_unique_id: str
    duration: int
    mime_type: Optional[str] = None
    file_size: Optional[int] = None


class TelegramVideo(BaseModel):
    file_id: str
    file_unique_id: str
    width: int
    height: int
    duration: int
    mime_type: Optional[str] = None
    file_size: Optional[int] = None


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
    caption: Optional[str] = None
    photo: Optional[list[TelegramPhotoSize]] = None
    document: Optional[TelegramDocument] = None
    audio: Optional[TelegramAudio] = None
    voice: Optional[TelegramVoice] = None
    video: Optional[TelegramVideo] = None

    model_config = ConfigDict(populate_by_name=True)

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
