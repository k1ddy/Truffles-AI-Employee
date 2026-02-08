from __future__ import annotations

import hashlib
import hmac
import os

_WEBHOOK_SECRET_PREFIX = "whs_v1_"
_DEFAULT_WEBHOOK_SECRET_SALT = "truffles-webhook-secret-v1"


def _normalize_required_text(value: str | None, field: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError(f"{field} is required")
    return cleaned


def get_webhook_secret_salt() -> str:
    return (
        os.environ.get("WEBHOOK_SECRET_PEPPER")
        or os.environ.get("SECRET_KEY")
        or _DEFAULT_WEBHOOK_SECRET_SALT
    )


def derive_webhook_secret_from_instance(instance_id: str) -> str:
    normalized_instance = _normalize_required_text(instance_id, "instance_id")
    digest = hmac.new(
        get_webhook_secret_salt().encode("utf-8"),
        normalized_instance.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{_WEBHOOK_SECRET_PREFIX}{digest[:40]}"


__all__ = [
    "derive_webhook_secret_from_instance",
    "get_webhook_secret_salt",
]
