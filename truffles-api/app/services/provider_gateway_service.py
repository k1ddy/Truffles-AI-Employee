from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.provider_gateway import ProviderInbound, ProviderParticipant
from app.schemas.webhook import WebhookBody, WebhookMetadata, WebhookRequest


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
    return WebhookRequest(body=body, client_slug=client_slug), None
