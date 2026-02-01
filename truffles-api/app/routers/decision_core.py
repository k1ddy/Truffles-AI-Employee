from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.schemas.webhook import WebhookRequest, WebhookResponse
from app.services import reasoning_core

logger = get_logger("decision_core")
router = APIRouter()


def _is_env_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _is_decision_core_enabled() -> bool:
    return _is_env_enabled(os.environ.get("DECISION_CORE_ENABLED"), default=False)


def _should_enqueue_only() -> bool:
    return _is_env_enabled(os.environ.get("WEBHOOK_ENQUEUE_ONLY"), default=False)


def _enforce_decision_token(request: Request) -> None:
    expected_token = os.environ.get("DECISION_CORE_TOKEN")
    if not expected_token:
        return
    provided_token = request.headers.get("X-Decision-Core-Token") or request.headers.get("X-Decision-Token")
    if provided_token != expected_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid decision core token")


@router.post("/decision/handle", response_model=WebhookResponse)
async def handle_decision(request: Request, db: Session = Depends(get_db)):
    if not _is_decision_core_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    _enforce_decision_token(request)

    try:
        payload_json = await request.json()
    except Exception as exc:
        logger.warning(
            "Decision core payload is not valid JSON",
            extra={"context": {"error": str(exc)}},
        )
        return WebhookResponse(success=False, message="Invalid JSON payload")

    if not isinstance(payload_json, dict):
        return WebhookResponse(success=False, message="Invalid payload format")

    try:
        payload = WebhookRequest.model_validate(payload_json)
    except ValidationError as exc:
        logger.warning(
            "Decision core validation failed",
            extra={"context": {"error": str(exc)}},
        )
        return WebhookResponse(success=False, message="Invalid webhook payload")

    return await reasoning_core.handle_webhook_payload(
        payload,
        db,
        provided_secret=None,
        enforce_secret=False,
        enqueue_only=_should_enqueue_only(),
    )


__all__ = ["handle_decision", "router"]
