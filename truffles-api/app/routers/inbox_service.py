from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.schemas.provider_gateway import ProviderInbound
from app.services.inbox_event_service import record_inbox_event

logger = get_logger("inbox_service")
router = APIRouter()


def _is_env_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _is_inbox_enabled() -> bool:
    return _is_env_enabled(os.environ.get("INBOX_SERVICE_ENABLED"), default=False)


def _enforce_inbox_token(request: Request) -> None:
    expected_token = os.environ.get("INBOX_SERVICE_TOKEN")
    if not expected_token:
        return
    provided_token = request.headers.get("X-Inbox-Service-Token") or request.headers.get("X-Inbox-Token")
    if provided_token != expected_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid inbox service token")


@router.post("/inbox/event")
async def handle_inbox_event(request: Request, db: Session = Depends(get_db)):
    if not _is_inbox_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    _enforce_inbox_token(request)

    try:
        payload_json = await request.json()
    except Exception as exc:
        logger.warning(
            "Inbox event payload is not valid JSON",
            extra={"context": {"error": str(exc)}},
        )
        return {"success": False, "message": "Invalid JSON payload"}

    if not isinstance(payload_json, dict):
        return {"success": False, "message": "Invalid payload format"}

    try:
        payload = ProviderInbound.model_validate(payload_json)
    except ValidationError as exc:
        logger.warning(
            "Inbox event validation failed",
            extra={"context": {"error": str(exc)}},
        )
        return {"success": False, "message": "Invalid provider inbound payload"}

    ok, result = record_inbox_event(db, payload=payload, raw_payload=payload_json)
    if ok:
        return {"success": True, "event_id": result}
    if result == "duplicate":
        return {"success": True, "message": "duplicate"}
    return {"success": False, "message": result}


__all__ = ["handle_inbox_event", "router"]
