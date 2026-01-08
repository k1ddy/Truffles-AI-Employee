"""Webhook secret helpers."""

from __future__ import annotations

from fastapi import Request

from app.models import ClientSettings


def _get_client_webhook_secret(settings: ClientSettings | None) -> str | None:
    if not settings:
        return None
    secret = getattr(settings, "webhook_secret", None)
    if not secret:
        return None
    cleaned = str(secret).strip()
    return cleaned or None


def _get_request_webhook_secret(request: Request) -> str | None:
    header_secret = request.headers.get("X-Webhook-Secret")
    if header_secret:
        return header_secret.strip()
    query_secret = request.query_params.get("webhook_secret")
    if query_secret:
        return query_secret.strip()
    return None


__all__ = ["_get_client_webhook_secret", "_get_request_webhook_secret"]
