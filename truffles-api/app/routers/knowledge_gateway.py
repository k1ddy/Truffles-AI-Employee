from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.schemas.knowledge_snapshot import KnowledgeSnapshotRequest
from app.services.knowledge_snapshot_service import build_knowledge_snapshot

logger = get_logger("knowledge_gateway")
router = APIRouter()


def _is_env_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _is_snapshot_enabled() -> bool:
    return _is_env_enabled(os.environ.get("KNOWLEDGE_SNAPSHOT_ENABLED"), default=False)


def _enforce_snapshot_token(request: Request) -> None:
    expected_token = os.environ.get("KNOWLEDGE_SNAPSHOT_TOKEN")
    if not expected_token:
        return
    provided = request.headers.get("X-Knowledge-Snapshot-Token")
    if provided != expected_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid knowledge snapshot token")


@router.post("/knowledge/snapshot")
async def handle_knowledge_snapshot(
    payload: KnowledgeSnapshotRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    if not _is_snapshot_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    _enforce_snapshot_token(request)

    snapshot, error = build_knowledge_snapshot(
        db,
        tenant_context=payload.tenant_context,
        version_id=payload.version_id,
    )
    if error:
        if error in {"branch_not_found", "version_not_found"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        if error in {"client_slug_mismatch", "invalid_client_id", "invalid_branch_id", "invalid_version_id"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    logger.info(
        "Knowledge snapshot built",
        extra={"context": {"version_id": snapshot.get("version_id"), "client_id": payload.tenant_context.client_id}},
    )
    return snapshot


__all__ = ["handle_knowledge_snapshot", "router"]
