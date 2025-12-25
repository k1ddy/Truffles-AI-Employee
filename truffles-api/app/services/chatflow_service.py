import hashlib
import hmac
import os
import time
from typing import Optional
from urllib.parse import quote
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Client
from app.services.alert_service import alert_critical

logger = get_logger("chatflow_service")

CHATFLOW_API_URL = os.environ.get("CHATFLOW_API_URL", "https://app.chatflow.kz/api/v1/send-text")
CHATFLOW_TOKEN = os.environ.get("CHATFLOW_TOKEN")
CHATFLOW_MEDIA_BASE_URL = os.environ.get("CHATFLOW_MEDIA_BASE_URL", "https://app.chatflow.kz/api/v1")
MEDIA_SIGNING_SECRET = os.environ.get("MEDIA_SIGNING_SECRET")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000")
MEDIA_URL_TTL_SECONDS = int(os.environ.get("MEDIA_URL_TTL_SECONDS", "3600"))


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


def _normalize_media_path(path: str) -> str:
    normalized = (path or "").strip().lstrip("/")
    return normalized.replace("\\", "/")


def _sign_media_path(path: str, expires: int, secret: str) -> str:
    payload = f"{path}:{expires}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def build_signed_media_url(relative_path: str, *, ttl_seconds: Optional[int] = None) -> Optional[str]:
    """Build signed public URL for media file under MEDIA_STORAGE_DEFAULT_DIR."""
    if not MEDIA_SIGNING_SECRET:
        logger.error("MEDIA_SIGNING_SECRET not configured")
        return None
    ttl = ttl_seconds if ttl_seconds is not None else MEDIA_URL_TTL_SECONDS
    expires = int(time.time()) + max(int(ttl), 60)
    normalized_path = _normalize_media_path(relative_path)
    signature = _sign_media_path(normalized_path, expires, MEDIA_SIGNING_SECRET)
    quoted_path = quote(normalized_path, safe="/")
    return f"{PUBLIC_BASE_URL.rstrip('/')}/media/{quoted_path}?expires={expires}&sig={signature}"


def verify_signed_media_path(relative_path: str, expires: int, signature: str) -> bool:
    if not MEDIA_SIGNING_SECRET:
        logger.error("MEDIA_SIGNING_SECRET not configured")
        return False
    if not signature:
        return False
    now_ts = int(time.time())
    if expires < now_ts:
        return False
    normalized_path = _normalize_media_path(relative_path)
    expected = _sign_media_path(normalized_path, expires, MEDIA_SIGNING_SECRET)
    return hmac.compare_digest(expected, signature)


def send_whatsapp_media(
    instance_id: str,
    remote_jid: str,
    *,
    media_type: str,
    media_url: str,
    caption: Optional[str] = None,
) -> bool:
    """Send media via ChatFlow API (image/audio/document/video)."""
    if not CHATFLOW_TOKEN:
        logger.error("ChatFlow token is missing (CHATFLOW_TOKEN env var not set)")
        alert_critical("WhatsApp media send failed", {"jid": remote_jid, "error": "missing_chatflow_token"})
        return False

    if not instance_id or not remote_jid or not media_url:
        logger.warning("send_whatsapp_media: missing instance_id, jid, or media_url")
        return False

    kind = (media_type or "").strip().lower()
    endpoint = None
    url_param = None
    allow_caption = False
    if kind in {"photo", "image"}:
        endpoint = "send-image"
        url_param = "imageurl"
        allow_caption = True
    elif kind in {"audio", "voice"}:
        endpoint = "send-audio"
        url_param = "audiourl"
    elif kind in {"document", "doc"}:
        endpoint = "send-doc"
        url_param = "docurl"
        allow_caption = True
    elif kind == "video":
        endpoint = "send-video"
        url_param = "videourl"
        allow_caption = True

    if not endpoint or not url_param:
        logger.warning(f"send_whatsapp_media: unsupported media_type={media_type}")
        return False

    url = f"{CHATFLOW_MEDIA_BASE_URL.rstrip('/')}/{endpoint}"
    params = {
        "token": CHATFLOW_TOKEN,
        "instance_id": instance_id,
        "jid": remote_jid,
        url_param: media_url,
    }
    if allow_caption:
        # ChatFlow rejects image/doc/video requests without a non-empty caption.
        if caption and caption.strip():
            params["caption"] = caption.strip()
        else:
            params["caption"] = " "

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            logger.info(
                f"ChatFlow media response: status={response.status_code}, jid={remote_jid}, body={response.text[:200]}"
            )
            if response.status_code != 200:
                return False
            try:
                payload = response.json()
            except Exception:
                return False
            return bool(payload.get("success"))
    except Exception as e:
        logger.error(f"Error sending WhatsApp media: {e}")
        alert_critical("WhatsApp media send failed", {"jid": remote_jid, "error": str(e)})
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
