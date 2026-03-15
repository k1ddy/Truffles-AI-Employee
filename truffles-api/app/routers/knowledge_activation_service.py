from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.knowledge_registry_service import (
    KNOWLEDGE_ACTIVATION_STUCK_AFTER_SECONDS,
    process_queued_knowledge_activation_jobs,
)

router = APIRouter()


def _is_env_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _is_knowledge_activation_enabled() -> bool:
    return _is_env_enabled(os.environ.get("KNOWLEDGE_ACTIVATION_SERVICE_ENABLED"), default=False)


def _enforce_service_token(request: Request) -> None:
    expected_token = os.environ.get("KNOWLEDGE_ACTIVATION_SERVICE_TOKEN")
    if not expected_token:
        return
    provided_token = (
        request.headers.get("X-Knowledge-Activation-Service-Token")
        or request.headers.get("X-Knowledge-Activation-Token")
    )
    if provided_token != expected_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid knowledge activation service token")


@router.post("/knowledge-activation/process")
async def process_knowledge_activation(request: Request, db: Session = Depends(get_db)):
    if not _is_knowledge_activation_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    _enforce_service_token(request)

    limit = int(os.environ.get("KNOWLEDGE_ACTIVATION_PROCESS_LIMIT", "10"))
    stuck_after_seconds = int(
        float(
            os.environ.get(
                "KNOWLEDGE_ACTIVATION_STUCK_AFTER_SECONDS",
                str(KNOWLEDGE_ACTIVATION_STUCK_AFTER_SECONDS),
            )
        )
    )
    return process_queued_knowledge_activation_jobs(
        db,
        limit=limit,
        stuck_after_seconds=max(stuck_after_seconds, 1),
    )


__all__ = ["process_knowledge_activation", "router"]
