from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from app.contracts import Result


@dataclass
class MessageOptions:
    """Options for sending a message."""
    instance_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    caption: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

@dataclass
class MessageSent:
    """Result of a successful message send."""
    remote_jid: str
    message_id: Optional[str] = None
    provider_response: dict[str, Any] = field(default_factory=dict)

class MessagingPort(ABC):
    """Abstract interface for messaging providers (WhatsApp, Telegram, etc)."""

    @abstractmethod
    def send_text(self, to: str, text: str, options: MessageOptions) -> Result[MessageSent]:
        """Send a text message."""
        pass

    @abstractmethod
    def send_media(self, to: str, media_url: str, media_type: str, options: MessageOptions) -> Result[MessageSent]:
        """
        Send a media message.
        media_type should be one of: 'image', 'video', 'audio', 'document'.
        """
        pass
