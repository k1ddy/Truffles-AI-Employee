import uuid
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Client, ClientSettings, Handover
from app.services.alert_service import alert_error
from app.services.knowledge_service import (
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    QDRANT_HOST,
    get_embedding,
)

logger = get_logger("learning_service")


def is_owner_response(db: Session, client_id: UUID, manager_telegram_id: int) -> bool:
    """
    Check if manager is the owner of this client.

    owner_telegram_id в client_settings может быть:
    - "@username"
    - "123456789" (telegram user id)
    """
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client_id).first()

    if not settings or not settings.owner_telegram_id:
        return False

    owner_id = settings.owner_telegram_id.lstrip("@")
    manager_id = str(manager_telegram_id)

    return manager_id == owner_id


def get_client_slug(db: Session, client_id: UUID) -> Optional[str]:
    """Get client slug (name) for Qdrant filtering."""
    client = db.query(Client).filter(Client.id == client_id).first()
    return client.name if client else None


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
        return None

    client_slug = get_client_slug(db, handover.client_id)
    if not client_slug:
        logger.warning(f"Cannot add to knowledge: client_slug not found for {handover.client_id}")
        return None

    # Format content for indexing
    content = f"Вопрос: {handover.user_message}\nОтвет: {handover.manager_response}"

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
                                    "question": handover.user_message,
                                    "answer": handover.manager_response,
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

            logger.info(f"Added to knowledge: point_id={point_id}, client_slug={client_slug}")
            return point_id

    except Exception as e:
        logger.error(f"Error adding to knowledge: {e}", exc_info=True)
        alert_error("Learning service error", {"handover_id": str(handover.id), "error": str(e)})
        return None
