"""Webhook secret helpers."""

from __future__ import annotations

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


__all__ = [
    "_get_branch_webhook_secret",
    "_get_client_webhook_secret",
    "_get_request_webhook_secret",
    "_resolve_expected_webhook_secret",
]
