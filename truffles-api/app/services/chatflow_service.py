import os
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Client
from app.services.alert_service import alert_critical

logger = get_logger("chatflow_service")

CHATFLOW_API_URL = os.environ.get("CHATFLOW_API_URL", "https://app.chatflow.kz/api/v1/send-text")
CHATFLOW_TOKEN = os.environ.get("CHATFLOW_TOKEN")


def get_instance_id(db: Session, client_id: UUID) -> Optional[str]:
    """Get ChatFlow instance_id for client."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if client and client.config:
        return client.config.get("instance_id")
    return None


def send_whatsapp_message(
    instance_id: str,
    remote_jid: str,
    message: str,
    idempotency_key: Optional[str] = None,
) -> bool:
    """Send message via ChatFlow API."""
    if not CHATFLOW_TOKEN:
        logger.error("ChatFlow token is missing (CHATFLOW_TOKEN env var not set)")
        alert_critical("WhatsApp send failed", {"jid": remote_jid, "error": "missing_chatflow_token"})
        return False

    if not instance_id or not message:
        logger.warning(f"send_whatsapp_message: missing instance_id={instance_id} or message")
        return False

    try:
        logger.debug(f"Sending to ChatFlow: jid={remote_jid}, instance_id={instance_id[:20]}...")
        params = {
            "token": CHATFLOW_TOKEN,
            "instance_id": instance_id,
            "jid": remote_jid,
            "msg": message,
        }
        if idempotency_key:
            params["msg_id"] = idempotency_key
        with httpx.Client(timeout=30.0) as client:
            response = client.get(CHATFLOW_API_URL, params=params)
            logger.info(
                f"ChatFlow response: status={response.status_code}, jid={remote_jid}, body={response.text[:200]}"
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}")
        alert_critical("WhatsApp send failed", {"jid": remote_jid, "error": str(e)})
        return False


def send_bot_response(
    db: Session,
    client_id: UUID,
    remote_jid: str,
    message: str,
    *,
    idempotency_key: Optional[str] = None,
    raise_on_fail: bool = False,
) -> bool:
    """Send bot response to WhatsApp user."""
    instance_id = get_instance_id(db, client_id)
    if not instance_id:
        logger.warning(f"No instance_id found for client {client_id}, jid={remote_jid}")
        return False

    ok = send_whatsapp_message(instance_id, remote_jid, message, idempotency_key=idempotency_key)
    if not ok:
        logger.warning(f"Failed to deliver via ChatFlow: jid={remote_jid}, client_id={client_id}")
        if raise_on_fail:
            raise RuntimeError("ChatFlow delivery failed")
    else:
        logger.info(f"Delivered via ChatFlow: jid={remote_jid}")
    return ok
