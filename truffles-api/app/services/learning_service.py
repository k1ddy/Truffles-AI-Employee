import re
import uuid
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Client, ClientSettings, Handover
from app.services.alert_service import alert_error, alert_warning
from app.services.knowledge_service import (
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    QDRANT_HOST,
    get_embedding,
)

logger = get_logger("learning_service")

MAX_KNOWLEDGE_TEXT_LENGTH = 2000
MIN_QUESTION_LENGTH = 5
MIN_ANSWER_LENGTH = 5


def _normalize_telegram_identifier(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return value.strip().lstrip("@")


def _split_owner_identifiers(raw_value: Optional[str]) -> list[str]:
    if not raw_value:
        return []
    parts = re.split(r"[\s,]+", raw_value.strip())
    normalized: list[str] = []
    for part in parts:
        if not part:
            continue
        token = _normalize_telegram_identifier(part)
        if token:
            normalized.append(token)
    return normalized


def is_owner_response(
    db: Session,
    client_id: UUID,
    manager_telegram_id: int,
    manager_username: Optional[str] = None,
) -> bool:
    """
    Check if manager is the owner of this client.

    owner_telegram_id в client_settings может быть:
    - "@username"
    - "123456789" (telegram user id)
    """
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client_id).first()

    if not settings or not settings.owner_telegram_id:
        return False

    owner_ids = _split_owner_identifiers(settings.owner_telegram_id)
    if not owner_ids:
        return False

    manager_id = str(manager_telegram_id) if manager_telegram_id else None
    normalized_username = _normalize_telegram_identifier(manager_username) if manager_username else None

    for owner_id in owner_ids:
        # Prefer numeric ID match when owner_telegram_id is a user/chat id.
        if owner_id.lstrip("-").isdigit():
            if manager_id and manager_id == owner_id:
                return True
            continue

        # Fall back to username match (case-insensitive).
        if normalized_username and normalized_username.lower() == owner_id.lower():
            return True

    if not manager_id and not normalized_username:
        logger.debug("Owner response check: missing manager id/username")
    else:
        logger.debug(
            "Owner response mismatch",
            extra={
                "context": {
                    "owner_ids": owner_ids,
                    "manager_id": manager_id,
                    "manager_username": normalized_username,
                }
            },
        )
    return False


def get_client_slug(db: Session, client_id: UUID) -> Optional[str]:
    """Get client slug (name) for Qdrant filtering."""
    client = db.query(Client).filter(Client.id == client_id).first()
    return client.name if client else None


def _trim_text(text: str) -> str:
    """Trim long text to keep Qdrant payloads bounded."""
    if text is None:
        return ""
    if len(text) <= MAX_KNOWLEDGE_TEXT_LENGTH:
        return text
    return text[:MAX_KNOWLEDGE_TEXT_LENGTH]


def add_to_knowledge(
    db: Session,
    handover: Handover,
    source: str = "learned",
) -> Optional[str]:
    """
    Add manager response to Qdrant knowledge base.

    Returns point_id if successful, None otherwise.
    """
    if not handover.user_message or not handover.manager_response:
        logger.warning("Cannot add to knowledge: missing user_message or manager_response")
        alert_warning(
            "Learning skipped: missing text",
            {"handover_id": str(getattr(handover, "id", None)), "client_id": str(handover.client_id)},
        )
        return None

    client_slug = get_client_slug(db, handover.client_id)
    if not client_slug:
        logger.warning(f"Cannot add to knowledge: client_slug not found for {handover.client_id}")
        alert_warning(
            "Learning skipped: client_slug not found",
            {"handover_id": str(getattr(handover, "id", None)), "client_id": str(handover.client_id)},
        )
        return None

    # Format content for indexing
    question = _trim_text(handover.user_message.strip())
    answer = _trim_text(handover.manager_response.strip())
    if len(question) < MIN_QUESTION_LENGTH or len(answer) < MIN_ANSWER_LENGTH:
        logger.info(
            "Skipped learning: text too short",
            extra={
                "context": {
                    "client_slug": client_slug,
                    "handover_id": str(handover.id),
                    "question_len": len(question),
                    "answer_len": len(answer),
                }
            },
        )
        alert_warning(
            "Learning skipped: text too short",
            {
                "handover_id": str(handover.id),
                "client_slug": client_slug,
                "question_len": len(question),
                "answer_len": len(answer),
            },
        )
        return None

    content = f"Вопрос: {question}\nОтвет: {answer}"
    if len(handover.user_message.strip()) > len(question) or len(handover.manager_response.strip()) > len(answer):
        logger.info("Truncated knowledge sample to fit length limits")

    try:
        # Get embedding
        embedding = get_embedding(content)

        # Generate point ID
        point_id = str(uuid.uuid4())

        # Upsert to Qdrant
        with httpx.Client(timeout=30.0) as client:
            response = client.put(
                f"{QDRANT_HOST}/collections/{QDRANT_COLLECTION}/points",
                headers={"api-key": QDRANT_API_KEY},
                json={
                    "points": [
                        {
                            "id": point_id,
                            "vector": embedding,
                            "payload": {
                                "content": content,
                                "metadata": {
                                    "client_slug": client_slug,
                                    "source": source,
                                    "handover_id": str(handover.id),
                                    "question": question,
                                    "answer": answer,
                                    "learned_from": handover.assigned_to_name or "manager",
                                },
                            },
                        }
                    ]
                },
            )

            if response.status_code not in [200, 201]:
                logger.error(f"Qdrant upsert error: {response.status_code} - {response.text}")
                alert_error("Failed to add to knowledge", {"handover_id": str(handover.id), "status": response.status_code})
                return None

            context = {
                "point_id": point_id,
                "client_slug": client_slug,
                "handover_id": str(handover.id),
                "question_len": len(question),
                "answer_len": len(answer),
                "source": source,
            }
            logger.info("Added to knowledge", extra={"context": context})
            alert_warning("Learning success", context)
            return point_id

    except Exception as e:
        logger.error(f"Error adding to knowledge: {e}", exc_info=True)
        alert_error("Learning service error", {"handover_id": str(handover.id), "error": str(e)})
        return None
