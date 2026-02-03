import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.contracts import ConfigError, Err, ErrorCodes, IntegrationError, Ok, Result
from app.logging_config import get_logger, record_delivery_failure
from app.models import Branch, Client, Conversation, User
from app.services.alert_service import alert_critical, alert_error

logger = get_logger("chatflow_service")

CHATFLOW_API_URL = os.environ.get("CHATFLOW_API_URL", "https://app.chatflow.kz/api/v1/send-text")
CHATFLOW_TOKEN = os.environ.get("CHATFLOW_TOKEN")
CHATFLOW_MEDIA_BASE_URL = os.environ.get("CHATFLOW_MEDIA_BASE_URL", "https://app.chatflow.kz/api/v1")
MEDIA_SIGNING_SECRET = os.environ.get("MEDIA_SIGNING_SECRET")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000")
MEDIA_URL_TTL_SECONDS = int(os.environ.get("MEDIA_URL_TTL_SECONDS", "3600"))
TEST_MODE = os.environ.get("TEST_MODE", "").strip().lower() in {"1", "true", "yes", "on"}
OUTBOUND_ALLOWLIST_JIDS = {
    jid.strip()
    for jid in os.environ.get("OUTBOUND_ALLOWLIST_JIDS", "").split(",")
    if jid.strip()
}


def _get_test_mode() -> bool:
    raw = os.environ.get("TEST_MODE")
    if raw is None:
        return TEST_MODE
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_outbound_allowlist() -> set[str]:
    raw = os.environ.get("OUTBOUND_ALLOWLIST_JIDS")
    if raw is None:
        return OUTBOUND_ALLOWLIST_JIDS
    return {jid.strip() for jid in raw.split(",") if jid.strip()}


def _get_chatflow_token() -> str | None:
    return os.environ.get("CHATFLOW_TOKEN") or CHATFLOW_TOKEN


def _get_chatflow_api_url() -> str:
    return os.environ.get("CHATFLOW_API_URL") or CHATFLOW_API_URL


def _get_chatflow_media_base_url() -> str:
    return os.environ.get("CHATFLOW_MEDIA_BASE_URL") or CHATFLOW_MEDIA_BASE_URL


def _should_skip_outbound(remote_jid: str, *, action: str) -> bool:
    if not _get_test_mode():
        return False
    jid = (remote_jid or "").strip()
    allowlist = _get_outbound_allowlist()
    if jid and jid in allowlist:
        return False
    allowlist_value = ",".join(sorted(allowlist)) or "<empty>"
    logger.warning(
        "Outbound guard: TEST_MODE enabled, SKIP %s to jid=%s (allowlist=%s)",
        action,
        jid or "<missing>",
        allowlist_value,
    )
    return True


def _get_branch_instance_id(db: Session, client_id: UUID, branch_id: UUID | None) -> Optional[str]:
    if not branch_id:
        return None
    branch = (
        db.query(Branch)
        .filter(Branch.id == branch_id, Branch.client_id == client_id)
        .first()
    )
    if branch and branch.instance_id:
        return branch.instance_id
    return None


def get_instance_id(
    db: Session,
    client_id: UUID,
    *,
    branch_id: UUID | None = None,
    remote_jid: str | None = None,
) -> Optional[str]:
    """Resolve ChatFlow instance_id (branch-aware, with client fallback)."""
    instance_id = _get_branch_instance_id(db, client_id, branch_id)
    if not instance_id and remote_jid:
        conversation = (
            db.query(Conversation)
            .join(User, User.id == Conversation.user_id)
            .filter(
                Conversation.client_id == client_id,
                Conversation.status == "active",
                User.remote_jid == remote_jid,
            )
            .first()
        )
        if conversation and conversation.branch_id:
            instance_id = _get_branch_instance_id(db, client_id, conversation.branch_id)
    if instance_id:
        return instance_id
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
    if _should_skip_outbound(remote_jid, action="message"):
        return True

    token = _get_chatflow_token()
    if not token:
        logger.error("ChatFlow token is missing (CHATFLOW_TOKEN env var not set)")
        alert_critical("WhatsApp send failed", {"jid": remote_jid, "error": "missing_chatflow_token"})
        record_delivery_failure(None, source="chatflow", provider="chatflow", reason="missing_token")
        return False

    if not instance_id or not message:
        logger.warning(f"send_whatsapp_message: missing instance_id={instance_id} or message")
        record_delivery_failure(None, source="chatflow", provider="chatflow", reason="invalid_payload")
        return False

    try:
        logger.debug(f"Sending to ChatFlow: jid={remote_jid}, instance_id={instance_id[:20]}...")
        params = {
            "token": token,
            "instance_id": instance_id,
            "jid": remote_jid,
            "msg": message,
        }
        if idempotency_key:
            params["msg_id"] = idempotency_key
        with httpx.Client(timeout=30.0) as client:
            response = client.get(_get_chatflow_api_url(), params=params)
            logger.info(
                f"ChatFlow response: status={response.status_code}, jid={remote_jid}, body={response.text[:200]}"
            )
            if response.status_code != 200:
                record_delivery_failure(
                    None,
                    source="chatflow",
                    provider="chatflow",
                    reason=f"status_{response.status_code}",
                )
                alert_error(
                    "WhatsApp send failed",
                    {"jid": remote_jid, "status": response.status_code, "body": response.text[:200]},
                )
                return False
            return True
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}")
        alert_critical("WhatsApp send failed", {"jid": remote_jid, "error": str(e)})
        record_delivery_failure(None, source="chatflow", provider="chatflow", reason="exception")
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
    timeout_seconds: float = 30.0,
    notify_on_failure: bool = True,
    record_metrics: bool = True,
) -> bool:
    """Send media via ChatFlow API (image/audio/document/video)."""
    if _should_skip_outbound(remote_jid, action="media"):
        return True

    token = _get_chatflow_token()
    if not token:
        logger.error("ChatFlow token is missing (CHATFLOW_TOKEN env var not set)")
        if notify_on_failure:
            alert_critical("WhatsApp media send failed", {"jid": remote_jid, "error": "missing_chatflow_token"})
        if record_metrics:
            record_delivery_failure(None, source="chatflow", provider="chatflow", reason="missing_token")
        return False

    if not instance_id or not remote_jid or not media_url:
        logger.warning("send_whatsapp_media: missing instance_id, jid, or media_url")
        if record_metrics:
            record_delivery_failure(None, source="chatflow", provider="chatflow", reason="invalid_payload")
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
        if record_metrics:
            record_delivery_failure(None, source="chatflow", provider="chatflow", reason="unsupported_media")
        return False

    url = f"{_get_chatflow_media_base_url().rstrip('/')}/{endpoint}"
    params = {
        "token": token,
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
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get(url, params=params)
            logger.info(
                f"ChatFlow media response: status={response.status_code}, jid={remote_jid}, body={response.text[:200]}"
            )
            if response.status_code != 200:
                if record_metrics:
                    record_delivery_failure(
                        None,
                        source="chatflow",
                        provider="chatflow",
                        reason=f"status_{response.status_code}",
                    )
                if notify_on_failure:
                    alert_error(
                        "WhatsApp media send failed",
                        {"jid": remote_jid, "status": response.status_code, "body": response.text[:200]},
                    )
                return False
            try:
                payload = response.json()
            except Exception:
                if record_metrics:
                    record_delivery_failure(
                        None,
                        source="chatflow",
                        provider="chatflow",
                        reason="invalid_response",
                    )
                return False
            success = bool(payload.get("success"))
            if not success:
                if record_metrics:
                    record_delivery_failure(
                        None,
                        source="chatflow",
                        provider="chatflow",
                        reason="payload_failure",
                    )
                if notify_on_failure:
                    alert_error(
                        "WhatsApp media send failed",
                        {"jid": remote_jid, "error": "payload_success_false"},
                    )
            return success
    except Exception as e:
        logger.error(f"Error sending WhatsApp media: {e}")
        if notify_on_failure:
            alert_critical("WhatsApp media send failed", {"jid": remote_jid, "error": str(e)})
        if record_metrics:
            record_delivery_failure(None, source="chatflow", provider="chatflow", reason="exception")
        return False

def send_bot_response(
    db: Session,
    client_id: UUID,
    remote_jid: str,
    message: str,
    *,
    branch_id: UUID | None = None,
    idempotency_key: Optional[str] = None,
    raise_on_fail: bool = False,
) -> bool:
    """Send bot response to WhatsApp user."""
    instance_id = get_instance_id(db, client_id, branch_id=branch_id, remote_jid=remote_jid)
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


# ============================================================================
# Result-based API (новый контракт)
# ============================================================================

@dataclass
class MessageSent:
    """Результат успешной отправки сообщения."""
    remote_jid: str
    instance_id: str


def send_message_safe(
    instance_id: str,
    remote_jid: str,
    message: str,
    idempotency_key: Optional[str] = None,
    *,
    notify_on_failure: bool = True,
    record_metrics: bool = True,
) -> Result[MessageSent]:
    """
    Отправить сообщение через ChatFlow с Result-контрактом.
    
    Возвращает Result.ok(MessageSent) или Result.fail(IntegrationError).
    """
    if _should_skip_outbound(remote_jid, action="message"):
        return Ok(MessageSent(remote_jid=remote_jid, instance_id=instance_id))

    token = _get_chatflow_token()
    if not token:
        logger.error("ChatFlow token is missing (CHATFLOW_TOKEN env var not set)")
        if notify_on_failure:
            alert_critical("WhatsApp send failed", {"jid": remote_jid, "error": "missing_chatflow_token"})
        if record_metrics:
            record_delivery_failure(None, source="chatflow", provider="chatflow", reason="missing_token")
        return Err(ConfigError(
            code=ErrorCodes.CONFIG_MISSING,
            message="CHATFLOW_TOKEN not configured",
            context={"remote_jid": remote_jid},
        ))

    if not instance_id or not message:
        if record_metrics:
            record_delivery_failure(None, source="chatflow", provider="chatflow", reason="invalid_payload")
        return Err(IntegrationError(
            code=ErrorCodes.INVALID_PAYLOAD,
            message="Missing instance_id or message",
            service="chatflow",
            context={"instance_id": instance_id, "has_message": bool(message)},
        ))

    try:
        logger.debug(f"Sending to ChatFlow: jid={remote_jid}, instance_id={instance_id[:20]}...")
        params = {
            "token": token,
            "instance_id": instance_id,
            "jid": remote_jid,
            "msg": message,
        }
        if idempotency_key:
            params["msg_id"] = idempotency_key
            
        with httpx.Client(timeout=30.0) as client:
            response = client.get(_get_chatflow_api_url(), params=params)
            logger.info(
                f"ChatFlow response: status={response.status_code}, jid={remote_jid}, body={response.text[:200]}"
            )
            if response.status_code == 200:
                return Ok(MessageSent(remote_jid=remote_jid, instance_id=instance_id))
            if record_metrics:
                record_delivery_failure(
                    None,
                    source="chatflow",
                    provider="chatflow",
                    reason=f"status_{response.status_code}",
                )
            if notify_on_failure:
                alert_error(
                    "WhatsApp send failed",
                    {"jid": remote_jid, "status": response.status_code, "body": response.text[:200]},
                )
            return Err(IntegrationError(
                code=ErrorCodes.CHATFLOW_ERROR,
                message=f"ChatFlow returned {response.status_code}",
                service="chatflow",
                context={"status_code": response.status_code, "body": response.text[:200]},
            ))
    except httpx.TimeoutException as e:
        logger.error(f"ChatFlow timeout: {e}")
        if notify_on_failure:
            alert_critical("WhatsApp send timeout", {"jid": remote_jid})
        if record_metrics:
            record_delivery_failure(None, source="chatflow", provider="chatflow", reason="timeout")
        return Err(IntegrationError(
            code=ErrorCodes.CHATFLOW_TIMEOUT,
            message="ChatFlow request timed out",
            service="chatflow",
            context={"remote_jid": remote_jid, "timeout": 30.0},
        ))
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}")
        if notify_on_failure:
            alert_critical("WhatsApp send failed", {"jid": remote_jid, "error": str(e)})
        if record_metrics:
            record_delivery_failure(None, source="chatflow", provider="chatflow", reason="exception")
        return Err(IntegrationError(
            code=ErrorCodes.CHATFLOW_ERROR,
            message=str(e),
            service="chatflow",
            context={"remote_jid": remote_jid, "exception": type(e).__name__},
        ))


def send_bot_response_safe(
    db: Session,
    client_id: UUID,
    remote_jid: str,
    message: str,
    *,
    branch_id: UUID | None = None,
    idempotency_key: Optional[str] = None,
) -> Result[MessageSent]:
    """
    Отправить ответ бота через WhatsApp с Result-контрактом.
    
    Возвращает Result.ok(MessageSent) или Result.fail(IntegrationError).
    """
    instance_id = get_instance_id(db, client_id, branch_id=branch_id, remote_jid=remote_jid)
    if not instance_id:
        logger.warning(f"No instance_id found for client {client_id}, jid={remote_jid}")
        return Err(ConfigError(
            code=ErrorCodes.CLIENT_NOT_FOUND,
            message="No instance_id configured for client",
            context={"client_id": str(client_id), "remote_jid": remote_jid},
        ))

    result = send_message_safe(
        instance_id,
        remote_jid,
        message,
        idempotency_key,
        notify_on_failure=True,
        record_metrics=True,
    )
    if result.is_ok():
        logger.info(f"Delivered via ChatFlow: jid={remote_jid}")
    else:
        logger.warning(f"Failed to deliver via ChatFlow: jid={remote_jid}, error={result.error}")
    
    return result
