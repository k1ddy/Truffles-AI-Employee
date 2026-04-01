from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.services.outbox_runtime_service import run_default_outbox_process

logger = get_logger("outbox_service")
router = APIRouter()


def _is_env_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _is_outbox_enabled() -> bool:
    return _is_env_enabled(os.environ.get("OUTBOX_SERVICE_ENABLED"), default=False)


def _enforce_outbox_token(request: Request) -> None:
    expected_token = os.environ.get("OUTBOX_SERVICE_TOKEN")
    if not expected_token:
        return
    provided_token = request.headers.get("X-Outbox-Service-Token") or request.headers.get("X-Outbox-Token")
    if provided_token != expected_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid outbox service token")


@router.post("/outbox/process")
async def process_outbox(request: Request, db: Session = Depends(get_db)):
    if not _is_outbox_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    _enforce_outbox_token(request)
    return await run_default_outbox_process(db, include_reminders=True)


__all__ = ["process_outbox", "router"]
