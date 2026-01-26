from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.routers.webhook import _legacy as legacy
from app.schemas.provider_gateway import ProviderInbound
from app.schemas.webhook import WebhookResponse
from app.services.provider_gateway_service import translate_provider_inbound

logger = get_logger("provider_gateway")
router = APIRouter()


def _is_env_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _is_provider_inbound_enabled() -> bool:
    return _is_env_enabled(os.environ.get("PROVIDER_GATEWAY_INBOUND_ENABLED"), default=False)


def _enforce_gateway_token(request: Request) -> None:
    expected_token = os.environ.get("PROVIDER_GATEWAY_TOKEN")
    if not expected_token:
        return
    provided_token = request.headers.get("X-Provider-Gateway-Token") or request.headers.get("X-Provider-Token")
    if provided_token != expected_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid provider gateway token")


@router.post("/provider/inbound", response_model=WebhookResponse)
async def handle_provider_inbound(request: Request, db: Session = Depends(get_db)):
    if not _is_provider_inbound_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    _enforce_gateway_token(request)

    try:
        payload_json = await request.json()
    except Exception as exc:
        logger.warning(
            "Provider inbound payload is not valid JSON",
            extra={"context": {"error": str(exc)}},
        )
        return WebhookResponse(success=False, message="Invalid JSON payload")

    if not isinstance(payload_json, dict):
        return WebhookResponse(success=False, message="Invalid payload format")

    try:
        payload = ProviderInbound.model_validate(payload_json)
    except ValidationError as exc:
        logger.warning(
            "Provider inbound validation failed",
            extra={"context": {"error": str(exc)}},
        )
        return WebhookResponse(success=False, message="Invalid provider inbound payload")

    webhook_payload, error = translate_provider_inbound(payload)
    if error:
        return WebhookResponse(success=False, message=error)

    return await legacy._handle_webhook_payload(
        webhook_payload,
        db,
        provided_secret=None,
        enforce_secret=False,
    )


__all__ = ["handle_provider_inbound", "router"]
