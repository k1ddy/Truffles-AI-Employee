from __future__ import annotations

from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Branch, ClientSettings, Conversation, Handover, Message, User
from app.services.telegram_service import TelegramService

logger = get_logger("escalation_service")


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


def _build_handover_meta(
    conversation: Conversation,
    message: Message | None,
    user: User | None,
    *,
    recent_messages: list[Message] | None = None,
) -> dict | None:
    from app.services.handover_owner_service import _build_handover_meta as owner_build_handover_meta

    return owner_build_handover_meta(
        conversation,
        message,
        user,
        recent_messages=recent_messages,
    )


def _get_latest_user_message(db: Session, conversation_id: UUID) -> Message | None:
    from app.services.handover_owner_service import _get_latest_user_message as owner_get_latest_user_message

    return owner_get_latest_user_message(db, conversation_id)


def _get_recent_user_messages(
    db: Session,
    conversation_id: UUID,
    *,
    limit: int = 12,
) -> list[Message]:
    from app.services.handover_owner_service import _get_recent_user_messages as owner_get_recent_user_messages

    return owner_get_recent_user_messages(db, conversation_id, limit=limit)


def _build_simulated_topic_id(conversation: Conversation, user: User | None) -> int:
    from app.services.handover_owner_service import _build_simulated_topic_id as owner_build_simulated_topic_id

    return owner_build_simulated_topic_id(conversation, user)


def create_handover(
    db: Session,
    conversation: Conversation,
    user: User,
    trigger_type: str,
    trigger_value: Optional[str] = None,
    user_message: Optional[str] = None,
) -> Handover:
    from app.services.handover_owner_service import create_handover as owner_create_handover

    return owner_create_handover(
        db=db,
        conversation=conversation,
        user=user,
        trigger_type=trigger_type,
        trigger_value=trigger_value,
        user_message=user_message,
    )


def get_active_handover(db: Session, conversation_id: UUID) -> Optional[Handover]:
    from app.services.handover_owner_service import get_active_handover as owner_get_active_handover

    return owner_get_active_handover(db, conversation_id)


def get_or_create_topic(
    db: Session,
    telegram: TelegramService | None,
    chat_id: str,
    conversation: Conversation,
    user: User,
) -> Optional[int]:
    from app.services.handover_owner_service import get_or_create_topic as owner_get_or_create_topic

    return owner_get_or_create_topic(db, telegram, chat_id, conversation, user)


def _refresh_handover_media_contract(
    db: Session,
    *,
    handover: Handover,
    conversation: Conversation,
    user: User | None,
) -> None:
    from app.services.handover_owner_service import (
        _refresh_handover_media_contract as owner_refresh_handover_media_contract,
    )

    return owner_refresh_handover_media_contract(
        db,
        handover=handover,
        conversation=conversation,
        user=user,
    )


def _download_remote_media_to_tempfile(
    media_url: str,
    *,
    media_type: str,
) -> tuple[str | None, str | None]:
    from app.services.handover_owner_service import (
        _download_remote_media_to_tempfile as owner_download_remote_media_to_tempfile,
    )

    return owner_download_remote_media_to_tempfile(media_url, media_type=media_type)


def send_telegram_notification(
    db: Session,
    handover: Handover,
    conversation: Conversation,
    user: User,
    message: str,
    routing_meta: dict | None = None,
) -> bool:
    from app.services.handover_owner_service import (
        send_telegram_notification as owner_send_telegram_notification,
    )

    return owner_send_telegram_notification(
        db=db,
        handover=handover,
        conversation=conversation,
        user=user,
        message=message,
        routing_meta=routing_meta,
    )


def escalate_conversation(
    db: Session,
    conversation: Conversation,
    user: User,
    trigger_type: str,
    trigger_value: Optional[str] = None,
    user_message: Optional[str] = None,
) -> Tuple[Handover, bool]:
    from app.services.handover_owner_service import materialize_handover

    handoff_result = materialize_handover(
        db=db,
        conversation=conversation,
        user=user,
        message=user_message or "",
        source="escalation_service",
        intent=trigger_value,
        trigger_type=trigger_type,
        trigger_value=trigger_value,
        allow_create=True,
    )
    if not handoff_result.ok or handoff_result.handover is None:
        raise RuntimeError(handoff_result.error or "handover_materialization_failed")
    return handoff_result.handover, handoff_result.telegram_sent
