"""HTTP endpoints for webhook ingress and media serving."""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.models import Branch, Client, ClientSettings, Conversation, Message, User
from app.routers.webhook.instance_routing import resolve_active_branch_by_instance
from app.routers.webhook.media import _extract_media_info
from app.routers.webhook.parsing import _parse_webhook_request
from app.routers.webhook.secrets import (
    _get_request_webhook_secret,
    _resolve_expected_webhook_secret,
    _webhook_secrets_match,
)
from app.schemas.webhook import WebhookRequest, WebhookResponse
from app.services.alert_service import alert_warning
from app.services.chatflow_service import verify_signed_media_path
from app.services.integration_guardrails_service import (
    REASON_INVALID_WEBHOOK_SECRET,
    REASON_UNKNOWN_INSTANCE_ID,
    report_integration_incident,
)
from app.services.tenant_context_contract import validate_tenant_context_contract

logger = get_logger("webhook")
router = APIRouter()
_MEDIA_STORAGE_DEFAULT_DIR = os.environ.get("MEDIA_STORAGE_DIR", "/home/zhan/truffles-media")


@dataclass(frozen=True)
class _PreflightBridgeCacheEntry:
    payload_id: int
    db_id: int
    conversation_id: UUID | None
    preflight_payload: dict[str, Any]


_PREFLIGHT_BRIDGE_CACHE: ContextVar[_PreflightBridgeCacheEntry | None] = ContextVar(
    "webhook_preflight_bridge_cache",
    default=None,
)


def _should_enqueue_only() -> bool:
    raw = os.environ.get("WEBHOOK_ENQUEUE_ONLY")
    if raw is None:
        return False
    return raw.strip().lower() not in {"0", "false", "no", "off"}

def _normalize_phone_digits(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\D", "", value)

def _lookup_sender_branch(db: Session, remote_jid: str | None) -> Branch | None:
    digits = _normalize_phone_digits(remote_jid)
    if not digits:
        return None
    branch = (
        db.query(Branch)
        .filter(
            Branch.is_active.is_(True),
            Branch.phone.isnot(None),
            func.regexp_replace(Branch.phone, r"\D", "", "g") == digits,
        )
        .first()
    )
    if not branch or not getattr(branch, "phone", None):
        return None
    return branch


def _find_message_by_message_id(
    db: Session,
    *,
    client_id: UUID,
    message_id: str,
) -> Message | None:
    return (
        db.query(Message)
        .filter(
            Message.client_id == client_id,
            or_(
                Message.message_metadata["message_id"].astext == message_id,
                Message.message_metadata["messageId"].astext == message_id,
            ),
        )
        .order_by(Message.created_at.desc())
        .first()
    )


def _resolve_secret_preflight_trace_conversation(
    db: Session,
    *,
    trace_client: Client | None,
    trace_conversation_id: UUID | None,
    trace_message_id: str | None,
    trace_remote_jid: str | None,
) -> Conversation | None:
    if trace_conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == trace_conversation_id).first()
        if conversation:
            return conversation
    if trace_client and trace_message_id:
        saved_message = _find_message_by_message_id(
            db,
            client_id=trace_client.id,
            message_id=trace_message_id,
        )
        if saved_message:
            return (
                db.query(Conversation)
                .filter(Conversation.id == saved_message.conversation_id)
                .first()
            )
    if trace_client and trace_remote_jid:
        user = (
            db.query(User)
            .filter(User.client_id == trace_client.id, User.remote_jid == trace_remote_jid)
            .first()
        )
        if user:
            return (
                db.query(Conversation)
                .filter(
                    Conversation.client_id == trace_client.id,
                    Conversation.user_id == user.id,
                    Conversation.status == "active",
                )
                .first()
            )
    return None


def _record_secret_preflight_trace(
    trace_conversation: Conversation | None,
    *,
    stage: str,
    decision: str,
    reason: str,
    meta: dict[str, object] | None = None,
) -> bool:
    if not trace_conversation:
        return False
    trace_payload: dict[str, object] = {
        "stage": stage,
        "decision": decision,
        "reason": reason,
    }
    if meta:
        trace_payload.update(meta)
    trace = list((trace_conversation.context or {}).get("decision_trace") or [])
    trace.append(trace_payload)
    context = dict(trace_conversation.context or {})
    context["decision_trace"] = trace[-20:]
    trace_conversation.context = context
    return True


def _get_preflight_bridge_cache_payload(
    payload: WebhookRequest,
    db: Session,
    *,
    conversation_id: UUID | None,
    enforce_secret: bool,
) -> dict[str, Any] | None:
    if enforce_secret:
        return None
    cached = _PREFLIGHT_BRIDGE_CACHE.get()
    if cached is None:
        return None
    if cached.payload_id != id(payload):
        return None
    if cached.db_id != id(db):
        return None
    if cached.conversation_id != conversation_id:
        return None
    return cached.preflight_payload


@contextmanager
def _use_preflight_bridge_cache(
    payload: WebhookRequest,
    db: Session,
    *,
    conversation_id: UUID | None,
    preflight_payload: dict[str, Any],
) -> Iterator[None]:
    token = _PREFLIGHT_BRIDGE_CACHE.set(
        _PreflightBridgeCacheEntry(
            payload_id=id(payload),
            db_id=id(db),
            conversation_id=conversation_id,
            preflight_payload=preflight_payload,
        )
    )
    try:
        yield
    finally:
        _PREFLIGHT_BRIDGE_CACHE.reset(token)


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
    cached_preflight_payload = _get_preflight_bridge_cache_payload(
        payload,
        db,
        conversation_id=conversation_id,
        enforce_secret=enforce_secret,
    )
    if cached_preflight_payload is not None:
        return None, cached_preflight_payload

    def _normalize_phone(value: str | None) -> str | None:
        if not value:
            return None
        digits = re.sub(r"\D", "", value)
        return digits or None

    def _normalize_uuid(value: object) -> str | None:
        if value is None:
            return None
        try:
            return str(UUID(str(value)))
        except (TypeError, ValueError, AttributeError):
            return None

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

    body = payload.body
    incoming_tenant_context = payload.tenant_context
    metadata = body.metadata
    message_id = metadata.messageId if metadata else None
    missing_secret_warned = False

    def _raise_invalid_secret(*, branch: Branch | None, instance_id: str | None, branch_mode: str | None):
        report_integration_incident(
            db,
            client=client,
            branch=branch,
            reason=REASON_INVALID_WEBHOOK_SECRET,
            source="webhook_preflight",
            context={
                "message_id": message_id,
                "remote_jid": metadata.remoteJid if metadata else None,
                "instance_id": instance_id,
                "branch_mode": branch_mode,
            },
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")

    if enforce_secret:
        # Enforce client-level secret before payload validation to avoid bypass via malformed bodies.
        client_expected_secret = _resolve_expected_webhook_secret(
            settings=settings,
            branch=None,
        )
        if client_expected_secret and not _webhook_secrets_match(
            provided_secret,
            client_expected_secret,
        ):
            _raise_invalid_secret(
                branch=None,
                instance_id=metadata.instanceId if metadata else None,
                branch_mode=None,
            )
        elif not provided_secret:
            alert_warning(
                "Webhook secret missing",
                {
                    "client_slug": payload.client_slug,
                    "branch_id": None,
                },
            )
            missing_secret_warned = True

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

    tenant_client_slug = (incoming_tenant_context.client_slug or "").strip() if incoming_tenant_context else ""
    if not incoming_tenant_context or (
        incoming_tenant_context.client_id is None and not tenant_client_slug
    ):
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
            reason="missing_tenant_context",
        ):
            db.commit()
        return WebhookResponse(success=False, message="Missing tenant_context"), {}

    def _reject_tenant_context(reason: str, *, message: str = "Tenant mismatch", meta: dict | None = None):
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
            reason=reason,
            meta=meta,
        ):
            db.commit()
        return WebhookResponse(success=False, message=message), {}

    incoming_tenant_payload = incoming_tenant_context.model_dump(exclude_none=True, mode="json")
    _, incoming_tenant_error = validate_tenant_context_contract(
        incoming_tenant_payload,
        require_client_id=False,
    )
    if incoming_tenant_error:
        return _reject_tenant_context(
            "tenant_context_contract_invalid",
            message="Invalid tenant_context",
            meta={"error": incoming_tenant_error},
        )

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

    remote_digits = _normalize_phone(remote_jid)
    if remote_digits:
        branch_phones = (
            db.query(Branch.phone)
            .filter(Branch.client_id == client.id, Branch.phone.isnot(None))
            .all()
        )
        if not isinstance(branch_phones, list):
            branch_phones = []
        for row in branch_phones:
            if isinstance(row, (list, tuple)):
                phone = row[0] if row else None
            else:
                phone = getattr(row, "phone", None)
            if not phone:
                continue
            if remote_digits == _normalize_phone(phone):
                trace_conversation = resolve_trace_conversation(
                    trace_client=client,
                    trace_conversation_id=conversation_id,
                    trace_message_id=message_id,
                    trace_remote_jid=remote_jid,
                )
                if record_early_trace(
                    trace_conversation,
                    stage="preflight",
                    decision="drop",
                    reason="remote_is_branch_phone",
                ):
                    db.commit()
                return WebhookResponse(success=True, message="Ignored branch sender"), {}

    branch_mode = settings.branch_resolution_mode if settings and settings.branch_resolution_mode else "hybrid"
    instance_id = metadata.instanceId if metadata else None
    resolved_branch = None
    instance_match_mode = None
    if branch_mode in {"by_instance", "hybrid"}:
        if not instance_id:
            if branch_mode == "by_instance":
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
                    reason="missing_instance_id",
                    meta={"branch_mode": branch_mode},
                ):
                    db.commit()
                return WebhookResponse(success=False, message="Missing instanceId"), {}
        else:
            resolution = resolve_active_branch_by_instance(
                db,
                client_id=client.id,
                instance_id=instance_id,
            )
            resolved_branch = resolution.branch
            instance_match_mode = resolution.match_mode
            if not resolved_branch:
                trace_conversation = resolve_trace_conversation(
                    trace_client=client,
                    trace_conversation_id=conversation_id,
                    trace_message_id=message_id,
                    trace_remote_jid=remote_jid,
                )
                should_commit = False
                if record_early_trace(
                    trace_conversation,
                    stage="preflight",
                    decision="reject",
                    reason="unknown_instance_id",
                    meta={
                        "branch_mode": branch_mode,
                        "instance_id": instance_id,
                        "instance_match_mode": instance_match_mode,
                    },
                ):
                    should_commit = True
                report_integration_incident(
                    db,
                    client=client,
                    reason=REASON_UNKNOWN_INSTANCE_ID,
                    source="webhook_preflight",
                    context={
                        "instance_id": instance_id,
                        "instance_match_mode": instance_match_mode,
                        "message_id": message_id,
                        "remote_jid": remote_jid,
                    },
                )
                should_commit = True
                if should_commit:
                    db.commit()
                return WebhookResponse(success=False, message="Unknown instanceId"), {}

    if incoming_tenant_context:
        if incoming_tenant_context.client_id and incoming_tenant_context.client_id != client.id:
            return _reject_tenant_context(
                "tenant_context_client_mismatch",
                meta={
                    "tenant_client_id": str(incoming_tenant_context.client_id),
                    "expected_client_id": str(client.id),
                },
            )

        tenant_client_slug = (incoming_tenant_context.client_slug or "").strip()
        if tenant_client_slug and tenant_client_slug != client.name:
            return _reject_tenant_context(
                "tenant_context_client_slug_mismatch",
                meta={
                    "tenant_client_slug": tenant_client_slug,
                    "expected_client_slug": client.name,
                },
            )

        tenant_instance_id = (incoming_tenant_context.instance_id or "").strip()
        if tenant_instance_id and instance_id and tenant_instance_id != instance_id:
            return _reject_tenant_context(
                "tenant_context_instance_mismatch",
                meta={
                    "tenant_instance_id": tenant_instance_id,
                    "instance_id": instance_id,
                },
            )

        tenant_branch = None
        if incoming_tenant_context.branch_id:
            tenant_branch = (
                db.query(Branch)
                .filter(
                    Branch.id == incoming_tenant_context.branch_id,
                    Branch.client_id == client.id,
                    Branch.is_active == True,
                )
                .first()
            )
            if not tenant_branch:
                return _reject_tenant_context(
                    "tenant_context_branch_invalid",
                    meta={
                        "tenant_branch_id": str(incoming_tenant_context.branch_id),
                    },
                )
            if resolved_branch and tenant_branch.id != resolved_branch.id:
                return _reject_tenant_context(
                    "tenant_context_branch_mismatch",
                    meta={
                        "tenant_branch_id": str(tenant_branch.id),
                        "resolved_branch_id": str(resolved_branch.id),
                    },
                )
            if not resolved_branch and branch_mode != "by_instance":
                resolved_branch = tenant_branch

    effective_instance_id = instance_id
    if resolved_branch and resolved_branch.instance_id:
        effective_instance_id = resolved_branch.instance_id
    if not effective_instance_id and incoming_tenant_context:
        effective_instance_id = incoming_tenant_context.instance_id

    tenant_source = "webhook"
    if incoming_tenant_context and incoming_tenant_context.source:
        source_value = incoming_tenant_context.source.strip()
        if source_value:
            tenant_source = source_value

    company_id = _normalize_uuid(getattr(client, "company_id", None))
    client_id = _normalize_uuid(getattr(client, "id", None))
    branch_id = _normalize_uuid(getattr(resolved_branch, "id", None)) if resolved_branch else None
    effective_tenant_context = {
        "company_id": company_id,
        "client_id": client_id,
        "client_slug": client.name,
        "source": tenant_source,
        "origin_source": incoming_tenant_context.origin_source if incoming_tenant_context else None,
        "instance_id": effective_instance_id or None,
        "branch_id": branch_id,
        "branch_slug": getattr(resolved_branch, "slug", None) if resolved_branch else None,
    }
    effective_tenant_context = {
        key: value for key, value in effective_tenant_context.items() if value is not None
    }
    _, effective_tenant_error = validate_tenant_context_contract(
        effective_tenant_context,
        require_client_id=client_id is not None,
    )
    if effective_tenant_error:
        return _reject_tenant_context(
            "tenant_context_contract_invalid",
            message="Invalid tenant_context",
            meta={"error": effective_tenant_error},
        )

    if enforce_secret:
        expected_secret = _resolve_expected_webhook_secret(
            settings=settings,
            branch=resolved_branch,
        )
        if expected_secret:
            if not _webhook_secrets_match(provided_secret, expected_secret):
                _raise_invalid_secret(
                    branch=resolved_branch,
                    instance_id=instance_id,
                    branch_mode=branch_mode,
                )
        elif not provided_secret and not missing_secret_warned:
            alert_warning(
                "Webhook secret missing",
                {
                    "client_slug": payload.client_slug,
                    "branch_id": str(resolved_branch.id) if resolved_branch else None,
                },
            )

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
            "resolved_branch_id": resolved_branch.id if resolved_branch else None,
            "resolved_knowledge_tag": resolved_branch.knowledge_tag if resolved_branch else None,
            "resolved_instance_match_mode": instance_match_mode,
            "tenant_context": effective_tenant_context,
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

    base_dir = Path(_MEDIA_STORAGE_DEFAULT_DIR).resolve()
    target_path = (base_dir / normalized_path).resolve()
    if base_dir not in target_path.parents and target_path != base_dir:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid media path")
    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    return FileResponse(target_path)


@router.post("/webhook/debug")
async def debug_webhook(request: Request):
    """Debug endpoint to see raw request."""
    raw_debug = os.environ.get("DEBUG_WEBHOOK_ENABLED")
    debug_enabled = bool(raw_debug and raw_debug.strip().lower() not in {"0", "false", "no", "off"})
    if not debug_enabled:
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
    metadata = parsed.body.metadata
    instance_id = metadata.instanceId if metadata else None
    resolved_branch = None
    if instance_id:
        resolved_branch = resolve_active_branch_by_instance(
            db,
            client_id=client.id,
            instance_id=instance_id,
        ).branch
    expected_secret = _resolve_expected_webhook_secret(
        settings=settings,
        branch=resolved_branch,
    )
    if expected_secret:
        if not _webhook_secrets_match(provided_secret, expected_secret):
            report_integration_incident(
                db,
                client=client,
                branch=resolved_branch,
                reason=REASON_INVALID_WEBHOOK_SECRET,
                source="webhook_direct",
                context={
                    "instance_id": instance_id,
                    "message_id": metadata.messageId if metadata else None,
                    "remote_jid": metadata.remoteJid if metadata else None,
                },
            )
            db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")
    elif not provided_secret:
        alert_warning("Webhook secret missing", {"client_slug": parsed.client_slug})

    preflight_response, preflight_payload = _run_preflight(
        parsed,
        db,
        provided_secret=provided_secret,
        enforce_secret=False,
        conversation_id=None,
        resolve_trace_conversation=lambda **kwargs: _resolve_secret_preflight_trace_conversation(
            db,
            **kwargs,
        ),
        record_early_trace=_record_secret_preflight_trace,
    )
    if preflight_response is not None:
        return preflight_response

    from app.routers.public_entrypoint_contract import (
        PublicEntrypointMaterializationMode,
        handle_public_webhook_payload,
    )

    return await handle_public_webhook_payload(
        parsed,
        db,
        entrypoint_name="Webhook direct",
        materialization_mode=PublicEntrypointMaterializationMode.ALLOW_UNMATERIALIZED,
        provided_secret=provided_secret,
        enforce_secret=False,
        enqueue_only=_should_enqueue_only(),
        preflight_payload=preflight_payload,
    )


@router.get("/webhook/{client_slug}")
async def handle_webhook_probe(client_slug: str):
    """Health probe for ChatFlow UI checks; real webhooks must use POST."""
    return {"ok": True, "message": "Use POST with JSON payload", "client_slug": client_slug}


@router.post("/webhook", response_model=WebhookResponse)
async def handle_webhook(payload: WebhookRequest, http_request: Request, db: Session = Depends(get_db)):
    """Handle legacy webhook wrapper (same format as ChatFlow webhook)."""
    provided_secret = _get_request_webhook_secret(http_request)
    from app.routers.public_entrypoint_contract import (
        PublicEntrypointMaterializationMode,
        handle_public_webhook_payload,
    )

    return await handle_public_webhook_payload(
        payload,
        db,
        entrypoint_name="Webhook",
        materialization_mode=PublicEntrypointMaterializationMode.ALLOW_UNMATERIALIZED,
        provided_secret=provided_secret,
        enforce_secret=True,
        enqueue_only=_should_enqueue_only(),
    )


__all__ = [
    "handle_webhook",
    "handle_webhook_direct",
    "handle_webhook_probe",
    "router",
    "serve_media",
]
