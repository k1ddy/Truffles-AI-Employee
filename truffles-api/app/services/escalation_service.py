import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Branch, ClientSettings, Conversation, Handover, Message, User
from app.services.alert_service import alert_error
from app.services.state_machine import ConversationState
from app.services.telegram_service import TelegramService, build_handover_buttons, format_handover_message

logger = get_logger("escalation_service")

SIMULATION_CONTEXT_KEY = "simulation"
HANDOVER_MEDIA_LOOKBACK_LIMIT = 12
HANDOVER_MEDIA_HISTORY_WINDOW = timedelta(minutes=30)
HANDOVER_MEDIA_DOWNLOAD_TIMEOUT_SECONDS = max(
    float(os.environ.get("HANDOVER_MEDIA_DOWNLOAD_TIMEOUT_SECONDS", "12.0")),
    1.0,
)
HANDOVER_MEDIA_MAX_DOWNLOAD_BYTES = max(
    int(os.environ.get("HANDOVER_MEDIA_MAX_DOWNLOAD_BYTES", str(20 * 1024 * 1024))),
    1 * 1024 * 1024,
)
MEDIA_STORAGE_BASE_DIR = Path(os.environ.get("MEDIA_STORAGE_DIR", "/home/zhan/truffles-media"))


def _normalize_slot_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_media_ref(
    raw_media: dict | None,
    *,
    source: str,
    inbound_message_id: str | None = None,
) -> dict | None:
    if not isinstance(raw_media, dict):
        return None

    ref: dict[str, object] = {"source": source}
    for key in (
        "media_type",
        "raw_type",
        "mime",
        "url",
        "file_name",
        "caption",
        "storage_path",
        "public_url",
        "expires_at",
        "sha256",
    ):
        value = _normalize_slot_value(raw_media.get(key))
        if value:
            ref[key] = value

    if "media_type" not in ref:
        media_type = _normalize_slot_value(raw_media.get("type"))
        if media_type:
            ref["media_type"] = media_type

    size_bytes = raw_media.get("size_bytes")
    if isinstance(size_bytes, int) and size_bytes >= 0:
        ref["size_bytes"] = size_bytes
    duration_seconds = raw_media.get("duration_seconds")
    if isinstance(duration_seconds, int) and duration_seconds >= 0:
        ref["duration_seconds"] = duration_seconds
    if isinstance(raw_media.get("ptt"), bool):
        ref["ptt"] = raw_media["ptt"]
    if isinstance(raw_media.get("forwarded_to_telegram"), bool):
        ref["forwarded_to_telegram"] = raw_media["forwarded_to_telegram"]
    if inbound_message_id:
        ref["inbound_message_id"] = inbound_message_id

    if not any(ref.get(locator_key) for locator_key in ("storage_path", "public_url", "url")):
        return None
    return ref


def _media_ref_fingerprint(ref: dict) -> tuple[str | None, ...]:
    return (
        ref.get("sha256"),
        ref.get("storage_path"),
        ref.get("public_url"),
        ref.get("url"),
        ref.get("media_type"),
        ref.get("inbound_message_id"),
    )


def _extract_handover_media_refs(
    conversation: Conversation,
    message: Message | None,
    *,
    recent_messages: list[Message] | None = None,
) -> tuple[list[dict], bool]:
    refs: list[dict] = []
    required = False
    reference_time = datetime.now(timezone.utc)
    trigger_created_at = getattr(message, "created_at", None) if message is not None else None
    if isinstance(trigger_created_at, datetime):
        if trigger_created_at.tzinfo is None:
            trigger_created_at = trigger_created_at.replace(tzinfo=timezone.utc)
        reference_time = trigger_created_at

    message_meta = message.message_metadata if message and isinstance(message.message_metadata, dict) else {}
    message_media = message_meta.get("media") if isinstance(message_meta, dict) else None
    if isinstance(message_media, dict):
        required = True
        inbound_message_id = _normalize_slot_value(getattr(message, "message_id", None))
        media_ref = _normalize_media_ref(
            message_media,
            source="message_metadata",
            inbound_message_id=inbound_message_id,
        )
        if media_ref:
            refs.append(media_ref)

    context = conversation.context if isinstance(conversation.context, dict) else {}
    pending_style = context.get("style_reference_pending") if isinstance(context, dict) else None
    if isinstance(pending_style, dict):
        pending_media = pending_style.get("media")
        if isinstance(pending_media, dict):
            required = True
            pending_payload = dict(pending_media)
            for key in ("storage_path", "public_url", "sha256"):
                if key in pending_style and key not in pending_payload:
                    pending_payload[key] = pending_style.get(key)
            if "expires_at" not in pending_payload:
                media_expires_at = (
                    pending_style.get("public_url_expires_at")
                    or pending_style.get("media_expires_at")
                    or pending_style.get("expires_at")
                )
                if media_expires_at:
                    pending_payload["expires_at"] = media_expires_at
            media_ref = _normalize_media_ref(
                pending_payload,
                source="style_reference_pending",
            )
            if media_ref:
                refs.append(media_ref)

    for recent_message in recent_messages or []:
        if recent_message is None:
            continue
        created_at = getattr(recent_message, "created_at", None)
        if isinstance(created_at, datetime):
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if reference_time - created_at > HANDOVER_MEDIA_HISTORY_WINDOW:
                continue
        if message is not None and getattr(recent_message, "id", None) == getattr(message, "id", None):
            continue
        recent_meta = (
            recent_message.message_metadata
            if isinstance(recent_message.message_metadata, dict)
            else {}
        )
        recent_media = recent_meta.get("media") if isinstance(recent_meta, dict) else None
        if not isinstance(recent_media, dict):
            continue
        required = True
        recent_inbound_id = _normalize_slot_value(getattr(recent_message, "message_id", None))
        media_ref = _normalize_media_ref(
            recent_media,
            source="recent_message_history",
            inbound_message_id=recent_inbound_id,
        )
        if media_ref:
            refs.append(media_ref)
    deduped: list[dict] = []
    seen: set[tuple[str | None, ...]] = set()
    for ref in refs:
        fingerprint = _media_ref_fingerprint(ref)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        deduped.append(ref)

    return deduped, required


def _extract_decision_meta(message: Message | None) -> dict:
    if not message or not isinstance(message.message_metadata, dict):
        return {}
    decision_meta = message.message_metadata.get("decision_meta")
    return decision_meta if isinstance(decision_meta, dict) else {}


def _build_handover_meta(
    conversation: Conversation,
    message: Message | None,
    user: User | None,
    *,
    recent_messages: list[Message] | None = None,
) -> dict | None:
    decision_meta = _extract_decision_meta(message)
    meta: dict = {}
    intent = decision_meta.get("intent")
    if isinstance(intent, str) and intent.strip():
        meta["intent"] = intent.strip()
    info_sections = decision_meta.get("info_sections")
    if isinstance(info_sections, list):
        cleaned_sections = [item.strip() for item in info_sections if isinstance(item, str) and item.strip()]
        if cleaned_sections:
            meta["info_sections"] = cleaned_sections

    slots: dict[str, str] = {}
    raw_slots = decision_meta.get("slots")
    if isinstance(raw_slots, dict):
        for key in ("service", "datetime", "name", "phone"):
            value = _normalize_slot_value(raw_slots.get(key))
            if value:
                slots[key] = value

    context = conversation.context if isinstance(conversation.context, dict) else {}
    booking = context.get("booking") if isinstance(context, dict) else None
    if isinstance(booking, dict):
        for key in ("service", "datetime", "name", "phone"):
            if key in slots:
                continue
            value = _normalize_slot_value(booking.get(key))
            if value:
                slots[key] = value

    if user:
        if "name" not in slots:
            name = _normalize_slot_value(getattr(user, "name", None))
            if name:
                slots["name"] = name
        if "phone" not in slots:
            phone = _normalize_slot_value(getattr(user, "phone", None))
            if phone:
                slots["phone"] = phone

    if slots:
        meta["slots"] = slots

    media_refs, media_required = _extract_handover_media_refs(
        conversation,
        message,
        recent_messages=recent_messages,
    )
    if media_refs:
        meta["media_refs"] = media_refs
    if media_required or media_refs:
        contract = {
            "required": bool(media_required),
            "bound": bool(media_refs),
            "media_refs_count": len(media_refs),
        }
        sources = sorted({item.get("source") for item in media_refs if isinstance(item.get("source"), str)})
        if sources:
            contract["sources"] = sources
        if media_required and not media_refs:
            contract["reason"] = "media_ref_missing"
        meta["media_handoff_contract"] = contract

    return meta or None


def _get_latest_user_message(db: Session, conversation_id: UUID) -> Message | None:
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id, Message.role == "user")
        .order_by(Message.created_at.desc())
        .first()
    )


def _get_recent_user_messages(
    db: Session,
    conversation_id: UUID,
    *,
    limit: int = HANDOVER_MEDIA_LOOKBACK_LIMIT,
) -> list[Message]:
    safe_limit = max(1, int(limit or HANDOVER_MEDIA_LOOKBACK_LIMIT))
    try:
        rows = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id, Message.role == "user")
            .order_by(Message.created_at.desc())
            .limit(safe_limit)
            .all()
        )
    except Exception:
        return []
    if isinstance(rows, list):
        return rows
    if isinstance(rows, tuple):
        return list(rows)
    return []


def _is_simulation_context(conversation: Conversation | None) -> bool:
    if not conversation or not isinstance(conversation.context, dict):
        return False
    sim_context = conversation.context.get(SIMULATION_CONTEXT_KEY)
    if isinstance(sim_context, dict):
        if sim_context.get("mode") is not None:
            return bool(sim_context.get("mode"))
        if sim_context.get("id"):
            return True
    if conversation.context.get("simulation_mode") is True:
        return True
    if conversation.context.get("simulation_id"):
        return True
    return False


def _build_simulated_topic_id(conversation: Conversation, user: User | None) -> int:
    seed = f"sim:{conversation.id}:{getattr(user, 'id', '')}"
    digest = uuid.uuid5(uuid.NAMESPACE_DNS, seed).int
    return 1000 + (digest % 2147480000)


def get_telegram_credentials(db: Session, client_id: UUID) -> Tuple[Optional[str], Optional[str]]:
    """Get Telegram bot_token and chat_id for client."""
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client_id).first()

    if settings and settings.telegram_bot_token and settings.telegram_chat_id:
        return settings.telegram_bot_token, settings.telegram_chat_id

    return None, None


def resolve_telegram_routing(
    db: Session,
    *,
    conversation: Conversation,
    client_id: UUID,
) -> dict:
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client_id).first()
    manager_scope = getattr(settings, "manager_scope", None) or "branch"
    bot_token = getattr(settings, "telegram_bot_token", None)
    chat_id = getattr(settings, "telegram_chat_id", None)
    routing_source = "client"
    branch_chat_id = None
    branch_id = conversation.branch_id if conversation else None

    if manager_scope == "branch" and branch_id:
        branch = (
            db.query(Branch)
            .filter(Branch.id == branch_id, Branch.client_id == client_id)
            .first()
        )
        if branch and branch.telegram_chat_id:
            branch_chat_id = branch.telegram_chat_id
            chat_id = branch_chat_id
            routing_source = "branch"
        else:
            routing_source = "branch_fallback"

    return {
        "bot_token": bot_token,
        "chat_id": chat_id,
        "routing_source": routing_source,
        "manager_scope": manager_scope,
        "branch_id": str(branch_id) if branch_id else None,
        "branch_chat_id": branch_chat_id,
    }


def create_handover(
    db: Session,
    conversation: Conversation,
    user: User,
    trigger_type: str,
    trigger_value: Optional[str] = None,
    user_message: Optional[str] = None,
) -> Handover:
    """Create handover record in database."""
    now = datetime.now(timezone.utc)
    trigger_message = _get_latest_user_message(db, conversation.id)
    recent_messages = _get_recent_user_messages(db, conversation.id)
    handover_meta = _build_handover_meta(
        conversation,
        trigger_message,
        user,
        recent_messages=recent_messages,
    )

    handover = Handover(
        conversation_id=conversation.id,
        client_id=conversation.client_id,
        trigger_type=trigger_type,
        trigger_value=trigger_value,
        status="pending",
        user_message=user_message,
        created_at=now,
        adapter_type="telegram",
        channel="telegram",
        channel_ref=user.remote_jid if user else None,
        trigger_message_id=trigger_message.id if trigger_message else None,
        meta=handover_meta,
    )
    db.add(handover)
    db.flush()  # Get ID before commit

    return handover


def get_active_handover(db: Session, conversation_id: UUID) -> Optional[Handover]:
    """Get latest pending/active handover for conversation."""
    return (
        db.query(Handover)
        .filter(
            Handover.conversation_id == conversation_id,
            Handover.status.in_(["pending", "active"]),
        )
        .order_by(Handover.created_at.desc())
        .first()
    )


def get_or_create_topic(
    db: Session,
    telegram: TelegramService | None,
    chat_id: str,
    conversation: Conversation,
    user: User,
) -> Optional[int]:
    """Get existing topic or create new one. Returns topic_id."""
    if not user:
        logger.warning(f"Cannot resolve topic: user missing for conversation {conversation.id}")
        return None

    # Check if topic already exists (canonical: user.telegram_topic_id)
    topic_id = user.telegram_topic_id or conversation.telegram_topic_id
    if topic_id:
        if not user.telegram_topic_id:
            user.telegram_topic_id = topic_id
        if conversation.telegram_topic_id != topic_id:
            conversation.telegram_topic_id = topic_id
        db.flush()
        return topic_id

    if _is_simulation_context(conversation):
        topic_id = _build_simulated_topic_id(conversation, user)
        user.telegram_topic_id = topic_id
        conversation.telegram_topic_id = topic_id
        db.flush()
        logger.info("Simulation topic assigned %s for conversation %s", topic_id, conversation.id)
        return topic_id

    # Create topic name: "77015705555 Жанбол [Truffles]"
    phone = user.phone or "Unknown"
    name = user.name or "Клиент"
    topic_name = f"{phone} {name}"

    # Create topic
    topic_id = telegram.create_forum_topic(chat_id, topic_name)

    if topic_id:
        # Save to user (canonical) + conversation copy
        user.telegram_topic_id = topic_id
        conversation.telegram_topic_id = topic_id
        db.flush()
        logger.info(f"Created topic {topic_id} for conversation {conversation.id}")
    else:
        logger.warning(f"Failed to create topic for conversation {conversation.id}")

    return topic_id


def _extract_media_contract_state(handover: Handover) -> tuple[list[dict], bool]:
    meta = handover.meta if isinstance(handover.meta, dict) else {}
    media_refs = meta.get("media_refs") if isinstance(meta.get("media_refs"), list) else []
    media_refs = [item for item in media_refs if isinstance(item, dict)]
    contract = meta.get("media_handoff_contract") if isinstance(meta.get("media_handoff_contract"), dict) else {}
    required = bool(contract.get("required"))
    if not required and media_refs:
        required = bool(contract.get("bound")) or False
    return media_refs, required


def _apply_media_delivery_meta(
    handover: Handover,
    *,
    status: str,
    media_refs_count: int,
    required: bool,
    sent_count: int = 0,
    failed: list[dict] | None = None,
    reason: str | None = None,
) -> None:
    meta = dict(handover.meta or {})
    delivery = dict(meta.get("media_handoff_delivery") or {})
    telegram_payload = {
        "status": status,
        "required": bool(required),
        "media_refs_count": int(media_refs_count),
        "sent_count": int(sent_count),
        "failed_count": len(failed or []),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if reason:
        telegram_payload["reason"] = reason
    if failed:
        telegram_payload["failed"] = failed[:5]
    delivery["telegram"] = telegram_payload
    meta["media_handoff_delivery"] = delivery
    handover.meta = meta


def _refresh_handover_media_contract(
    db: Session,
    *,
    handover: Handover,
    conversation: Conversation,
    user: User | None,
) -> None:
    existing_refs, required = _extract_media_contract_state(handover)
    if existing_refs:
        return

    trigger_message = _get_latest_user_message(db, conversation.id)
    recent_messages = _get_recent_user_messages(db, conversation.id)
    refreshed_meta = _build_handover_meta(
        conversation,
        trigger_message,
        user,
        recent_messages=recent_messages,
    )
    if not isinstance(refreshed_meta, dict):
        return

    refreshed_refs = refreshed_meta.get("media_refs")
    refreshed_contract = refreshed_meta.get("media_handoff_contract")
    if not isinstance(refreshed_refs, list) and not isinstance(refreshed_contract, dict):
        return

    merged = dict(handover.meta or {})
    if isinstance(refreshed_refs, list):
        merged["media_refs"] = [item for item in refreshed_refs if isinstance(item, dict)]
    if isinstance(refreshed_contract, dict):
        merged["media_handoff_contract"] = refreshed_contract
    handover.meta = merged


def _resolve_handover_media_locator(raw_value: str) -> str:
    locator = (raw_value or "").strip()
    if not locator:
        return locator
    if locator.startswith("http://") or locator.startswith("https://"):
        return locator
    candidate = Path(locator)
    if candidate.is_absolute():
        return str(candidate)
    normalized = locator.lstrip("/").replace("\\", "/")
    resolved = MEDIA_STORAGE_BASE_DIR / normalized
    if resolved.exists():
        return str(resolved)
    return locator


def _is_telegram_url_fetch_failure(description: str | None) -> bool:
    text = (description or "").strip().casefold()
    if not text:
        return False
    return "failed to get http url content" in text or "wrong file identifier/http url specified" in text


def _download_remote_media_to_tempfile(
    media_url: str,
    *,
    media_type: str,
) -> tuple[str | None, str | None]:
    if not media_url.startswith(("http://", "https://")):
        return None, "unsupported_media_locator"
    suffix_map = {
        "photo": ".jpg",
        "image": ".jpg",
        "voice": ".ogg",
        "audio": ".mp3",
    }
    suffix = suffix_map.get(media_type, ".bin")
    fd, tmp_path = tempfile.mkstemp(prefix="handover-media-", suffix=suffix)
    os.close(fd)
    target = Path(tmp_path)
    size_bytes = 0
    try:
        with httpx.Client(timeout=HANDOVER_MEDIA_DOWNLOAD_TIMEOUT_SECONDS, follow_redirects=True) as client:
            with client.stream("GET", media_url) as response:
                response.raise_for_status()
                with target.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        if not chunk:
                            continue
                        size_bytes += len(chunk)
                        if size_bytes > HANDOVER_MEDIA_MAX_DOWNLOAD_BYTES:
                            raise ValueError("media_too_large")
                        handle.write(chunk)
    except Exception as exc:
        if target.exists():
            target.unlink()
        return None, str(exc)
    return str(target), None


def _send_handover_media_item(
    telegram: TelegramService,
    *,
    chat_id: str,
    topic_id: int,
    reply_to_message_id: int,
    locator: str,
    media_type: str,
    caption: str,
    ptt: bool = False,
) -> dict:
    if media_type in {"photo", "image"}:
        return telegram.send_photo(
            chat_id=chat_id,
            photo=locator,
            caption=caption,
            message_thread_id=topic_id,
            reply_to_message_id=reply_to_message_id,
        )
    if media_type in {"voice"} or ptt:
        return telegram.send_voice(
            chat_id=chat_id,
            voice=locator,
            caption=caption,
            message_thread_id=topic_id,
            reply_to_message_id=reply_to_message_id,
        )
    if media_type in {"audio"}:
        return telegram.send_audio(
            chat_id=chat_id,
            audio=locator,
            caption=caption,
            message_thread_id=topic_id,
            reply_to_message_id=reply_to_message_id,
        )
    return telegram.send_document(
        chat_id=chat_id,
        document=locator,
        caption=caption,
        message_thread_id=topic_id,
        reply_to_message_id=reply_to_message_id,
    )


def _send_handover_media_to_topic(
    telegram: TelegramService,
    *,
    chat_id: str,
    topic_id: int,
    reply_to_message_id: int,
    media_refs: list[dict],
) -> tuple[int, list[dict]]:
    sent_count = 0
    failed: list[dict] = []

    for index, ref in enumerate(media_refs, start=1):
        media_locator_raw = (
            _normalize_slot_value(ref.get("public_url"))
            or _normalize_slot_value(ref.get("url"))
            or _normalize_slot_value(ref.get("storage_path"))
        )
        if not media_locator_raw:
            failed.append(
                {
                    "index": index,
                    "reason": "media_url_missing",
                }
            )
            continue

        media_locator = _resolve_handover_media_locator(media_locator_raw)
        media_type = (_normalize_slot_value(ref.get("media_type")) or "").lower()
        caption = _normalize_slot_value(ref.get("caption")) or f"Референс клиента #{index}"
        ptt = bool(ref.get("ptt"))

        try:
            result = _send_handover_media_item(
                telegram,
                chat_id=chat_id,
                topic_id=topic_id,
                reply_to_message_id=reply_to_message_id,
                locator=media_locator,
                media_type=media_type,
                caption=caption,
                ptt=ptt,
            )
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}

        fallback_error = None
        fallback_attempted = False
        description = _normalize_slot_value(result.get("description")) or _normalize_slot_value(
            result.get("error")
        )
        if (
            not result.get("ok")
            and media_locator_raw.startswith(("http://", "https://"))
            and _is_telegram_url_fetch_failure(description)
        ):
            fallback_attempted = True
            local_path, fallback_error = _download_remote_media_to_tempfile(
                media_locator_raw,
                media_type=media_type,
            )
            if local_path:
                try:
                    result = _send_handover_media_item(
                        telegram,
                        chat_id=chat_id,
                        topic_id=topic_id,
                        reply_to_message_id=reply_to_message_id,
                        locator=local_path,
                        media_type=media_type,
                        caption=caption,
                        ptt=ptt,
                    )
                except Exception as exc:
                    result = {"ok": False, "error": str(exc)}
                finally:
                    local_file = Path(local_path)
                    if local_file.exists():
                        local_file.unlink()
            description = _normalize_slot_value(result.get("description")) or _normalize_slot_value(
                result.get("error")
            )

        if result.get("ok"):
            sent_count += 1
            continue
        failure_payload = {
            "index": index,
            "reason": "telegram_media_send_failed",
            "description": description,
        }
        if fallback_attempted:
            failure_payload["fallback_attempted"] = True
        if fallback_error:
            failure_payload["fallback_error"] = fallback_error
        failed.append(failure_payload)

    return sent_count, failed


def send_telegram_notification(
    db: Session,
    handover: Handover,
    conversation: Conversation,
    user: User,
    message: str,
    routing_meta: dict | None = None,
) -> bool:
    """Send handover notification to Telegram topic with buttons and pin."""
    _refresh_handover_media_contract(
        db,
        handover=handover,
        conversation=conversation,
        user=user,
    )
    media_refs, media_required = _extract_media_contract_state(handover)
    if media_required and not media_refs:
        _apply_media_delivery_meta(
            handover,
            status="failed",
            media_refs_count=0,
            required=True,
            reason="media_refs_missing",
        )
        db.flush()
        logger.error(
            "Media handoff contract violation: required media refs missing for handover %s",
            handover.id,
        )
        alert_error(
            "Media handoff contract violation",
            {"handover_id": str(handover.id), "reason": "media_refs_missing"},
        )
        return False

    if _is_simulation_context(conversation):
        topic_id = get_or_create_topic(db, None, "", conversation, user)
        handover.notified_at = datetime.now(timezone.utc)
        if topic_id and not handover.telegram_message_id:
            handover.telegram_message_id = -abs(int(topic_id))
        _apply_media_delivery_meta(
            handover,
            status="simulated",
            media_refs_count=len(media_refs),
            required=media_required,
            sent_count=len(media_refs),
        )
        db.flush()
        logger.info(
            "Simulation mode: skipping telegram notification for handover %s",
            handover.id,
        )
        return True

    routing_meta = routing_meta or resolve_telegram_routing(
        db,
        conversation=conversation,
        client_id=handover.client_id,
    )
    bot_token = routing_meta.get("bot_token")
    chat_id = routing_meta.get("chat_id")

    if not bot_token or not chat_id:
        logger.warning(f"No Telegram credentials for client {handover.client_id}")
        return False

    telegram = TelegramService(bot_token)

    # 1. Get or create topic
    topic_id = get_or_create_topic(db, telegram, chat_id, conversation, user)
    if not topic_id:
        logger.warning(f"No topic_id for conversation {conversation.id}")
        return False

    # 2. Format message
    text = format_handover_message(
        user_name=user.name,
        user_phone=user.phone,
        message=message,
        trigger_type=handover.trigger_value or handover.trigger_type,
    )
    if media_refs:
        text = f"{text}\n\n<b>Медиа:</b> {len(media_refs)} файл(а) отправляю ниже."

    # 3. Build buttons
    buttons = build_handover_buttons(handover.id)

    # 4. Send message to topic
    result = telegram.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=buttons,
        message_thread_id=topic_id,
    )

    # 4.1 If topic not found - reset and create new
    if not result.get("ok"):
        error_desc = result.get("description", "")
        if "thread not found" in error_desc.lower() or "message_thread_id" in error_desc.lower():
            logger.warning(f"Topic {topic_id} not found, creating new one...")
            # Reset topic_id
            if user:
                user.telegram_topic_id = None
            conversation.telegram_topic_id = None
            db.flush()
            # Create new topic
            topic_id = get_or_create_topic(db, telegram, chat_id, conversation, user)
            if topic_id:
                # Retry send
                result = telegram.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=buttons,
                    message_thread_id=topic_id,
                )

    if result.get("ok"):
        message_id = result["result"]["message_id"]

        # 5. Save telegram_message_id
        handover.telegram_message_id = message_id
        handover.notified_at = datetime.now(timezone.utc)

        # 6. Pin message
        telegram.pin_message(chat_id, message_id)

        sent_media = 0
        media_failed: list[dict] = []
        if media_refs:
            sent_media, media_failed = _send_handover_media_to_topic(
                telegram,
                chat_id=chat_id,
                topic_id=topic_id,
                reply_to_message_id=message_id,
                media_refs=media_refs,
            )

        media_status = "sent"
        if media_failed:
            media_status = "partial" if sent_media > 0 else "failed"
        _apply_media_delivery_meta(
            handover,
            status=media_status,
            media_refs_count=len(media_refs),
            required=media_required,
            sent_count=sent_media,
            failed=media_failed,
            reason="telegram_media_send_failed" if media_failed else None,
        )
        db.flush()
        if media_required and media_failed:
            logger.error(
                "Media handoff delivery failed for handover %s: %s",
                handover.id,
                media_failed,
            )
            alert_error(
                "Media handoff delivery failed",
                {"handover_id": str(handover.id), "failed": media_failed[:3]},
            )
            return False

        logger.info(f"Sent to Telegram: topic={topic_id}, message_id={message_id}")
        return True
    else:
        _apply_media_delivery_meta(
            handover,
            status="failed",
            media_refs_count=len(media_refs),
            required=media_required,
            reason="telegram_message_send_failed",
        )
        db.flush()
        logger.error(f"Telegram send error: {result}")
        alert_error("Telegram notification failed", {"handover_id": str(handover.id), "result": str(result)})
        return False


def escalate_conversation(
    db: Session,
    conversation: Conversation,
    user: User,
    trigger_type: str,
    trigger_value: Optional[str] = None,
    user_message: Optional[str] = None,
) -> Tuple[Handover, bool]:
    """
    Full escalation flow:
    1. Create handover in DB
    2. Send Telegram notification with buttons
    3. Pin message

    Returns: (handover, telegram_sent)
    """
    from app.services.state_service import transition_state

    existing_handover = get_active_handover(db, conversation.id)
    if existing_handover:
        if conversation.state == ConversationState.BOT_ACTIVE.value:
            target_state = (
                ConversationState.MANAGER_ACTIVE
                if existing_handover.status == "active"
                else ConversationState.PENDING
            )
            transition_state(
                conversation,
                target_state,
                allow_same=True,
                enforce=False,
                handover=existing_handover,
            )
            conversation.escalated_at = datetime.now(timezone.utc)
        telegram_sent = send_telegram_notification(
            db=db,
            handover=existing_handover,
            conversation=conversation,
            user=user,
            message=user_message or "",
        )
        return existing_handover, telegram_sent

    # 1. Create handover
    handover = create_handover(
        db=db,
        conversation=conversation,
        user=user,
        trigger_type=trigger_type,
        trigger_value=trigger_value,
        user_message=user_message,
    )

    # 2. Send to Telegram (with topic)
    telegram_sent = send_telegram_notification(
        db=db,
        handover=handover,
        conversation=conversation,
        user=user,
        message=user_message or "",
    )

    return handover, telegram_sent
