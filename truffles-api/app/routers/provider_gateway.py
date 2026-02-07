from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.schemas.provider_gateway import ProviderInbound, ProviderStatus
from app.schemas.webhook import WebhookResponse
from app.services import reasoning_core
from app.services.inbox_event_service import record_inbox_event
from app.services.provider_gateway_service import translate_provider_inbound, update_outbox_status_from_provider
from app.services.tenant_context_contract import validate_tenant_context_contract

logger = get_logger("provider_gateway")
router = APIRouter()


def _is_env_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _is_provider_inbound_enabled() -> bool:
    return _is_env_enabled(os.environ.get("PROVIDER_GATEWAY_INBOUND_ENABLED"), default=False)


def _is_provider_status_enabled() -> bool:
    return _is_env_enabled(os.environ.get("PROVIDER_GATEWAY_STATUS_ENABLED"), default=False)


def _is_provider_inbox_enabled() -> bool:
    return _is_env_enabled(os.environ.get("PROVIDER_GATEWAY_INBOX_ENABLED"), default=False)


def _is_provider_inbox_required() -> bool:
    return _is_env_enabled(os.environ.get("PROVIDER_GATEWAY_INBOX_REQUIRED"), default=False)


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

    _, tenant_error = validate_tenant_context_contract(
        payload.tenant_context.model_dump(exclude_none=True, mode="json")
    )
    if tenant_error:
        logger.warning(
            "Provider inbound tenant_context contract validation failed",
            extra={"context": {"error": tenant_error}},
        )
        return WebhookResponse(success=False, message="Invalid tenant_context contract")

    if _is_provider_inbox_enabled():
        ok, result = record_inbox_event(db, payload=payload, raw_payload=payload_json)
        if not ok and result != "duplicate":
            logger.warning(
                "Provider inbox event record failed",
                extra={"context": {"error": result}},
            )
            if _is_provider_inbox_required():
                return WebhookResponse(success=False, message=f"inbox_event:{result}")

    webhook_payload, error = translate_provider_inbound(payload)
    if error:
        return WebhookResponse(success=False, message=error)

    return await reasoning_core.handle_webhook_payload(
        webhook_payload,
        db,
        provided_secret=None,
        enforce_secret=False,
    )


@router.post("/provider/status")
async def handle_provider_status(request: Request, db: Session = Depends(get_db)):
    if not _is_provider_status_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    _enforce_gateway_token(request)

    try:
        payload_json = await request.json()
    except Exception as exc:
        logger.warning(
            "Provider status payload is not valid JSON",
            extra={"context": {"error": str(exc)}},
        )
        return {"success": False, "message": "Invalid JSON payload"}

    if not isinstance(payload_json, dict):
        return {"success": False, "message": "Invalid payload format"}

    try:
        payload = ProviderStatus.model_validate(payload_json)
    except ValidationError as exc:
        logger.warning(
            "Provider status validation failed",
            extra={"context": {"error": str(exc)}},
        )
        return {"success": False, "message": "Invalid provider status payload"}

    _, tenant_error = validate_tenant_context_contract(
        payload.tenant_context.model_dump(exclude_none=True, mode="json")
    )
    if tenant_error:
        logger.warning(
            "Provider status tenant_context contract validation failed",
            extra={"context": {"error": tenant_error}},
        )
        return {"success": False, "message": "Invalid tenant_context contract"}

    ok, message = update_outbox_status_from_provider(db, status=payload)
    if not ok:
        status_code = status.HTTP_400_BAD_REQUEST
        if message == "outbox_not_found":
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=message)

    return {"success": True, "message": "ok"}


__all__ = ["handle_provider_inbound", "handle_provider_status", "router"]
