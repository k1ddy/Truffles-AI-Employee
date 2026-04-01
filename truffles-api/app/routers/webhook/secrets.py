"""Webhook secret helpers."""

from __future__ import annotations

import hmac

from fastapi import Request

from app.models import Branch, ClientSettings


def _clean_secret(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _get_client_webhook_secret(settings: ClientSettings | None) -> str | None:
    if not settings:
        return None
    return _clean_secret(getattr(settings, "webhook_secret", None))


def _get_branch_webhook_secret(branch: Branch | None) -> str | None:
    if not branch:
        return None
    return _clean_secret(getattr(branch, "webhook_secret", None))


def _resolve_expected_webhook_secret(
    *,
    settings: ClientSettings | None,
    branch: Branch | None,
) -> str | None:
    branch_secret = _get_branch_webhook_secret(branch)
    if branch_secret:
        return branch_secret
    return _get_client_webhook_secret(settings)


def _get_request_webhook_secret(request: Request) -> str | None:
    header_secret = request.headers.get("X-Webhook-Secret")
    if header_secret:
        return header_secret.strip()
    query_secret = request.query_params.get("webhook_secret")
    if query_secret:
        return query_secret.strip()
    return None


def _webhook_secrets_match(provided_secret: str | None, expected_secret: str | None) -> bool:
    provided = _clean_secret(provided_secret)
    expected = _clean_secret(expected_secret)
    if expected is None:
        return provided is None
    if provided is None:
        return False
    return hmac.compare_digest(provided, expected)


__all__ = [
    "_get_branch_webhook_secret",
    "_get_client_webhook_secret",
    "_get_request_webhook_secret",
    "_resolve_expected_webhook_secret",
    "_webhook_secrets_match",
]
