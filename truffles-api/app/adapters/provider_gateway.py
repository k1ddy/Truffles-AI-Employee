from __future__ import annotations

import os
from typing import Any

import httpx

from app.contracts import Err, ErrorCodes, IntegrationError, Ok, Result
from app.ports.messaging import MessageOptions, MessageSent, MessagingPort
from app.services.provider_gateway_service import build_provider_outbound_payload


class ProviderGatewayAdapter(MessagingPort):
    """Adapter for Provider Gateway outbound."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        timeout_seconds: float | None = None,
        provider: str | None = None,
        channel: str | None = None,
        callback_url: str | None = None,
    ) -> None:
        self.base_url = base_url or os.environ.get("PROVIDER_GATEWAY_OUTBOUND_URL")
        self.token = token or os.environ.get("PROVIDER_GATEWAY_TOKEN")
        self.timeout_seconds = timeout_seconds or float(
            os.environ.get("PROVIDER_GATEWAY_OUTBOUND_TIMEOUT_SECONDS", "5")
        )
        self.provider = provider or os.environ.get("PROVIDER_GATEWAY_PROVIDER", "chatflow")
        self.channel = channel or os.environ.get("PROVIDER_GATEWAY_CHANNEL", "whatsapp")
        self.callback_url = callback_url or os.environ.get("PROVIDER_GATEWAY_STATUS_CALLBACK_URL")

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-Provider-Gateway-Token"] = self.token
        return headers

    def send_text(self, to: str, text: str, options: MessageOptions) -> Result[MessageSent]:
        if not self.base_url:
            return Err(
                IntegrationError(
                    code=ErrorCodes.CONFIG_MISSING,
                    message="provider_gateway outbound url missing",
                    service="provider_gateway",
                )
            )

        outbox_id = options.extra.get("outbox_id")
        tenant_context = options.extra.get("tenant_context")
        provider = options.extra.get("provider") or self.provider
        channel = options.extra.get("channel") or self.channel
        callback_url = options.extra.get("callback_url") or self.callback_url
        idempotency_key = options.idempotency_key or ""

        payload, error = build_provider_outbound_payload(
            outbox_id=str(outbox_id) if outbox_id else "",
            provider=provider,
            channel=channel,
            tenant_context=tenant_context,
            remote_jid=to,
            text=text,
            idempotency_key=idempotency_key,
            callback_url=callback_url,
            metadata=options.extra.get("metadata") if isinstance(options.extra, dict) else None,
        )
        if error:
            return Err(
                IntegrationError(
                    code=ErrorCodes.INVALID_PAYLOAD,
                    message=f"provider_gateway outbound invalid: {error}",
                    service="provider_gateway",
                )
            )

        try:
            response = httpx.post(
                self.base_url,
                json=payload,
                headers=self._build_headers(),
                timeout=self.timeout_seconds,
            )
        except Exception as exc:
            return Err(
                IntegrationError(
                    code=ErrorCodes.CHATFLOW_ERROR,
                    message=f"provider_gateway outbound failed: {exc}",
                    service="provider_gateway",
                )
            )

        if response.status_code >= 400:
            return Err(
                IntegrationError(
                    code=ErrorCodes.CHATFLOW_ERROR,
                    message=f"provider_gateway outbound http {response.status_code}",
                    service="provider_gateway",
                    context={"status_code": response.status_code},
                )
            )

        message_id = None
        provider_response: dict[str, Any] = {}
        try:
            provider_response = response.json()
            message_id = (
                provider_response.get("provider_message_id")
                or provider_response.get("message_id")
                or provider_response.get("id")
            )
        except Exception:
            provider_response = {}

        return Ok(
            MessageSent(
                remote_jid=to,
                message_id=message_id or options.idempotency_key,
                provider_response=provider_response,
            )
        )

    def send_media(self, to: str, media_url: str, media_type: str, options: MessageOptions) -> Result[MessageSent]:
        if not self.base_url:
            return Err(
                IntegrationError(
                    code=ErrorCodes.CONFIG_MISSING,
                    message="provider_gateway outbound url missing",
                    service="provider_gateway",
                )
            )
        if not media_url or not media_type:
            return Err(
                IntegrationError(
                    code=ErrorCodes.INVALID_PAYLOAD,
                    message="provider_gateway media missing",
                    service="provider_gateway",
                    context={"media_type": media_type},
                )
            )

        outbox_id = options.extra.get("outbox_id")
        tenant_context = options.extra.get("tenant_context")
        provider = options.extra.get("provider") or self.provider
        channel = options.extra.get("channel") or self.channel
        callback_url = options.extra.get("callback_url") or self.callback_url
        idempotency_key = options.idempotency_key or ""
        media_meta = options.extra.get("media_meta") if isinstance(options.extra, dict) else None
        media_payload: dict[str, Any] = {"media_type": media_type}
        if isinstance(media_meta, dict):
            media_payload.update(media_meta)
        if "signed_url" not in media_payload and "source_url" not in media_payload:
            media_payload["signed_url"] = media_url
        if options.caption and "caption" not in media_payload:
            media_payload["caption"] = options.caption

        payload, error = build_provider_outbound_payload(
            outbox_id=str(outbox_id) if outbox_id else "",
            provider=provider,
            channel=channel,
            tenant_context=tenant_context,
            remote_jid=to,
            text=None,
            media=media_payload,
            idempotency_key=idempotency_key,
            callback_url=callback_url,
            metadata=options.extra.get("metadata") if isinstance(options.extra, dict) else None,
        )
        if error:
            return Err(
                IntegrationError(
                    code=ErrorCodes.INVALID_PAYLOAD,
                    message=f"provider_gateway outbound invalid: {error}",
                    service="provider_gateway",
                )
            )

        try:
            response = httpx.post(
                self.base_url,
                json=payload,
                headers=self._build_headers(),
                timeout=self.timeout_seconds,
            )
        except Exception as exc:
            return Err(
                IntegrationError(
                    code=ErrorCodes.CHATFLOW_ERROR,
                    message=f"provider_gateway outbound failed: {exc}",
                    service="provider_gateway",
                )
            )

        if response.status_code >= 400:
            return Err(
                IntegrationError(
                    code=ErrorCodes.CHATFLOW_ERROR,
                    message=f"provider_gateway outbound http {response.status_code}",
                    service="provider_gateway",
                    context={"status_code": response.status_code},
                )
            )

        message_id = None
        provider_response: dict[str, Any] = {}
        try:
            provider_response = response.json()
            message_id = (
                provider_response.get("provider_message_id")
                or provider_response.get("message_id")
                or provider_response.get("id")
            )
        except Exception:
            provider_response = {}

        return Ok(
            MessageSent(
                remote_jid=to,
                message_id=message_id or options.idempotency_key,
                provider_response=provider_response,
            )
        )
