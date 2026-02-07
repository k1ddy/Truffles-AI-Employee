from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from app.models import OutboxMessage
from app.schemas.outbox_payload import TenantContext
from app.schemas.provider_gateway import (
    ProviderInbound,
    ProviderOutbound,
    ProviderOutboundContent,
    ProviderOutboundMedia,
    ProviderOutboundRecipient,
    ProviderParticipant,
    ProviderStatus,
)
from app.schemas.webhook import WebhookBody, WebhookMetadata, WebhookRequest
from app.services.tenant_context_contract import validate_tenant_context_contract


def _coerce_remote_jid(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if "@" in text:
        return text
    digits = "".join(char for char in text if char.isdigit())
    if not digits:
        return None
    return f"{digits}@s.whatsapp.net"


def _resolve_remote_jid(sender: ProviderParticipant) -> str | None:
    for candidate in (sender.jid, sender.phone, sender.id):
        remote_jid = _coerce_remote_jid(candidate)
        if remote_jid:
            return remote_jid
    return None


def _parse_received_at(value: str | None) -> int | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())


def _extract_signed_url_expires_at(signed_url: str) -> str | None:
    if not signed_url:
        return None
    try:
        parsed = urlparse(signed_url)
        expires_values = parse_qs(parsed.query or "").get("expires")
        if not expires_values:
            return None
        expires = int(expires_values[0])
        return datetime.fromtimestamp(expires, tz=timezone.utc).isoformat()
    except Exception:
        return None


def translate_provider_inbound(payload: ProviderInbound) -> tuple[WebhookRequest | None, str | None]:
    tenant_context = payload.tenant_context
    client_slug = (tenant_context.client_slug or "").strip()
    if not client_slug:
        return None, "client_slug_required"

    message_type = (payload.message.type or "").strip().lower()
    if message_type != "text":
        return None, "unsupported_message_type"

    message_text = (payload.message.text or "").strip()
    if not message_text:
        return None, "missing_text"

    if payload.message.media or payload.message.payload:
        return None, "media_not_supported"

    remote_jid = _resolve_remote_jid(payload.sender)
    if not remote_jid:
        return None, "missing_remote_jid"

    timestamp = _parse_received_at(payload.received_at)
    if timestamp is None:
        return None, "invalid_received_at"

    metadata = WebhookMetadata(
        remoteJid=remote_jid,
        messageId=payload.provider_message_id,
        timestamp=timestamp,
        sender=payload.sender.display_name or payload.sender.id,
        instanceId=tenant_context.instance_id,
    )
    body = WebhookBody(
        messageType="text",
        message=message_text,
        metadata=metadata,
    )
    webhook_tenant_context = tenant_context.model_dump(exclude_none=True, mode="json")
    webhook_tenant_context.setdefault("source", "system")
    return WebhookRequest(
        body=body,
        client_slug=client_slug,
        tenant_context=webhook_tenant_context,
    ), None


def build_provider_outbound_payload(
    *,
    outbox_id: str,
    provider: str,
    channel: str,
    tenant_context: dict[str, Any] | TenantContext | None,
    remote_jid: str,
    text: str | None,
    media: dict[str, Any] | None = None,
    idempotency_key: str,
    callback_url: str | None,
    metadata: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    if not tenant_context:
        return None, "missing_tenant_context"
    if not remote_jid:
        return None, "missing_remote_jid"
    if not text and not media:
        return None, "missing_content"
    if not outbox_id:
        return None, "missing_outbox_id"
    if not idempotency_key:
        return None, "missing_idempotency_key"

    if not isinstance(tenant_context, TenantContext):
        try:
            tenant_context = TenantContext.model_validate(tenant_context)
        except Exception:
            return None, "invalid_tenant_context"
    _, tenant_error = validate_tenant_context_contract(
        tenant_context.model_dump(exclude_none=True, mode="json")
    )
    if tenant_error:
        return None, "invalid_tenant_context_contract"

    media_payload = None
    if media:
        try:
            media_payload = ProviderOutboundMedia.model_validate(media)
        except Exception:
            return None, "invalid_media"
        if not media_payload.signed_url:
            return None, "missing_media_signed_url"
        if not media_payload.expires_at:
            expires_at = _extract_signed_url_expires_at(media_payload.signed_url)
            if not expires_at:
                return None, "missing_media_expires_at"
            media_payload = media_payload.model_copy(update={"expires_at": expires_at})
    content = ProviderOutboundContent(
        text=text if text else None,
        media=media_payload,
    )
    if not content.text and not content.media:
        return None, "missing_content"

    outbound = ProviderOutbound(
        outbox_id=outbox_id,
        provider=provider,
        channel=channel,
        tenant_context=tenant_context,
        to=ProviderOutboundRecipient(jid=remote_jid),
        content=content,
        idempotency_key=idempotency_key,
        callback_url=callback_url,
        requested_at=datetime.now(timezone.utc).isoformat(),
        metadata=metadata,
    )
    return outbound.model_dump(exclude_none=True, mode="json"), None


def _merge_dict(base: dict, updates: dict) -> dict:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = {**base[key], **value}
        else:
            base[key] = value
    return base


def update_outbox_status_from_provider(
    db,
    *,
    status: ProviderStatus,
) -> tuple[bool, str]:
    if not status.outbox_id:
        return False, "missing_outbox_id"
    try:
        outbox_uuid = UUID(status.outbox_id)
    except (TypeError, ValueError):
        return False, "invalid_outbox_id"

    outbox = db.query(OutboxMessage).filter(OutboxMessage.id == outbox_uuid).first()
    if not outbox:
        return False, "outbox_not_found"

    tenant_context = status.tenant_context
    if tenant_context and tenant_context.client_id and outbox.client_id != tenant_context.client_id:
        return False, "tenant_mismatch"
    if outbox.branch_id and tenant_context and tenant_context.branch_id:
        if outbox.branch_id != tenant_context.branch_id:
            return False, "tenant_mismatch"

    meta = dict(outbox.meta or {})
    status_meta = {
        "provider": status.provider,
        "channel": status.channel,
        "provider_message_id": status.provider_message_id,
        "status": status.status,
        "status_at": status.status_at,
    }
    if status.error_code:
        status_meta["error_code"] = status.error_code
    if status.error_message:
        status_meta["error_message"] = status.error_message
    if status.raw_ref:
        status_meta["raw_ref"] = status.raw_ref
    if status.extensions:
        status_meta["extensions"] = status.extensions

    meta = _merge_dict(meta, {"provider_status": status_meta})
    outbox.meta = meta

    if status.status in {"failed", "rejected"}:
        outbox.status = "FAILED"
        outbox.last_error = status.error_message or status.error_code or "provider_failed"
    elif status.status in {"queued", "sent", "delivered", "read"}:
        if outbox.status != "FAILED":
            outbox.status = "SENT"

    outbox.updated_at = datetime.now(timezone.utc)
    db.commit()
    return True, "ok"
