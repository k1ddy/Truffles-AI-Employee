from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Client
from app.services.alert_service import alert_critical

logger = get_logger("chatflow_service")

CHATFLOW_API_URL = "https://app.chatflow.kz/api/v1/send-text"
CHATFLOW_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiJhTFpMend0d1AzUnBCWHpHNlNzbG1aNWNTOTZib1F5YyIsInJvbGUiOiJ1c2VyIiwiaWF0IjoxNzYyMTExNDU2fQ.myOt6xgCLfqbD9IF9EdJxkAyjij3fMty1B7sOhP2iKA"


def get_instance_id(db: Session, client_id: UUID) -> Optional[str]:
    """Get ChatFlow instance_id for client."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if client and client.config:
        return client.config.get("instance_id")
    return None


def send_whatsapp_message(instance_id: str, remote_jid: str, message: str) -> bool:
    """Send message via ChatFlow API."""
    if not instance_id or not message:
        logger.warning(f"send_whatsapp_message: missing instance_id={instance_id} or message")
        return False

    try:
        logger.debug(f"Sending to ChatFlow: jid={remote_jid}, instance_id={instance_id[:20]}...")
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                CHATFLOW_API_URL,
                params={
                    "token": CHATFLOW_TOKEN,
                    "instance_id": instance_id,
                    "jid": remote_jid,
                    "msg": message,
                },
            )
            logger.debug(f"ChatFlow response: {response.status_code} - {response.text[:200]}")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}")
        alert_critical("WhatsApp send failed", {"jid": remote_jid, "error": str(e)})
        return False


def send_bot_response(db: Session, client_id: UUID, remote_jid: str, message: str) -> bool:
    """Send bot response to WhatsApp user."""
    instance_id = get_instance_id(db, client_id)
    if not instance_id:
        logger.warning(f"No instance_id found for client {client_id}")
        return False

    return send_whatsapp_message(instance_id, remote_jid, message)
