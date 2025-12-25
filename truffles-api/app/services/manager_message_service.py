import hashlib
import mimetypes
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import ClientSettings, Conversation, Handover, User
from app.services.chatflow_service import (
    build_signed_media_url,
    get_instance_id,
    send_bot_response,
    send_whatsapp_media,
)
from app.services.learning_service import add_to_knowledge, get_client_slug, is_owner_response
from app.services.message_service import save_message
from app.services.telegram_service import TelegramService

logger = get_logger("manager_message_service")

MEDIA_STORAGE_BASE_DIR = Path(os.environ.get("MEDIA_STORAGE_DIR", "/home/zhan/truffles-media"))
MEDIA_MANAGER_DIRNAME = "manager"


def _safe_media_id(value: Optional[str]) -> str:
    if not value:
        return "media"
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", str(value))
    return cleaned or "media"


def _guess_media_extension(mime_type: Optional[str], file_name: Optional[str], fallback_ext: str) -> str:
    if file_name:
        suffix = Path(file_name).suffix
        if suffix:
            return suffix
    if mime_type:
        ext = mimetypes.guess_extension(mime_type.split(";")[0].strip())
        if ext:
            return ext
    return fallback_ext


def _build_manager_media_path(
    *,
    client_slug: str,
    conversation_id: UUID,
    media_id: str,
    file_name: Optional[str],
    mime_type: Optional[str],
    fallback_ext: str,
) -> Path:
    safe_id = _safe_media_id(media_id)
    ext = _guess_media_extension(mime_type, file_name, fallback_ext)
    target_dir = MEDIA_STORAGE_BASE_DIR / client_slug / str(conversation_id) / MEDIA_MANAGER_DIRNAME
    return target_dir / f"{safe_id}{ext}"


def _update_media_metadata(message, updates: dict) -> None:
    metadata = dict(getattr(message, "message_metadata", {}) or {})
    media_meta = dict(metadata.get("media") or {})
    media_meta.update(updates)
    metadata["media"] = media_meta
    message.message_metadata = metadata


def is_probably_whatsapp_jid(value: Optional[str]) -> bool:
    if not value:
        return False
    return "@" in value


def find_conversation_by_telegram(
    db: Session,
    chat_id: int,
    message_thread_id: Optional[int] = None,
) -> Optional[Tuple[Conversation, Handover]]:
    """
    Find conversation by Telegram chat_id and optional topic_id.

    Strategy:
    1. If message_thread_id exists - find handover by telegram_message_id in that thread
    2. Otherwise find by chat_id in client_settings + active handover
    """
    # Find client by telegram_chat_id
    settings = db.query(ClientSettings).filter(ClientSettings.telegram_chat_id == str(chat_id)).first()

    if not settings:
        logger.warning(f"No client found for telegram chat_id={chat_id}")
        return None

    # Preferred strategy: topic-based routing (avoid cross-client mix-ups)
    if message_thread_id:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.client_id == settings.client_id,
                Conversation.telegram_topic_id == message_thread_id,
            )
            .first()
        )

        if not conversation:
            logger.warning(
                f"No conversation found for client={settings.client_id}, topic_id={message_thread_id}"
            )
            return None

        handover = (
            db.query(Handover)
            .filter(
                Handover.conversation_id == conversation.id,
                Handover.status.in_(["pending", "active"]),
            )
            .order_by(Handover.created_at.desc())
            .first()
        )

        if not handover:
            logger.warning(f"No active handover for conversation {conversation.id} in topic {message_thread_id}")
            return None

        return conversation, handover

    # Fallback strategy (no topic): pick latest active handover for this client
    handover = (
        db.query(Handover)
        .filter(
            Handover.client_id == settings.client_id,
            Handover.status.in_(["pending", "active"]),
        )
        .order_by(Handover.created_at.desc())
        .first()
    )

    if not handover:
        logger.debug(f"No active handover for client {settings.client_id}")
        return None

    conversation = db.query(Conversation).filter(Conversation.id == handover.conversation_id).first()

    if not conversation:
        logger.warning(f"Conversation not found for handover {handover.id}")
        return None

    return conversation, handover


def get_user_remote_jid(db: Session, user_id: UUID) -> Optional[str]:
    """Get user's WhatsApp remote_jid."""
    user = db.query(User).filter(User.id == user_id).first()
    return user.remote_jid if user else None


def _prepare_handover_for_manager(
    db: Session,
    chat_id: int,
    message_thread_id: Optional[int],
    manager_telegram_id: int,
    manager_name: str,
) -> Tuple[Optional[Conversation], Optional[Handover], bool, str]:
    result = find_conversation_by_telegram(db, chat_id, message_thread_id)
    if not result:
        logger.warning(f"No conversation found for chat_id={chat_id}, thread={message_thread_id}")
        return None, None, False, "No active conversation found for this chat"

    conversation, handover = result
    took_handover = False

    if handover.status == "pending":
        handover.status = "active"
        handover.first_response_at = datetime.now(timezone.utc)
        if manager_telegram_id:
            handover.assigned_to = str(manager_telegram_id)
        if manager_name and manager_name != "Unknown":
            handover.assigned_to_name = manager_name
        took_handover = True
        conversation.state = "manager_active"

    return conversation, handover, took_handover, ""


def process_manager_message(
    db: Session,
    chat_id: int,
    message_text: str,
    manager_telegram_id: int,
    manager_name: str,
    manager_username: Optional[str] = None,
    message_thread_id: Optional[int] = None,
) -> Tuple[bool, str, bool, Optional[Handover]]:
    """
    Process message from manager in Telegram and forward to client.

    Returns: (success, message, took_handover, handover)
    """
    logger.info(f"process_manager_message: chat_id={chat_id}, manager={manager_telegram_id}, thread={message_thread_id}")

    conversation, handover, took_handover, error = _prepare_handover_for_manager(
        db, chat_id, message_thread_id, manager_telegram_id, manager_name
    )
    if not conversation or not handover:
        return False, error or "No active conversation found for this chat", False, None

    # 3. Save manager message
    save_message(
        db=db,
        conversation_id=conversation.id,
        client_id=conversation.client_id,
        role="manager",
        content=message_text,
    )

    # Update handover with manager response
    handover.manager_response = message_text

    # Auto-learn from owner responses
    effective_manager_id = manager_telegram_id if manager_telegram_id else None
    if not effective_manager_id and handover.assigned_to:
        assigned_raw = str(handover.assigned_to).strip()
        if assigned_raw.lstrip("-").isdigit():
            effective_manager_id = int(assigned_raw)

    if effective_manager_id or manager_username:
        if is_owner_response(
            db,
            handover.client_id,
            effective_manager_id or 0,
            manager_username,
        ):
            logger.info("Owner response detected, auto-adding to knowledge base")
            point_id = add_to_knowledge(db, handover, source="owner")
            if point_id:
                logger.info(f"Successfully added to knowledge: {point_id}")
    else:
        logger.info(
            "Owner response check skipped: missing manager identity",
            extra={
                "context": {
                    "handover_id": str(handover.id),
                    "chat_id": chat_id,
                    "thread_id": message_thread_id,
                }
            },
        )

    # 4. Get user's WhatsApp JID (authoritative source: user.remote_jid)
    user_remote_jid = get_user_remote_jid(db, conversation.user_id)
    remote_jid = user_remote_jid

    # Fallback for legacy/broken data
    if not is_probably_whatsapp_jid(remote_jid):
        remote_jid = handover.channel_ref if is_probably_whatsapp_jid(handover.channel_ref) else None

    # Self-heal mismatch: never trust channel_ref if it points to another WhatsApp JID
    if is_probably_whatsapp_jid(user_remote_jid) and handover.channel_ref != user_remote_jid:
        if is_probably_whatsapp_jid(handover.channel_ref):
            logger.warning(
                "handover.channel_ref mismatch: "
                f"'{handover.channel_ref}' != user.remote_jid '{user_remote_jid}', fixing"
            )
        handover.channel_ref = user_remote_jid

    if not remote_jid:
        return False, "User remote_jid not found", took_handover, handover

    # 5. Send to WhatsApp
    sent = send_bot_response(
        db=db,
        client_id=conversation.client_id,
        remote_jid=remote_jid,
        message=message_text,
    )

    if sent:
        return True, f"Message forwarded to client (conversation {conversation.id})", took_handover, handover
    else:
        return False, "Failed to send message to WhatsApp", took_handover, handover


def process_manager_media(
    db: Session,
    *,
    chat_id: int,
    manager_telegram_id: int,
    manager_name: str,
    media_type: str,
    file_id: str,
    bot_token: str,
    caption: Optional[str] = None,
    file_name: Optional[str] = None,
    mime_type: Optional[str] = None,
    file_size: Optional[int] = None,
    manager_username: Optional[str] = None,
    message_thread_id: Optional[int] = None,
    telegram_message_id: Optional[int] = None,
) -> Tuple[bool, str, bool, Optional[Handover]]:
    logger.info(
        f"process_manager_media: chat_id={chat_id}, manager={manager_telegram_id}, thread={message_thread_id}, type={media_type}"
    )

    conversation, handover, took_handover, error = _prepare_handover_for_manager(
        db, chat_id, message_thread_id, manager_telegram_id, manager_name
    )
    if not conversation or not handover:
        return False, error or "No active conversation found for this chat", False, None

    if not bot_token:
        return False, "Telegram bot token not found", took_handover, handover
    if not file_id:
        return False, "Missing Telegram file_id", took_handover, handover

    client_slug = get_client_slug(db, conversation.client_id) or "truffles"
    fallback_ext = ".bin"
    if media_type == "photo":
        fallback_ext = ".jpg"
    elif media_type in {"audio", "voice"}:
        fallback_ext = ".ogg"
    elif media_type == "video":
        fallback_ext = ".mp4"
    elif media_type == "document":
        fallback_ext = ".bin"

    target_path = _build_manager_media_path(
        client_slug=client_slug,
        conversation_id=conversation.id,
        media_id=str(telegram_message_id or file_id),
        file_name=file_name,
        mime_type=mime_type,
        fallback_ext=fallback_ext,
    )

    content = caption.strip() if caption and caption.strip() else f"[{media_type}]"
    media_meta = {
        "type": media_type,
        "file_id": file_id,
        "file_name": file_name,
        "mime": mime_type,
        "size_bytes": file_size,
        "caption": caption,
        "storage_path": str(target_path),
        "stored": False,
        "source": "telegram",
    }
    saved_message = save_message(
        db=db,
        conversation_id=conversation.id,
        client_id=conversation.client_id,
        role="manager",
        content=content,
        message_metadata={"media": media_meta},
    )

    telegram = TelegramService(bot_token)
    file_path = telegram.get_file_path(file_id)
    if not file_path:
        _update_media_metadata(saved_message, {"storage_error": "telegram_file_not_found"})
        return False, "Failed to resolve Telegram file", took_handover, handover

    download_result = telegram.download_file(file_path, target_path)
    if not download_result.get("ok"):
        _update_media_metadata(saved_message, {"storage_error": download_result.get("error") or "download_failed"})
        return False, "Failed to download Telegram file", took_handover, handover

    sha256 = ""
    try:
        digest = hashlib.sha256()
        with target_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        sha256 = digest.hexdigest()
    except Exception as exc:
        logger.warning(f"Media hash failed: {exc}")

    _update_media_metadata(
        saved_message,
        {
            "stored": True,
            "size_bytes": file_size or download_result.get("size_bytes"),
            "sha256": sha256,
        },
    )

    if caption and caption.strip():
        handover.manager_response = caption.strip()

    # Auto-learn from owner responses (text only)
    if caption and caption.strip():
        effective_manager_id = manager_telegram_id if manager_telegram_id else None
        if not effective_manager_id and handover.assigned_to:
            assigned_raw = str(handover.assigned_to).strip()
            if assigned_raw.lstrip("-").isdigit():
                effective_manager_id = int(assigned_raw)
        if effective_manager_id or manager_username:
            if is_owner_response(
                db,
                handover.client_id,
                effective_manager_id or 0,
                manager_username,
            ):
                logger.info("Owner media caption detected, auto-adding to knowledge base")
                point_id = add_to_knowledge(db, handover, source="owner")
                if point_id:
                    logger.info(f"Successfully added to knowledge: {point_id}")

    user_remote_jid = get_user_remote_jid(db, conversation.user_id)
    remote_jid = user_remote_jid
    if not is_probably_whatsapp_jid(remote_jid):
        remote_jid = handover.channel_ref if is_probably_whatsapp_jid(handover.channel_ref) else None
    if is_probably_whatsapp_jid(user_remote_jid) and handover.channel_ref != user_remote_jid:
        if is_probably_whatsapp_jid(handover.channel_ref):
            logger.warning(
                "handover.channel_ref mismatch: "
                f"'{handover.channel_ref}' != user.remote_jid '{user_remote_jid}', fixing"
            )
        handover.channel_ref = user_remote_jid

    if not remote_jid:
        return False, "User remote_jid not found", took_handover, handover

    relative_path = str(target_path.relative_to(MEDIA_STORAGE_BASE_DIR))
    signed_url = build_signed_media_url(relative_path)
    if not signed_url:
        if saved_message:
            _update_media_metadata(saved_message, {"storage_error": "signed_url_missing"})
        return False, "Signed media URL unavailable", took_handover, handover
    if saved_message:
        _update_media_metadata(saved_message, {"public_url": signed_url})

    instance_id = get_instance_id(db, conversation.client_id)
    if not instance_id:
        return False, "Instance ID not found", took_handover, handover

    sent = send_whatsapp_media(
        instance_id,
        remote_jid,
        media_type=media_type,
        media_url=signed_url,
        caption=caption,
    )

    if sent:
        return True, f"Media forwarded to client (conversation {conversation.id})", took_handover, handover
    return False, "Failed to send media to WhatsApp", took_handover, handover
