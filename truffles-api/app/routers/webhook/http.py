"""HTTP endpoints for webhook ingress and media serving."""

from __future__ import annotations

import os
import re
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.models import Branch, Client, ClientSettings
from app.routers.webhook.media import _extract_media_info
from app.routers.webhook.parsing import _parse_webhook_request
from app.routers.webhook.secrets import _get_client_webhook_secret, _get_request_webhook_secret
from app.schemas.webhook import WebhookRequest, WebhookResponse
from app.services.alert_service import alert_warning
from app.services.chatflow_service import verify_signed_media_path

from . import _legacy as legacy

logger = get_logger("webhook")
router = APIRouter()

def _normalize_phone_digits(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\D", "", value)

def _lookup_sender_branch(db: Session, remote_jid: str | None) -> Branch | None:
    digits = _normalize_phone_digits(remote_jid)
    if not digits:
        return None
    return (
        db.query(Branch)
        .filter(
            Branch.is_active.is_(True),
            Branch.phone.isnot(None),
            func.regexp_replace(Branch.phone, r"\D", "", "g") == digits,
        )
        .first()
    )


def _run_preflight(
    payload: WebhookRequest,
    db: Session,
    *,
    provided_secret: str | None,
    enforce_secret: bool,
    conversation_id: UUID | None,
    resolve_trace_conversation,
    record_early_trace,
) -> tuple[WebhookResponse | None, dict]:
    client = db.query(Client).filter(Client.name == payload.client_slug).first()
    if not client:
        trace_conversation = resolve_trace_conversation(
            trace_client=None,
            trace_conversation_id=conversation_id,
            trace_message_id=None,
            trace_remote_jid=None,
        )
        if record_early_trace(
            trace_conversation,
            stage="preflight",
            decision="reject",
            reason="client_missing",
        ):
            db.commit()
        return WebhookResponse(success=False, message=f"Client '{payload.client_slug}' not found"), {}

    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client.id).first()
    if enforce_secret:
        expected_secret = _get_client_webhook_secret(settings)
        if expected_secret:
            if not provided_secret or provided_secret != expected_secret:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")
        elif not provided_secret:
            alert_warning("Webhook secret missing", {"client_slug": payload.client_slug})

    body = payload.body
    metadata = body.metadata
    message_id = metadata.messageId if metadata else None
    if not metadata or not metadata.remoteJid:
        trace_conversation = resolve_trace_conversation(
            trace_client=client,
            trace_conversation_id=conversation_id,
            trace_message_id=message_id,
            trace_remote_jid=None,
        )
        if record_early_trace(
            trace_conversation,
            stage="preflight",
            decision="reject",
            reason="missing_remote_jid",
        ):
            db.commit()
        return WebhookResponse(success=False, message="Missing metadata.remoteJid"), {}

    remote_jid = metadata.remoteJid
    sender_branch = _lookup_sender_branch(db, remote_jid)
    if sender_branch:
        trace_conversation = resolve_trace_conversation(
            trace_client=client,
            trace_conversation_id=conversation_id,
            trace_message_id=message_id,
            trace_remote_jid=remote_jid,
        )
        if record_early_trace(
            trace_conversation,
            stage="preflight",
            decision="ignore",
            reason="sender_is_branch",
            meta={
                "sender_branch_id": str(sender_branch.id),
                "sender_branch_client_id": str(sender_branch.client_id),
                "sender_branch_phone": sender_branch.phone,
            },
        ):
            db.commit()
        return WebhookResponse(success=True, message="Ignored sender (branch number)"), {}
    message_text = body.message or ""
    media_info = _extract_media_info(body)
    if not message_text.strip() and media_info and media_info.caption:
        message_text = media_info.caption
    message_type = (body.messageType or "").strip()
    has_media = bool(body.mediaData) or (message_type and message_type.lower() != "text")
    is_media_without_text = has_media and not message_text.strip()
    if not message_text and not is_media_without_text:
        trace_conversation = resolve_trace_conversation(
            trace_client=client,
            trace_conversation_id=conversation_id,
            trace_message_id=message_id,
            trace_remote_jid=remote_jid,
        )
        if record_early_trace(
            trace_conversation,
            stage="preflight",
            decision="reject",
            reason="empty_message",
        ):
            db.commit()
        return WebhookResponse(success=False, message="Empty message"), {}
    if is_media_without_text:
        media_label = message_type.lower() if message_type else "media"
        message_text = f"[{media_label}]"

    return (
        None,
        {
            "client": client,
            "settings": settings,
            "body": body,
            "metadata": metadata,
            "message_id": message_id,
            "remote_jid": remote_jid,
            "message_text": message_text,
            "message_type": message_type,
            "has_media": has_media,
            "is_media_without_text": is_media_without_text,
            "media_info": media_info,
        },
    )


@router.get("/media/{media_path:path}")
async def serve_media(media_path: str, expires: int, sig: str):
    """Serve locally stored media via signed URLs."""
    normalized_path = (media_path or "").strip().lstrip("/")
    if not normalized_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing media path")
    if not verify_signed_media_path(normalized_path, expires, sig):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired signature")

    base_dir = Path(legacy.MEDIA_STORAGE_DEFAULT_DIR).resolve()
    target_path = (base_dir / normalized_path).resolve()
    if base_dir not in target_path.parents and target_path != base_dir:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid media path")
    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    return FileResponse(target_path)


@router.post("/webhook/debug")
async def debug_webhook(request: Request):
    """Debug endpoint to see raw request."""
    if not legacy._is_env_enabled(os.environ.get("DEBUG_WEBHOOK_ENABLED"), default=False):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    admin_token = request.headers.get("X-Admin-Token")
    expected_token = os.environ.get("ALERTS_ADMIN_TOKEN")
    if not expected_token or admin_token != expected_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")
    body = await request.json()
    logger.debug(f"DEBUG webhook body: {body}")
    return {"received": body}


@router.post("/webhook/{client_slug}", response_model=WebhookResponse)
async def handle_webhook_direct(client_slug: str, request: Request, db: Session = Depends(get_db)):
    """Handle direct ChatFlow webhook without wrapper."""
    parsed = await _parse_webhook_request(request, client_slug=client_slug)
    if isinstance(parsed, WebhookResponse):
        return parsed

    provided_secret = _get_request_webhook_secret(request)
    client = db.query(Client).filter(Client.name == parsed.client_slug).first()
    if not client:
        return WebhookResponse(success=False, message=f"Client '{parsed.client_slug}' not found")

    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client.id).first()
    expected_secret = _get_client_webhook_secret(settings)
    if expected_secret:
        if not provided_secret or provided_secret != expected_secret:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")
    elif not provided_secret:
        alert_warning("Webhook secret missing", {"client_slug": parsed.client_slug})

    return await legacy._handle_webhook_payload(
        parsed,
        db,
        provided_secret=provided_secret,
        enforce_secret=False,
        enqueue_only=True,
    )


@router.get("/webhook/{client_slug}")
async def handle_webhook_probe(client_slug: str):
    """Health probe for ChatFlow UI checks; real webhooks must use POST."""
    return {"ok": True, "message": "Use POST with JSON payload", "client_slug": client_slug}


@router.post("/webhook", response_model=WebhookResponse)
async def handle_webhook(payload: WebhookRequest, http_request: Request, db: Session = Depends(get_db)):
    """Handle legacy webhook wrapper (same format as ChatFlow webhook)."""
    provided_secret = _get_request_webhook_secret(http_request)
    return await legacy._handle_webhook_payload(
        payload,
        db,
        provided_secret=provided_secret,
        enforce_secret=True,
        enqueue_only=True,
    )


__all__ = [
    "handle_webhook",
    "handle_webhook_direct",
    "handle_webhook_probe",
    "router",
    "serve_media",
]
