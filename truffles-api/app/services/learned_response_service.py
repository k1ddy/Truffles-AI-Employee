from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Agent, ClientSettings, Handover, LearnedResponse
from app.services.escalation_service import resolve_telegram_routing
from app.services.knowledge_registry_service import get_current_published, upsert_draft
from app.services.knowledge_validation import strip_compiled_artifacts
from app.services.learning_service import add_learned_response_to_knowledge, is_owner_response
from app.services.telegram_service import (
    TelegramService,
    build_learned_response_buttons,
    format_learned_response_message,
)

logger = get_logger("learned_response_service")

MIN_QUESTION_LENGTH = 5
MIN_ANSWER_LENGTH = 5
LOW_VALUE_TEXTS = {
    "ок",
    "окей",
    "ok",
    "okay",
    "ага",
    "угу",
    "да",
    "нет",
    "неа",
    "спасибо",
    "спасибо большое",
    "благодарю",
    "понял",
    "поняла",
    "понятно",
    "ясно",
    "хорошо",
    "принято",
}
DEFAULT_AUTO_APPROVE_ROLES = {"owner", "admin"}


def _normalize_text(text: str) -> str:
    cleaned = (text or "").strip().casefold()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _is_low_value_text(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return True
    if normalized in LOW_VALUE_TEXTS:
        return True
    if not re.search(r"[a-zа-я]", normalized):
        return True
    return False


def _parse_auto_approve_roles(value: Optional[str]) -> set[str]:
    if not value:
        return set(DEFAULT_AUTO_APPROVE_ROLES)
    roles = {item.strip().lower() for item in value.split(",") if item.strip()}
    return roles or set(DEFAULT_AUTO_APPROVE_ROLES)


def resolve_auto_approve(
    db: Session,
    *,
    handover: Handover,
    agent: Optional[Agent],
    manager_telegram_id: Optional[int],
    manager_username: Optional[str],
) -> tuple[bool, Optional[str]]:
    settings = (
        db.query(ClientSettings)
        .filter(ClientSettings.client_id == handover.client_id)
        .first()
    )
    auto_roles = _parse_auto_approve_roles(
        settings.auto_approve_roles if settings else None
    )

    owner_match = False
    if manager_telegram_id or manager_username:
        owner_match = is_owner_response(
            db,
            handover.client_id,
            manager_telegram_id or 0,
            manager_username,
        )

    effective_role = "owner" if owner_match else (agent.role if agent else None)
    if effective_role == "owner":
        return True, "owner"
    if effective_role and effective_role in auto_roles:
        if effective_role == "admin":
            if not agent or not agent.branch_id or not handover.branch_id:
                return False, effective_role
            if agent.branch_id != handover.branch_id:
                return False, effective_role
        return True, effective_role
    return False, effective_role


def is_agent_allowed_to_approve(
    db: Session,
    *,
    learned_response: LearnedResponse,
    agent: Optional[Agent],
) -> bool:
    if not agent:
        return False
    if agent.role == "owner":
        return True

    settings = (
        db.query(ClientSettings)
        .filter(ClientSettings.client_id == learned_response.client_id)
        .first()
    )
    auto_roles = _parse_auto_approve_roles(
        settings.auto_approve_roles if settings else None
    )
    if agent.role not in auto_roles:
        return False
    if agent.role == "admin":
        if not agent.branch_id or not learned_response.branch_id:
            return False
        return agent.branch_id == learned_response.branch_id
    return True


def notify_learned_response_pending(
    db: Session,
    *,
    learned_response: LearnedResponse,
    handover: Handover,
    conversation,
) -> bool:
    routing = resolve_telegram_routing(
        db,
        conversation=conversation,
        client_id=handover.client_id,
    )
    bot_token = routing.get("bot_token")
    chat_id = routing.get("chat_id")
    if not bot_token or not chat_id:
        logger.warning(
            "Learned response moderation skipped: telegram routing missing",
            extra={
                "context": {
                    "learned_response_id": str(learned_response.id),
                    "client_id": str(handover.client_id),
                    "routing": routing,
                }
            },
        )
        return False

    telegram = TelegramService(bot_token)
    message_thread_id = getattr(conversation, "telegram_topic_id", None)
    text = format_learned_response_message(
        question=learned_response.question_text,
        answer=learned_response.response_text,
        source_name=learned_response.source_name,
    )
    reply_markup = build_learned_response_buttons(learned_response.id)
    response = telegram.send_message(
        chat_id=str(chat_id),
        text=text,
        reply_markup=reply_markup,
        message_thread_id=message_thread_id,
    )
    if not response.get("ok"):
        logger.warning(
            "Learned response moderation message failed",
            extra={
                "context": {
                    "learned_response_id": str(learned_response.id),
                    "chat_id": str(chat_id),
                    "error": response.get("error"),
                }
            },
        )
        return False
    return True


def create_learned_response(
    db: Session,
    *,
    handover: Handover,
    source_channel: str = "telegram",
    source_name: Optional[str] = None,
    source_role: Optional[str] = None,
    agent_id: Optional[UUID] = None,
    auto_approve: bool = False,
) -> LearnedResponse | None:
    if not handover.user_message or not handover.manager_response:
        return None
    question = handover.user_message.strip()
    answer = handover.manager_response.strip()
    if len(question) < MIN_QUESTION_LENGTH or len(answer) < MIN_ANSWER_LENGTH:
        return None
    if _is_low_value_text(question) or _is_low_value_text(answer):
        return None

    now = datetime.now(timezone.utc)
    learned = LearnedResponse(
        client_id=handover.client_id,
        branch_id=handover.branch_id,
        handover_id=handover.id,
        question_text=question,
        question_normalized=_normalize_text(question),
        response_text=answer,
        source="manager",
        source_name=source_name,
        source_role=source_role,
        source_channel=source_channel,
        agent_id=agent_id,
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db.add(learned)
    db.flush()
    if auto_approve:
        approve_learned_response(
            db,
            learned_response=learned,
            actor_id=agent_id,
        )
    return learned


def approve_learned_response(
    db: Session,
    *,
    learned_response: LearnedResponse,
    actor_id: Optional[UUID],
) -> bool:
    now = datetime.now(timezone.utc)
    learned_response.status = "approved"
    learned_response.approved_by = actor_id
    learned_response.approved_at = now
    learned_response.rejected_at = None

    applied = apply_learned_response_to_draft(
        db,
        learned_response=learned_response,
        actor_id=actor_id,
    )
    if not applied:
        logger.warning(
            "Approved learned_response not applied to draft",
            extra={"context": {"learned_response_id": str(learned_response.id)}},
        )

    point_id = add_learned_response_to_knowledge(db, learned_response)
    if point_id:
        learned_response.qdrant_point_id = point_id

    learned_response.updated_at = datetime.now(timezone.utc)
    return applied


def reject_learned_response(
    db: Session,
    *,
    learned_response: LearnedResponse,
    actor_id: Optional[UUID],
) -> None:
    now = datetime.now(timezone.utc)
    learned_response.status = "rejected"
    learned_response.rejected_at = now
    learned_response.updated_at = now
    logger.info(
        "Learned response rejected",
        extra={
            "context": {
                "learned_response_id": str(learned_response.id),
                "actor_id": str(actor_id) if actor_id else None,
            }
        },
    )


def apply_learned_response_to_draft(
    db: Session,
    *,
    learned_response: LearnedResponse,
    actor_id: Optional[UUID],
) -> bool:
    if not learned_response.branch_id:
        return False
    current = get_current_published(db, branch_id=learned_response.branch_id)
    if not current:
        return False

    payload = strip_compiled_artifacts(current.payload_json)
    if not isinstance(payload, dict):
        return False
    client_pack = payload.get("client_pack")
    if not isinstance(client_pack, dict):
        return False

    faq = client_pack.get("faq")
    if not isinstance(faq, list):
        faq = []
    normalized_question = _normalize_text(learned_response.question_text)
    for item in faq:
        if not isinstance(item, dict):
            continue
        existing_q = _normalize_text(str(item.get("question") or ""))
        existing_a = _normalize_text(str(item.get("answer") or ""))
        if existing_q == normalized_question and existing_a:
            return True

    entry = {
        "question": learned_response.question_text,
        "answer": learned_response.response_text,
        "source": learned_response.source,
        "handover_id": str(learned_response.handover_id) if learned_response.handover_id else None,
    }
    faq.append(entry)
    client_pack["faq"] = faq
    payload["client_pack"] = client_pack

    upsert_draft(
        db,
        branch_id=learned_response.branch_id,
        client_id=learned_response.client_id,
        payload_json=payload,
        actor_id=actor_id,
    )
    return True
