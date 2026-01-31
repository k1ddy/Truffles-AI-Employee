import hashlib
import mimetypes
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Agent, AgentIdentity, Branch, ClientSettings, Conversation, Handover, Message, User
from app.services.audit_service import record_audit_event
from app.services.chatflow_service import (
    build_signed_media_url,
    get_instance_id,
    send_bot_response,
    send_whatsapp_media,
)
from app.services.console_errors import ConsoleAPIError
from app.services.learning_service import add_to_knowledge, get_client_slug, is_owner_response
from app.services.message_service import save_message
from app.services.outbox_service import build_inbound_message_id, enqueue_outbox_message
from app.services.state_service import is_simulation_context
from app.services.state_service import manager_take as state_manager_take
from app.services.telegram_service import TelegramService

logger = get_logger("manager_message_service")

MEDIA_STORAGE_BASE_DIR = Path(os.environ.get("MEDIA_STORAGE_DIR", "/home/zhan/truffles-media"))
MEDIA_MANAGER_DIRNAME = "manager"
MEDIA_CONSOLE_DIRNAME = "console"
CHATFLOW_MEDIA_TIMEOUT_SECONDS = float(os.environ.get("CHATFLOW_MEDIA_TIMEOUT_SECONDS", "90"))
MANAGER_CONNECTED_TEMPLATE = "👤 Менеджер {name} подключился. Сейчас отвечу."
MANAGER_DISCONNECTED_MESSAGE = "🤖 Заявка закрыта, бот снова отвечает."
CONSOLE_MEDIA_MAX_MB = {"photo": 8, "audio": 8, "document": 10}
CONSOLE_MEDIA_CHUNK_BYTES = 1024 * 1024


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


def _build_console_media_path(
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
    target_dir = MEDIA_STORAGE_BASE_DIR / client_slug / str(conversation_id) / MEDIA_CONSOLE_DIRNAME
    return target_dir / f"{safe_id}{ext}"


def _resolve_console_media_max_bytes(media_type: str) -> int:
    max_mb = CONSOLE_MEDIA_MAX_MB.get(media_type, 8)
    return max(max_mb, 1) * 1024 * 1024


async def _store_console_upload(
    upload: UploadFile,
    *,
    target_path: Path,
    max_bytes: int,
) -> dict:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    size_bytes = 0
    digest = hashlib.sha256()
    try:
        await upload.seek(0)
        with target_path.open("wb") as handle:
            while True:
                chunk = await upload.read(CONSOLE_MEDIA_CHUNK_BYTES)
                if not chunk:
                    break
                size_bytes += len(chunk)
                if max_bytes and size_bytes > max_bytes:
                    handle.close()
                    if target_path.exists():
                        target_path.unlink()
                    return {"stored": False, "error": "too_large", "size_bytes": size_bytes}
                digest.update(chunk)
                handle.write(chunk)
    except Exception as exc:
        if target_path.exists():
            target_path.unlink()
        return {"stored": False, "error": f"upload_failed:{exc}"}
    finally:
        try:
            await upload.close()
        except Exception:
            pass
    return {
        "stored": True,
        "path": str(target_path),
        "size_bytes": size_bytes,
        "sha256": digest.hexdigest(),
    }


def _update_media_metadata(message, updates: dict) -> None:
    metadata = dict(getattr(message, "message_metadata", {}) or {})
    media_meta = dict(metadata.get("media") or {})
    media_meta.update(updates)
    metadata["media"] = media_meta
    message.message_metadata = metadata


def _is_env_enabled(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _extract_signed_url_expires_at(signed_url: str) -> Optional[str]:
    if not signed_url:
        return None
    try:
        parsed = urlparse(signed_url)
        expires_values = parse_qs(parsed.query or "").get("expires")
        if not expires_values:
            return None
        expires = int(expires_values[0])
        return datetime.fromtimestamp(expires, tz=timezone.utc).isoformat()
    except Exception:
        return None


def is_probably_whatsapp_jid(value: Optional[str]) -> bool:
    if not value:
        return False
    return "@" in value


def resolve_linked_agent(
    db: Session,
    *,
    telegram_user_id: int,
    client_id: UUID,
    branch_id: Optional[UUID],
) -> Optional[Agent]:
    identity = (
        db.query(AgentIdentity)
        .join(Agent)
        .filter(
            AgentIdentity.channel == "telegram",
            AgentIdentity.external_id == str(telegram_user_id),
            Agent.client_id == client_id,
            Agent.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not identity or not identity.agent:
        return None
    agent = identity.agent
    if branch_id and agent.branch_id and agent.branch_id != branch_id:
        return None
    return agent


def notify_client_manager_status(
    db: Session,
    *,
    conversation: Conversation,
    handover: Handover,
    status: str,
    manager_name: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    remote_jid = get_user_remote_jid(db, conversation.user_id)
    if not is_probably_whatsapp_jid(remote_jid):
        return False, "remote_jid_missing"

    if status == "connected":
        name = (manager_name or "").strip() or "менеджер"
        message = MANAGER_CONNECTED_TEMPLATE.format(name=name)
        idempotency_key = f"manager_connected:{handover.id}"
    else:
        message = MANAGER_DISCONNECTED_MESSAGE
        idempotency_key = f"manager_disconnected:{handover.id}"

    save_message(
        db=db,
        conversation_id=conversation.id,
        client_id=conversation.client_id,
        role="assistant",
        content=message,
        message_metadata={"system": True, "event": f"manager_{status}", "source": "system"},
    )

    sent = send_bot_response(
        db=db,
        client_id=conversation.client_id,
        remote_jid=remote_jid,
        message=message,
        branch_id=conversation.branch_id,
        idempotency_key=idempotency_key,
    )
    if not sent:
        return False, "chatflow_failed"
    return True, None


def find_conversation_by_telegram(
    db: Session,
    chat_id: int,
    message_thread_id: Optional[int] = None,
) -> Optional[Tuple[Conversation, Handover]]:
    """
    Find conversation by Telegram chat_id and optional topic_id.

    Strategy:
    1. Require message_thread_id (topic per client)
    2. Resolve user by topic_id
    3. Find active handover for that user
    """
    # Find client by telegram_chat_id (branch preferred, fallback to client_settings)
    settings = db.query(ClientSettings).filter(ClientSettings.telegram_chat_id == str(chat_id)).first()
    if not settings:
        branch = db.query(Branch).filter(Branch.telegram_chat_id == str(chat_id)).first()
        if branch:
            settings = (
                db.query(ClientSettings)
                .filter(ClientSettings.client_id == branch.client_id)
                .first()
            )

    if not settings:
        logger.warning(f"No client found for telegram chat_id={chat_id}")
        return None

    if not message_thread_id:
        logger.warning(f"Manager message missing topic_id: chat_id={chat_id}")
        return None

    # Topics are reused across conversations; prefer active handover in this topic.
    handover = (
        db.query(Handover)
        .join(Conversation, Conversation.id == Handover.conversation_id)
        .filter(
            Conversation.client_id == settings.client_id,
            Conversation.telegram_topic_id == message_thread_id,
            Handover.status.in_(["pending", "active"]),
        )
        .order_by(Handover.created_at.desc())
        .first()
    )
    if handover:
        conversation = handover.conversation
        if not conversation:
            logger.warning(f"Conversation not found for handover {handover.id}")
            return None
        user = db.query(User).filter(User.id == conversation.user_id).first()
        if not user:
            logger.warning(f"Conversation {conversation.id} has no user")
            return None
        if user.telegram_topic_id != message_thread_id:
            user.telegram_topic_id = message_thread_id
            db.flush()
        if conversation.telegram_topic_id != message_thread_id:
            conversation.telegram_topic_id = message_thread_id
            db.flush()
        return conversation, handover

    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.client_id == settings.client_id,
            Conversation.telegram_topic_id == message_thread_id,
        )
        .first()
    )

    if conversation:
        user = db.query(User).filter(User.id == conversation.user_id).first()
        if not user:
            logger.warning(f"Conversation {conversation.id} has no user")
            return None
        if user.telegram_topic_id != message_thread_id:
            user.telegram_topic_id = message_thread_id
            db.flush()
        handover = (
            db.query(Handover)
            .filter(
                Handover.conversation_id == conversation.id,
                Handover.status.in_(["pending", "active"]),
            )
            .order_by(Handover.created_at.desc())
            .first()
        )
    else:
        user = (
            db.query(User)
            .filter(
                User.client_id == settings.client_id,
                User.telegram_topic_id == message_thread_id,
            )
            .first()
        )

        if not user:
            logger.warning(
                f"No user found for client={settings.client_id}, topic_id={message_thread_id}"
            )
            return None

        handover = (
            db.query(Handover)
            .join(Conversation, Conversation.id == Handover.conversation_id)
            .filter(
                Conversation.user_id == user.id,
                Handover.status.in_(["pending", "active"]),
            )
            .order_by(Handover.created_at.desc())
            .first()
        )

    if not handover:
        logger.warning(f"No active handover for user {user.id} in topic {message_thread_id}")
        return None

    if not conversation and handover:
        conversation = db.query(Conversation).filter(Conversation.id == handover.conversation_id).first()

    if not conversation:
        logger.warning(f"Conversation not found for handover {handover.id}")
        return None

    if conversation.telegram_topic_id != message_thread_id:
        conversation.telegram_topic_id = message_thread_id
        db.flush()

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
) -> Tuple[Optional[Conversation], Optional[Handover], Optional[Agent], bool, str]:
    result = find_conversation_by_telegram(db, chat_id, message_thread_id)
    if not result:
        logger.warning(f"No conversation found for chat_id={chat_id}, thread={message_thread_id}")
        return None, None, None, False, "No active conversation found for this chat"

    conversation, handover = result
    took_handover = False
    linked_agent = resolve_linked_agent(
        db,
        telegram_user_id=manager_telegram_id,
        client_id=conversation.client_id,
        branch_id=conversation.branch_id,
    )
    if not linked_agent:
        return None, None, None, False, "Access denied"

    if handover.status == "active":
        assigned_raw = str(handover.assigned_to or "").strip()
        if assigned_raw and assigned_raw != str(linked_agent.id):
            return None, None, None, False, "Access denied"

    if handover.status == "pending":
        take_result = state_manager_take(
            db,
            conversation,
            handover,
            str(linked_agent.id),
            linked_agent.name or manager_name,
        )
        if not take_result.ok:
            return None, None, None, False, take_result.error or "Case already taken"

        took_handover = True
        record_audit_event(
            db,
            actor=linked_agent,
            event_type="case_taken",
            entity_type="handover",
            entity_id=handover.id,
            payload={"previous_status": "pending"},
            branch_id=conversation.branch_id,
        )
        notify_ok, notify_detail = notify_client_manager_status(
            db,
            conversation=conversation,
            handover=handover,
            status="connected",
            manager_name=linked_agent.name or manager_name,
        )
        record_audit_event(
            db,
            actor=linked_agent,
            event_type="manager_connected",
            entity_type="handover",
            entity_id=handover.id,
            payload={
                "client_notify_status": "ok" if notify_ok else "failed",
                "client_notify_detail": notify_detail,
            },
            branch_id=conversation.branch_id,
        )

    return conversation, handover, linked_agent, took_handover, ""


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

    conversation, handover, linked_agent, took_handover, error = _prepare_handover_for_manager(
        db, chat_id, message_thread_id, manager_telegram_id, manager_name
    )
    if not conversation or not handover or not linked_agent:
        return False, error or "No active conversation found for this chat", False, None

    resolved_manager_name = linked_agent.name or manager_name

    # 3. Save manager message
    save_message(
        db=db,
        conversation_id=conversation.id,
        client_id=conversation.client_id,
        role="manager",
        content=message_text,
        message_metadata={"source": "telegram"},
    )

    # Update handover with manager response
    handover.manager_response = message_text
    if resolved_manager_name and resolved_manager_name != "Unknown":
        handover.assigned_to_name = resolved_manager_name

    if is_simulation_context(conversation):
        logger.info(
            "Simulation mode: skipping outbound and learning",
            extra={
                "context": {
                    "conversation_id": str(conversation.id),
                    "handover_id": str(handover.id),
                }
            },
        )
        return True, "Simulation: manager message recorded", took_handover, handover

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
        branch_id=conversation.branch_id,
    )

    if sent:
        return True, f"Message forwarded to client (conversation {conversation.id})", took_handover, handover
    else:
        return False, "Failed to send message to WhatsApp", took_handover, handover


async def process_console_media_upload(
    db: Session,
    *,
    conversation: Conversation,
    handover: Handover,
    agent: Agent,
    upload: UploadFile,
    media_type: str,
    caption: Optional[str],
    idempotency_key: Optional[str],
) -> tuple[Message, str, Optional[str]]:
    if media_type not in CONSOLE_MEDIA_MAX_MB:
        raise ConsoleAPIError(400, "MEDIA_UNSUPPORTED", "Unsupported media type")

    client_slug = get_client_slug(db, conversation.client_id) or "truffles"
    fallback_ext = ".bin"
    if media_type == "photo":
        fallback_ext = ".jpg"
    elif media_type == "audio":
        fallback_ext = ".ogg"

    target_path = _build_console_media_path(
        client_slug=client_slug,
        conversation_id=conversation.id,
        media_id=str(uuid4()),
        file_name=upload.filename,
        mime_type=upload.content_type,
        fallback_ext=fallback_ext,
    )
    store_result = await _store_console_upload(
        upload,
        target_path=target_path,
        max_bytes=_resolve_console_media_max_bytes(media_type),
    )
    if not store_result.get("stored"):
        error = store_result.get("error") or "upload_failed"
        if error == "too_large":
            raise ConsoleAPIError(400, "MEDIA_TOO_LARGE", "Файл слишком большой. Попробуйте меньший размер.")
        raise ConsoleAPIError(500, "MEDIA_UPLOAD_FAILED", "Не удалось загрузить файл")

    size_bytes = store_result.get("size_bytes") or 0
    if size_bytes <= 0:
        raise ConsoleAPIError(400, "MEDIA_EMPTY", "Файл пустой")

    content = caption.strip() if caption and caption.strip() else f"[{media_type}]"
    media_meta = {
        "type": media_type,
        "file_name": upload.filename,
        "mime": upload.content_type,
        "size_bytes": size_bytes,
        "caption": caption,
        "storage_path": str(target_path),
        "stored": True,
        "source": "console",
        "sha256": store_result.get("sha256"),
    }
    saved_message = save_message(
        db=db,
        conversation_id=conversation.id,
        client_id=conversation.client_id,
        role="manager",
        content=content,
        message_metadata={"media": media_meta, "source": "console"},
    )

    record_audit_event(
        db,
        actor=agent,
        event_type="message_sent",
        entity_type="conversation",
        entity_id=conversation.id,
        payload={
            "content_length": len(content),
            "source": "web_console",
            "media_type": media_type,
            "media_size": size_bytes,
        },
        branch_id=conversation.branch_id,
    )

    relative_path = str(target_path.relative_to(MEDIA_STORAGE_BASE_DIR))
    signed_url = build_signed_media_url(relative_path)
    if not signed_url:
        _update_media_metadata(saved_message, {"storage_error": "signed_url_missing"})
        db.commit()
        raise ConsoleAPIError(500, "MEDIA_SIGNING_FAILED", "Signed media URL unavailable")

    _update_media_metadata(
        saved_message,
        {
            "public_url": signed_url,
            "expires_at": _extract_signed_url_expires_at(signed_url),
        },
    )

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
        _update_media_metadata(saved_message, {"delivery_error": "user_jid_not_found"})
        db.commit()
        return saved_message, "failed", "user_jid_not_found"

    instance_id = get_instance_id(
        db,
        conversation.client_id,
        branch_id=conversation.branch_id,
        remote_jid=remote_jid,
    )
    if not instance_id:
        _update_media_metadata(saved_message, {"delivery_error": "instance_id_not_found"})
        db.commit()
        return saved_message, "failed", "instance_id_not_found"

    use_outbox_send = _is_env_enabled(os.environ.get("OUTBOX_WORKER_ENABLED"), default=False)
    if use_outbox_send:
        now = datetime.now(timezone.utc)
        outbox_idempotency_key = idempotency_key or build_inbound_message_id(
            None,
            remote_jid,
            int(now.timestamp()),
            caption or content,
        )
        media_meta_payload = {
            "media_type": media_type,
            "signed_url": signed_url,
            "expires_at": _extract_signed_url_expires_at(signed_url),
            "sha256": store_result.get("sha256"),
            "size_bytes": size_bytes,
            "mime_type": upload.content_type,
            "filename": upload.filename,
        }
        outbox_payload = {
            "schema_version": "outbox.v1",
            "event_type": "whatsapp.send_media",
            "idempotency_key": outbox_idempotency_key,
            "client_id": str(conversation.client_id),
            "branch_id": str(conversation.branch_id) if conversation.branch_id else None,
            "tenant_context": {
                "client_id": str(conversation.client_id),
                "branch_id": str(conversation.branch_id) if conversation.branch_id else None,
                "client_slug": client_slug,
                "instance_id": instance_id,
                "source": "console_media",
            },
            "conversation_id": str(conversation.id),
            "channel": "whatsapp",
            "created_at": now.isoformat(),
            "payload": {
                "remote_jid": remote_jid,
                "instance_id": instance_id,
                "idempotency_key": outbox_idempotency_key,
                "media_type": media_type,
                "media_url": signed_url,
                "caption": caption,
                "media_meta": media_meta_payload,
            },
        }
        enqueued = enqueue_outbox_message(
            db,
            client_id=conversation.client_id,
            conversation_id=conversation.id,
            inbound_message_id=outbox_idempotency_key,
            payload_json=outbox_payload,
            branch_id=conversation.branch_id,
        )
        _update_media_metadata(
            saved_message,
            {
                "outbox_enqueued": enqueued,
                "outbox_event_type": "whatsapp.send_media",
                "outbox_idempotency_key": outbox_idempotency_key,
            },
        )
        db.commit()
        return saved_message, "queued", None

    sent = send_whatsapp_media(
        instance_id,
        remote_jid,
        media_type=media_type,
        media_url=signed_url,
        caption=caption,
        timeout_seconds=CHATFLOW_MEDIA_TIMEOUT_SECONDS,
    )
    if sent:
        db.commit()
        return saved_message, "delivered", None

    _update_media_metadata(saved_message, {"delivery_error": "chatflow_send_failed"})
    db.commit()
    return saved_message, "failed", "chatflow_send_failed"


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

    conversation, handover, linked_agent, took_handover, error = _prepare_handover_for_manager(
        db, chat_id, message_thread_id, manager_telegram_id, manager_name
    )
    if not conversation or not handover or not linked_agent:
        return False, error or "No active conversation found for this chat", False, None

    resolved_manager_name = linked_agent.name or manager_name
    if resolved_manager_name and resolved_manager_name != "Unknown":
        handover.assigned_to_name = resolved_manager_name

    if is_simulation_context(conversation):
        if caption and caption.strip():
            handover.manager_response = caption.strip()
        return True, "Simulation: manager media recorded", took_handover, handover

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
        message_metadata={"media": media_meta, "source": "telegram"},
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

    instance_id = get_instance_id(
        db,
        conversation.client_id,
        branch_id=conversation.branch_id,
        remote_jid=remote_jid,
    )
    if not instance_id:
        return False, "Instance ID not found", took_handover, handover
    use_outbox_send = _is_env_enabled(os.environ.get("OUTBOX_WORKER_ENABLED"), default=False)
    if use_outbox_send:
        now = datetime.now(timezone.utc)
        idempotency_key = build_inbound_message_id(
            str(telegram_message_id) if telegram_message_id else None,
            remote_jid,
            int(now.timestamp()),
            caption or content,
        )
        media_meta_payload = {
            "media_type": media_type,
            "signed_url": signed_url,
            "expires_at": _extract_signed_url_expires_at(signed_url),
            "sha256": sha256,
            "size_bytes": file_size or download_result.get("size_bytes"),
            "mime_type": mime_type,
            "filename": file_name,
        }
        outbox_payload = {
            "schema_version": "outbox.v1",
            "event_type": "whatsapp.send_media",
            "idempotency_key": idempotency_key,
            "client_id": str(conversation.client_id),
            "branch_id": str(conversation.branch_id) if conversation.branch_id else None,
            "tenant_context": {
                "client_id": str(conversation.client_id),
                "branch_id": str(conversation.branch_id) if conversation.branch_id else None,
                "client_slug": client_slug,
                "instance_id": instance_id,
                "source": "manager_media",
            },
            "conversation_id": str(conversation.id),
            "channel": "whatsapp",
            "created_at": now.isoformat(),
            "payload": {
                "remote_jid": remote_jid,
                "instance_id": instance_id,
                "idempotency_key": idempotency_key,
                "media_type": media_type,
                "media_url": signed_url,
                "caption": caption,
                "media_meta": media_meta_payload,
            },
        }
        enqueued = enqueue_outbox_message(
            db,
            client_id=conversation.client_id,
            conversation_id=conversation.id,
            inbound_message_id=idempotency_key,
            payload_json=outbox_payload,
            branch_id=conversation.branch_id,
        )
        if saved_message:
            _update_media_metadata(
                saved_message,
                {
                    "outbox_enqueued": enqueued,
                    "outbox_event_type": "whatsapp.send_media",
                    "outbox_idempotency_key": idempotency_key,
                },
            )
        if not enqueued:
            logger.info(
                "Outbox media send skipped (duplicate)",
                extra={
                    "context": {
                        "conversation_id": str(conversation.id),
                        "remote_jid": remote_jid,
                        "idempotency_key": idempotency_key,
                    }
                },
            )
        return True, f"Media queued for client (conversation {conversation.id})", took_handover, handover

    sent = send_whatsapp_media(
        instance_id,
        remote_jid,
        media_type=media_type,
        media_url=signed_url,
        caption=caption,
        timeout_seconds=CHATFLOW_MEDIA_TIMEOUT_SECONDS,
    )

    if sent:
        return True, f"Media forwarded to client (conversation {conversation.id})", took_handover, handover
    return False, "Failed to send media to WhatsApp", took_handover, handover
