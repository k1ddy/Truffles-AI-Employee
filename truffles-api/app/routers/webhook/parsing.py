"""Normalize/validate webhook payloads (payload, instanceId, metadata)."""

from __future__ import annotations

import re

from fastapi import Request
from starlette.requests import ClientDisconnect

from app.logging_config import get_logger
from app.schemas.webhook import WebhookRequest, WebhookResponse

logger = get_logger("webhook")


def _coerce_remote_jid(value) -> str | None:
    if not value or isinstance(value, (dict, list, tuple)):
        return None
    text = str(value).strip()
    if not text:
        return None
    if "@" in text:
        return text
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    return f"{digits}@s.whatsapp.net"


def _extract_tenant_context(payload: dict, body: dict) -> dict | None:
    for source in (payload, body):
        for key in ("tenant_context", "tenantContext"):
            value = source.get(key)
            if isinstance(value, dict):
                return dict(value)
    return None


def _normalize_chatflow_payload(payload: dict, client_slug: str | None) -> tuple[dict, str, dict | None]:
    body = payload.get("body")
    if not isinstance(body, dict):
        body = payload

    body = dict(body)
    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}

    candidate = payload
    remote_jid = metadata.get("remoteJid")
    if not remote_jid:
        for key in ("remoteJid", "remote_jid", "jid", "from", "chatId", "session_id", "user_id", "phone"):
            remote_jid = candidate.get(key)
            if remote_jid:
                break
    remote_jid = _coerce_remote_jid(remote_jid)
    if remote_jid:
        metadata.setdefault("remoteJid", remote_jid)

    message_id = metadata.get("messageId")
    if not message_id:
        for key in ("messageId", "message_id", "id"):
            message_id = candidate.get(key)
            if message_id:
                break

    msg_obj = candidate.get("message") if isinstance(candidate.get("message"), dict) else None
    if not message_id and msg_obj:
        message_id = msg_obj.get("id") or msg_obj.get("messageId")
    if message_id:
        metadata.setdefault("messageId", message_id)

    timestamp = metadata.get("timestamp")
    if not timestamp:
        for key in ("timestamp", "t", "time"):
            timestamp = candidate.get(key)
            if timestamp:
                break
    if timestamp:
        metadata.setdefault("timestamp", timestamp)

    sender = metadata.get("sender")
    if not sender:
        for key in ("sender", "pushName", "name"):
            sender = candidate.get(key)
            if sender:
                break
    if sender:
        metadata.setdefault("sender", sender)

    instance_id = metadata.get("instanceId") or metadata.get("instance_id")
    if not instance_id:
        for key in ("instanceId", "instance_id", "instance", "whatsapp_instance_id"):
            instance_id = candidate.get(key)
            if instance_id:
                break
    if not instance_id:
        node_data = candidate.get("nodeData") or body.get("nodeData")
        if isinstance(node_data, dict):
            for key in ("instanceId", "instance_id", "instance", "whatsapp_instance_id"):
                instance_id = node_data.get(key)
                if instance_id:
                    break
    if instance_id:
        metadata.setdefault("instanceId", instance_id)

    message = body.get("message")
    if not isinstance(message, str) or not message.strip():
        message = None
        for key in ("text", "body", "message_text", "content"):
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                message = value
                break
        if not message and msg_obj:
            for key in ("text", "body", "message", "content"):
                value = msg_obj.get(key)
                if isinstance(value, str) and value.strip():
                    message = value
                    break
    if message:
        body["message"] = message

    body["metadata"] = metadata
    tenant_context = _extract_tenant_context(payload, body)
    slug = client_slug or payload.get("client_slug") or "truffles"
    return body, slug, tenant_context


async def _parse_webhook_request(
    request: Request,
    *,
    client_slug: str | None = None,
) -> WebhookRequest | WebhookResponse:
    try:
        payload = await request.json()
    except ClientDisconnect:
        logger.info("Webhook client disconnected during read", extra={"context": {"client_slug": client_slug}})
        return WebhookResponse(success=True, message="Client disconnected")
    except Exception as exc:
        try:
            raw = await request.body()
        except ClientDisconnect:
            logger.info("Webhook client disconnected during body read", extra={"context": {"client_slug": client_slug}})
            return WebhookResponse(success=True, message="Client disconnected")
        if not raw or not raw.strip():
            logger.info("Webhook probe with empty body", extra={"context": {"client_slug": client_slug}})
            return WebhookResponse(success=True, message="Empty payload")

        logger.warning(
            "Webhook payload is not valid JSON",
            extra={
                "context": {
                    "error": str(exc),
                    "body_preview": raw[:200].decode("utf-8", "ignore"),
                }
            },
        )
        return WebhookResponse(success=False, message="Invalid JSON payload")

    if not isinstance(payload, dict):
        return WebhookResponse(success=False, message="Invalid payload format")

    body, slug, tenant_context = _normalize_chatflow_payload(payload, client_slug)

    query_instance_id = (
        request.query_params.get("instanceId")
        or request.query_params.get("instance_id")
        or request.query_params.get("instance")
    )
    tenant_context_payload = dict(tenant_context) if isinstance(tenant_context, dict) else {}
    if query_instance_id:
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
        metadata["instanceId"] = query_instance_id
        body["metadata"] = metadata
        tenant_context_payload.setdefault("instance_id", query_instance_id)
    else:
        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
        instance_id = metadata.get("instanceId") or metadata.get("instance_id")
        if instance_id:
            tenant_context_payload.setdefault("instance_id", instance_id)

    if slug:
        tenant_context_payload.setdefault("client_slug", slug)
    tenant_context_payload.setdefault("source", "webhook")

    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
    if not metadata.get("remoteJid") or not body.get("message"):
        logger.info(
            "Webhook payload missing expected fields",
            extra={
                "context": {
                    "client_slug": slug,
                    "payload_keys": list(payload.keys())[:20],
                    "body_keys": list(body.keys())[:20],
                    "metadata_keys": list(metadata.keys())[:20],
                    "has_message": bool(body.get("message")),
                }
            },
        )

    try:
        return WebhookRequest(body=body, client_slug=slug, tenant_context=tenant_context_payload)
    except Exception as exc:
        logger.warning("Webhook payload validation failed", extra={"context": {"error": str(exc)}})
        return WebhookResponse(success=False, message="Invalid webhook payload")


__all__ = ["_coerce_remote_jid", "_normalize_chatflow_payload", "_parse_webhook_request"]
