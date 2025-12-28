"""Admin API endpoints for managing bot configuration."""

import os
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Client, ClientSettings, Prompt
from app.services.alert_service import alert_warning
from app.services.health_service import check_and_heal_conversations, get_system_health
from app.services.outbox_service import claim_pending_outbox_batches, release_stale_processing

router = APIRouter(prefix="/admin", tags=["admin"])

ALLOWED_BRANCH_MODES = {"by_instance", "ask_user", "hybrid"}
ALLOWED_MANAGER_SCOPES = {"branch", "global"}
ALLOWED_AUTO_APPROVE_ROLES = {"owner", "admin", "manager", "support"}
MEDIA_STORAGE_DIR = Path(os.environ.get("MEDIA_STORAGE_DIR", "/home/zhan/truffles-media"))
MEDIA_CLEANUP_TTL_DAYS = int(os.environ.get("MEDIA_CLEANUP_TTL_DAYS", "7"))
MEDIA_STORAGE_WARN_BYTES = int(os.environ.get("MEDIA_STORAGE_WARN_BYTES", str(5 * 1024 * 1024 * 1024)))


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


class MediaCleanupResponse(BaseModel):
    ttl_days: int
    dry_run: bool
    total_files: int
    total_bytes: int
    deleted_files: int
    deleted_bytes: int
    remaining_files: int
    remaining_bytes: int


def _coerce_metric_value(value: object):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


# === PROMPT ENDPOINTS ===


def _require_admin_token(provided: Optional[str]) -> None:
    expected = os.environ.get("ALERTS_ADMIN_TOKEN")
    if not expected:
        raise HTTPException(status_code=500, detail="ALERTS_ADMIN_TOKEN not configured")
    if not provided or provided != expected:
        raise HTTPException(status_code=401, detail="Invalid admin token")


def _cleanup_media_storage(storage_dir: Path, ttl_days: int, dry_run: bool) -> dict:
    cutoff_ts = (datetime.now(timezone.utc).timestamp()) - (ttl_days * 86400)
    total_files = 0
    total_bytes = 0
    deleted_files = 0
    deleted_bytes = 0

    if not storage_dir.exists():
        return {
            "ttl_days": ttl_days,
            "dry_run": dry_run,
            "total_files": 0,
            "total_bytes": 0,
            "deleted_files": 0,
            "deleted_bytes": 0,
            "remaining_files": 0,
            "remaining_bytes": 0,
        }

    for path in storage_dir.rglob("*"):
        if not path.is_file():
            continue
        total_files += 1
        try:
            stat = path.stat()
        except OSError:
            continue
        total_bytes += stat.st_size
        if stat.st_mtime <= cutoff_ts:
            deleted_files += 1
            deleted_bytes += stat.st_size
            if not dry_run:
                try:
                    path.unlink()
                except OSError:
                    continue

    if not dry_run:
        for path in sorted(storage_dir.rglob("*"), reverse=True):
            if path.is_dir():
                try:
                    if not any(path.iterdir()):
                        path.rmdir()
                except OSError:
                    continue

    remaining_files = max(total_files - deleted_files, 0)
    remaining_bytes = max(total_bytes - deleted_bytes, 0)
    return {
        "ttl_days": ttl_days,
        "dry_run": dry_run,
        "total_files": total_files,
        "total_bytes": total_bytes,
        "deleted_files": deleted_files,
        "deleted_bytes": deleted_bytes,
        "remaining_files": remaining_files,
        "remaining_bytes": remaining_bytes,
    }


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
    stale_seconds = int(float(os.environ.get("OUTBOX_STALE_PROCESSING_SECONDS", "120")))
    stale_seconds = max(stale_seconds, 0)
    released = release_stale_processing(
        db,
        stale_seconds=stale_seconds,
        max_attempts=max_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
    )
    rows = claim_pending_outbox_batches(db, limit=limit, idle_seconds=idle_seconds)

    from app.routers.webhook import _process_outbox_rows

    results = await _process_outbox_rows(
        db,
        rows,
        max_attempts=max_attempts,
        retry_backoff_seconds=retry_backoff_seconds,
    )
    if released["released"] or released["failed"]:
        results["released_stale"] = released["released"]
        results["failed_stale"] = released["failed"]
    return results


# === MEDIA CLEANUP ===


@router.post("/media/cleanup", response_model=MediaCleanupResponse)
async def cleanup_media(
    ttl_days: Optional[int] = None,
    dry_run: bool = False,
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _require_admin_token(x_admin_token)
    effective_ttl = ttl_days if ttl_days is not None else MEDIA_CLEANUP_TTL_DAYS
    effective_ttl = max(int(effective_ttl), 1)
    results = _cleanup_media_storage(MEDIA_STORAGE_DIR, effective_ttl, dry_run)
    if results["remaining_bytes"] > MEDIA_STORAGE_WARN_BYTES:
        alert_warning(
            "Media storage exceeds threshold",
            {
                "remaining_bytes": results["remaining_bytes"],
                "threshold_bytes": MEDIA_STORAGE_WARN_BYTES,
                "storage_dir": str(MEDIA_STORAGE_DIR),
            },
        )
    return results


# === KNOWLEDGE BACKLOG ===


@router.get("/knowledge-backlog")
async def get_knowledge_backlog(
    client_slug: str,
    days: int = 7,
    limit: int = 20,
    db: Session = Depends(get_db),
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _require_admin_token(x_admin_token)
    client = db.query(Client).filter(Client.name == client_slug).first()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{client_slug}' not found")

    safe_days = max(1, min(int(days), 90))
    safe_limit = max(1, min(int(limit), 100))

    rows = (
        db.execute(
            text(
                """
                SELECT
                  miss_type,
                  user_text,
                  language,
                  repeat_count,
                  first_seen_at,
                  last_seen_at
                FROM knowledge_backlog
                WHERE client_id = :client_id
                  AND last_seen_at >= (NOW() - (:days * INTERVAL '1 day'))
                ORDER BY repeat_count DESC, last_seen_at DESC
                LIMIT :limit
                """
            ),
            {"client_id": client.id, "days": safe_days, "limit": safe_limit},
        )
        .mappings()
        .all()
    )

    return {
        "client_slug": client_slug,
        "days": safe_days,
        "limit": safe_limit,
        "items": [dict(row) for row in rows],
    }


# === METRICS ===


@router.get("/metrics")
async def get_metrics(
    client_slug: str,
    metric_date: Optional[str] = None,
    db: Session = Depends(get_db),
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    _require_admin_token(x_admin_token)
    client = db.query(Client).filter(Client.name == client_slug).first()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{client_slug}' not found")

    if metric_date:
        try:
            metric_day = date.fromisoformat(metric_date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="metric_date must be YYYY-MM-DD") from exc
    else:
        metric_day = datetime.now(timezone.utc).date()

    row = (
        db.execute(
            text(
                """
                SELECT
                  metric_date,
                  outbox_latency_p50,
                  outbox_latency_p90,
                  llm_timeout_rate,
                  llm_used_rate,
                  escalation_rate,
                  fast_intent_rate,
                  asr_fail_rate,
                  total_user_messages,
                  total_outbox_sent,
                  total_outbox_failed,
                  total_llm_used,
                  total_llm_timeout,
                  total_handovers,
                  total_fast_intent,
                  total_asr_used,
                  total_asr_failed,
                  created_at,
                  updated_at
                FROM metrics_daily
                WHERE client_id = :client_id AND metric_date = :metric_date
                """
            ),
            {"client_id": client.id, "metric_date": metric_day},
        )
        .mappings()
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="Metrics not found for date/client")

    payload = {key: _coerce_metric_value(value) for key, value in row.items()}
    payload["client_slug"] = client_slug
    return payload


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
