from pathlib import Path
from typing import Optional
from uuid import UUID

import httpx

from app.logging_config import get_logger

logger = get_logger("telegram_service")


class TelegramService:
    """Service for sending messages to Telegram."""

    BASE_URL = "https://api.telegram.org/bot{token}"

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = self.BASE_URL.format(token=bot_token)

    def _make_request(self, method: str, data: Optional[dict] = None, files: Optional[dict] = None) -> dict:
        """Make request to Telegram API."""
        url = f"{self.base_url}/{method}"
        try:
            with httpx.Client(timeout=30.0) as client:
                if files:
                    response = client.post(url, data=data or {}, files=files)
                else:
                    response = client.post(url, json=data or {})
                return response.json()
        except Exception as e:
            logger.error(f"Telegram API error: {e}")
            return {"ok": False, "error": str(e)}

    def send_message(
        self,
        chat_id: str,
        text: str,
        reply_markup: Optional[dict] = None,
        parse_mode: str = "HTML",
        message_thread_id: Optional[int] = None,
        reply_to_message_id: Optional[int] = None,
    ) -> dict:
        """Send message to Telegram chat."""
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            data["reply_markup"] = reply_markup
        if message_thread_id:
            data["message_thread_id"] = message_thread_id
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        return self._make_request("sendMessage", data)

    def send_photo(
        self,
        chat_id: str,
        photo: str,
        caption: Optional[str] = None,
        parse_mode: str = "HTML",
        message_thread_id: Optional[int] = None,
        reply_to_message_id: Optional[int] = None,
    ) -> dict:
        """Send photo to Telegram chat."""
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = parse_mode
        if message_thread_id:
            data["message_thread_id"] = message_thread_id
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        if photo.startswith("http://") or photo.startswith("https://"):
            data["photo"] = photo
            return self._make_request("sendPhoto", data=data)

        path = Path(photo)
        with path.open("rb") as handle:
            return self._make_request("sendPhoto", data=data, files={"photo": handle})

    def send_document(
        self,
        chat_id: str,
        document: str,
        caption: Optional[str] = None,
        parse_mode: str = "HTML",
        message_thread_id: Optional[int] = None,
        reply_to_message_id: Optional[int] = None,
    ) -> dict:
        """Send document to Telegram chat."""
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = parse_mode
        if message_thread_id:
            data["message_thread_id"] = message_thread_id
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        if document.startswith("http://") or document.startswith("https://"):
            data["document"] = document
            return self._make_request("sendDocument", data=data)

        path = Path(document)
        with path.open("rb") as handle:
            return self._make_request("sendDocument", data=data, files={"document": handle})

    def send_audio(
        self,
        chat_id: str,
        audio: str,
        caption: Optional[str] = None,
        parse_mode: str = "HTML",
        message_thread_id: Optional[int] = None,
        reply_to_message_id: Optional[int] = None,
    ) -> dict:
        """Send audio to Telegram chat."""
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = parse_mode
        if message_thread_id:
            data["message_thread_id"] = message_thread_id
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        if audio.startswith("http://") or audio.startswith("https://"):
            data["audio"] = audio
            return self._make_request("sendAudio", data=data)

        path = Path(audio)
        with path.open("rb") as handle:
            return self._make_request("sendAudio", data=data, files={"audio": handle})

    def send_voice(
        self,
        chat_id: str,
        voice: str,
        caption: Optional[str] = None,
        parse_mode: str = "HTML",
        message_thread_id: Optional[int] = None,
        reply_to_message_id: Optional[int] = None,
    ) -> dict:
        """Send voice note to Telegram chat."""
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = parse_mode
        if message_thread_id:
            data["message_thread_id"] = message_thread_id
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id

        if voice.startswith("http://") or voice.startswith("https://"):
            data["voice"] = voice
            return self._make_request("sendVoice", data=data)

        path = Path(voice)
        with path.open("rb") as handle:
            return self._make_request("sendVoice", data=data, files={"voice": handle})

    def pin_message(self, chat_id: str, message_id: int) -> dict:
        """Pin message in chat."""
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "disable_notification": True,
        }
        return self._make_request("pinChatMessage", data)

    def unpin_message(self, chat_id: str, message_id: int) -> dict:
        """Unpin message in chat."""
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
        }
        return self._make_request("unpinChatMessage", data)

    def edit_message(
        self,
        chat_id: str,
        message_id: int,
        text: str,
        reply_markup: Optional[dict] = None,
        parse_mode: str = "HTML",
    ) -> dict:
        """Edit existing message."""
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            data["reply_markup"] = reply_markup

        return self._make_request("editMessageText", data)

    def create_forum_topic(self, chat_id: str, name: str) -> Optional[int]:
        """Create forum topic in supergroup. Returns topic_id or None."""
        data = {
            "chat_id": chat_id,
            "name": name,
        }
        result = self._make_request("createForumTopic", data)

        if result.get("ok"):
            return result["result"]["message_thread_id"]
        else:
            logger.warning(f"Failed to create topic: {result}")
            return None


def build_handover_buttons(handover_id: UUID) -> dict:
    """Build inline keyboard for handover message."""
    return {
        "inline_keyboard": [
            [
                {"text": "Беру ✋", "callback_data": f"take_{handover_id}"},
                {"text": "Вернуть боту 🤖", "callback_data": f"return_{handover_id}"},
            ],
            [
                {"text": "Не могу ❌", "callback_data": f"skip_{handover_id}"},
            ],
        ]
    }


def format_handover_message(
    user_name: Optional[str],
    user_phone: Optional[str],
    message: str,
    trigger_type: str,
) -> str:
    """Format handover notification message."""
    name = user_name or "Неизвестный"
    phone = user_phone or "нет номера"

    trigger_labels = {
        "human_request": "Клиент попросил менеджера",
        "frustration": "Клиент раздражён",
        "intent": "Автоматическая эскалация",
        "manual": "Ручная эскалация",
    }
    trigger_label = trigger_labels.get(trigger_type, trigger_type)

    return f"""🔔 <b>Новая заявка</b>

<b>Клиент:</b> {name}
<b>Телефон:</b> {phone}
<b>Причина:</b> {trigger_label}

<b>Сообщение:</b>
{message}"""
