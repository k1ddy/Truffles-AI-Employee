"""Admin API endpoints for managing bot configuration."""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import get_logger
from app.models import Client, ClientSettings, Prompt
from app.schemas.webhook import WebhookRequest
from app.services.health_service import check_and_heal_conversations, get_system_health
from app.services.outbox_service import claim_pending_outbox_batches, mark_outbox_status

router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger("outbox")

ALLOWED_BRANCH_MODES = {"by_instance", "ask_user", "hybrid"}
ALLOWED_MANAGER_SCOPES = {"branch", "global"}
ALLOWED_AUTO_APPROVE_ROLES = {"owner", "admin", "manager", "support"}


# === SCHEMAS ===


class PromptUpdate(BaseModel):
    text: str


class PromptResponse(BaseModel):
    client_slug: str
    name: str
    text: str


class SettingsUpdate(BaseModel):
    mute_duration_first_minutes: Optional[int] = None
    mute_duration_second_hours: Optional[int] = None
    reminder_1_minutes: Optional[int] = None
    reminder_2_minutes: Optional[int] = None
    branch_resolution_mode: Optional[str] = None
    remember_branch_preference: Optional[bool] = None
    manager_scope: Optional[str] = None
    require_branch_for_pricing: Optional[bool] = None
    auto_approve_roles: Optional[list[str]] = None

    @field_validator("auto_approve_roles", mode="before")
    @classmethod
    def normalize_auto_approve_roles(cls, value: object) -> Optional[list[str]]:
        if value is None:
            return None
        if isinstance(value, str):
            items = [item.strip() for item in value.split(",")]
        elif isinstance(value, list):
            items = [str(item).strip() for item in value]
        else:
            raise ValueError("auto_approve_roles must be a list or comma-separated string")

        normalized: list[str] = []
        seen: set[str] = set()
        for item in items:
            if not item:
                continue
            role = item.lower()
            if role in seen:
                continue
            normalized.append(role)
            seen.add(role)
        return normalized


class VersionResponse(BaseModel):
    version: str
    git_commit: Optional[str] = None
    build_time: Optional[str] = None


# === PROMPT ENDPOINTS ===


def _require_admin_token(provided: Optional[str]) -> None:
    expected = os.environ.get("ALERTS_ADMIN_TOKEN")
    if not expected:
        raise HTTPException(status_code=500, detail="ALERTS_ADMIN_TOKEN not configured")
    if not provided or provided != expected:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.get("/prompt/{client_slug}")
async def get_prompt(client_slug: str, db: Session = Depends(get_db)) -> PromptResponse:
    """Get current system prompt for client."""
    client = db.query(Client).filter(Client.name == client_slug).first()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{client_slug}' not found")

    prompt = (
        db.query(Prompt)
        .filter(Prompt.client_id == client.id, Prompt.name == "system", Prompt.is_active == True)
        .first()
    )

    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt not found for '{client_slug}'")

    return PromptResponse(client_slug=client_slug, name="system", text=prompt.text)


@router.put("/prompt/{client_slug}")
async def update_prompt(client_slug: str, data: PromptUpdate, db: Session = Depends(get_db)) -> PromptResponse:
    """Update system prompt for client.

    Validation:
    - Client must exist
    - Prompt text must not be empty
    - Prompt text must be < 10000 chars
    """
    # Validation
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=400, detail="Prompt text cannot be empty")

    if len(data.text) > 10000:
        raise HTTPException(status_code=400, detail="Prompt text too long (max 10000 chars)")

    # Find client
    client = db.query(Client).filter(Client.name == client_slug).first()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{client_slug}' not found")

    # Find or create prompt
    prompt = db.query(Prompt).filter(Prompt.client_id == client.id, Prompt.name == "system").first()

    if prompt:
        prompt.text = data.text.strip()
        prompt.is_active = True
    else:
        prompt = Prompt(client_id=client.id, name="system", text=data.text.strip(), is_active=True)
        db.add(prompt)

    db.commit()

    return PromptResponse(client_slug=client_slug, name="system", text=prompt.text)


# === SETTINGS ENDPOINTS ===


@router.get("/settings/{client_slug}")
async def get_settings(client_slug: str, db: Session = Depends(get_db)):
    """Get client settings."""
    client = db.query(Client).filter(Client.name == client_slug).first()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{client_slug}' not found")

    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client.id).first()

    auto_approve_roles = None
    if settings and settings.auto_approve_roles is not None:
        auto_approve_roles = [
            role.strip().lower()
            for role in settings.auto_approve_roles.split(",")
            if role.strip()
        ]
    if auto_approve_roles is None:
        auto_approve_roles = ["owner", "admin"]

    return {
        "client_slug": client_slug,
        "mute_duration_first_minutes": (
            settings.mute_duration_first_minutes
            if settings and settings.mute_duration_first_minutes is not None
            else 30
        ),
        "mute_duration_second_hours": (
            settings.mute_duration_second_hours
            if settings and settings.mute_duration_second_hours is not None
            else 24
        ),
        "reminder_1_minutes": (
            settings.reminder_timeout_1
            if settings and settings.reminder_timeout_1 is not None
            else 30
        ),
        "reminder_2_minutes": (
            settings.reminder_timeout_2
            if settings and settings.reminder_timeout_2 is not None
            else 60
        ),
        "branch_resolution_mode": (
            settings.branch_resolution_mode
            if settings and settings.branch_resolution_mode
            else "hybrid"
        ),
        "remember_branch_preference": (
            settings.remember_branch_preference
            if settings and settings.remember_branch_preference is not None
            else True
        ),
        "manager_scope": (
            settings.manager_scope if settings and settings.manager_scope else "branch"
        ),
        "require_branch_for_pricing": (
            settings.require_branch_for_pricing
            if settings and settings.require_branch_for_pricing is not None
            else True
        ),
        "auto_approve_roles": auto_approve_roles,
    }


@router.put("/settings/{client_slug}")
async def update_settings(client_slug: str, data: SettingsUpdate, db: Session = Depends(get_db)):
    """Update client settings.

    Validation:
    - mute_duration_first_minutes: 1-120
    - mute_duration_second_hours: 1-72
    - reminder_1_minutes: 5-60
    - reminder_2_minutes: 30-180
    - branch_resolution_mode: by_instance/ask_user/hybrid
    - manager_scope: branch/global
    - auto_approve_roles: owner/admin/manager/support
    """
    # Find client
    client = db.query(Client).filter(Client.name == client_slug).first()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{client_slug}' not found")

    # Validation
    if data.mute_duration_first_minutes is not None:
        if not 1 <= data.mute_duration_first_minutes <= 120:
            raise HTTPException(status_code=400, detail="mute_duration_first_minutes must be 1-120")

    if data.mute_duration_second_hours is not None:
        if not 1 <= data.mute_duration_second_hours <= 72:
            raise HTTPException(status_code=400, detail="mute_duration_second_hours must be 1-72")

    if data.reminder_1_minutes is not None:
        if not 5 <= data.reminder_1_minutes <= 60:
            raise HTTPException(status_code=400, detail="reminder_1_minutes must be 5-60")

    if data.reminder_2_minutes is not None:
        if not 30 <= data.reminder_2_minutes <= 180:
            raise HTTPException(status_code=400, detail="reminder_2_minutes must be 30-180")

    if data.branch_resolution_mode is not None:
        if data.branch_resolution_mode not in ALLOWED_BRANCH_MODES:
            raise HTTPException(
                status_code=400,
                detail="branch_resolution_mode must be by_instance, ask_user, or hybrid",
            )

    if data.manager_scope is not None:
        if data.manager_scope not in ALLOWED_MANAGER_SCOPES:
            raise HTTPException(status_code=400, detail="manager_scope must be branch or global")

    if data.auto_approve_roles is not None:
        unknown_roles = [
            role for role in data.auto_approve_roles if role not in ALLOWED_AUTO_APPROVE_ROLES
        ]
        if unknown_roles:
            raise HTTPException(
                status_code=400,
                detail=f"auto_approve_roles invalid: {', '.join(unknown_roles)}",
            )

    # Find or create settings
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client.id).first()

    if not settings:
        settings = ClientSettings(client_id=client.id)
        db.add(settings)

    # Update only provided fields
    if data.mute_duration_first_minutes is not None:
        settings.mute_duration_first_minutes = data.mute_duration_first_minutes
    if data.mute_duration_second_hours is not None:
        settings.mute_duration_second_hours = data.mute_duration_second_hours
    if data.reminder_1_minutes is not None:
        settings.reminder_timeout_1 = data.reminder_1_minutes
    if data.reminder_2_minutes is not None:
        settings.reminder_timeout_2 = data.reminder_2_minutes
    if data.branch_resolution_mode is not None:
        settings.branch_resolution_mode = data.branch_resolution_mode
    if data.remember_branch_preference is not None:
        settings.remember_branch_preference = data.remember_branch_preference
    if data.manager_scope is not None:
        settings.manager_scope = data.manager_scope
    if data.require_branch_for_pricing is not None:
        settings.require_branch_for_pricing = data.require_branch_for_pricing
    if data.auto_approve_roles is not None:
        settings.auto_approve_roles = ",".join(data.auto_approve_roles)

    db.commit()

    return await get_settings(client_slug, db)


# === OUTBOX ENDPOINTS ===


@router.post("/outbox/process")
async def process_outbox(
    db: Session = Depends(get_db),
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _require_admin_token(x_admin_token)
    limit = int(os.environ.get("OUTBOX_PROCESS_LIMIT", "10"))
    idle_seconds = int(float(os.environ.get("OUTBOX_COALESCE_SECONDS", "8")))
    max_attempts = int(os.environ.get("OUTBOX_MAX_ATTEMPTS", "5"))
    retry_backoff_seconds = float(os.environ.get("OUTBOX_RETRY_BACKOFF_SECONDS", "2"))
    rows = claim_pending_outbox_batches(db, limit=limit, idle_seconds=idle_seconds)
    results = {"claimed": len(rows), "sent": 0, "failed": 0, "retry_scheduled": 0}

    if not rows:
        return results

    from app.routers.webhook import _handle_webhook_payload

    batches: dict[str, list[dict]] = {}
    for row in rows:
        conversation_id = row.get("conversation_id")
        if not conversation_id:
            continue
        batches.setdefault(str(conversation_id), []).append(row)

    for conversation_id, batch in batches.items():
        batch_sorted = sorted(
            batch,
            key=lambda r: r.get("created_at")
            if isinstance(r.get("created_at"), datetime)
            else datetime.min.replace(tzinfo=timezone.utc),
        )
        outbox_ids = [row.get("id") for row in batch_sorted]
        message_texts = []
        for row in batch_sorted:
            payload_json = row.get("payload_json") or {}
            try:
                payload = WebhookRequest.model_validate(payload_json)
            except Exception:
                continue
            text = payload.body.message or ""
            if text.strip():
                message_texts.append(text.strip())

        combined_text = " ".join(message_texts).strip()
        base_payload = WebhookRequest.model_validate(batch_sorted[-1].get("payload_json") or {})
        if combined_text:
            base_payload.body.message = combined_text

        logger.info(
            "Outbox processing start",
            extra={
                "context": {
                    "outbox_ids": [str(oid) for oid in outbox_ids if oid],
                    "conversation_id": conversation_id,
                    "attempts": batch_sorted[-1].get("attempts"),
                    "coalesced_count": len(batch_sorted),
                }
            },
        )

        try:
            response = await _handle_webhook_payload(
                base_payload,
                db,
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=UUID(conversation_id),
            )
            if not response.success:
                raise RuntimeError(response.message)
            for outbox_id in outbox_ids:
                if outbox_id:
                    mark_outbox_status(
                        db,
                        outbox_id=outbox_id,
                        status="SENT",
                        last_error=None,
                        next_attempt_at=None,
                    )
            results["sent"] += len(outbox_ids)
            logger.info(
                "Outbox processed",
                extra={"context": {"conversation_id": conversation_id, "coalesced_count": len(batch_sorted)}},
            )
        except Exception as exc:
            now = datetime.now(timezone.utc)
            for row in batch_sorted:
                outbox_id = row.get("id")
                if not outbox_id:
                    continue
                attempts = int(row.get("attempts") or 0)
                if attempts >= max_attempts:
                    mark_outbox_status(
                        db,
                        outbox_id=outbox_id,
                        status="FAILED",
                        last_error=str(exc)[:500],
                        next_attempt_at=None,
                    )
                    results["failed"] += 1
                    continue
                backoff = retry_backoff_seconds * (2 ** max(attempts - 1, 0))
                next_attempt_at = now + timedelta(seconds=backoff)
                mark_outbox_status(
                    db,
                    outbox_id=outbox_id,
                    status="PENDING",
                    last_error=str(exc)[:500],
                    next_attempt_at=next_attempt_at,
                )
                results["retry_scheduled"] += 1
            logger.error(
                "Outbox processing failed",
                extra={
                    "context": {
                        "conversation_id": conversation_id,
                        "error": str(exc),
                        "coalesced_count": len(batch_sorted),
                    }
                },
            )

    return results


# === HEALTH ENDPOINTS ===


@router.get("/health")
async def system_health(db: Session = Depends(get_db)):
    """Get system health status."""
    return get_system_health(db)


@router.post("/heal")
async def heal_system(db: Session = Depends(get_db)):
    """Check and heal invariant violations."""
    return check_and_heal_conversations(db)


@router.get("/version", response_model=VersionResponse)
async def get_version():
    """Return build metadata for diagnostics."""
    return VersionResponse(
        version=os.environ.get("APP_VERSION", "unknown"),
        git_commit=os.environ.get("GIT_COMMIT"),
        build_time=os.environ.get("BUILD_TIME"),
    )
