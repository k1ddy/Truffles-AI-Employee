from __future__ import annotations

import os
from dataclasses import dataclass

from app.schemas.consult import ConsultPlaybook, validate_consult_playbook
from app.schemas.outbox_payload import TenantContext
from app.services.knowledge_snapshot_service import build_knowledge_snapshot


def _is_env_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def is_snapshot_consumer_enabled() -> bool:
    return _is_env_enabled(os.environ.get("KNOWLEDGE_SNAPSHOT_CONSUMER_ENABLED"), default=False)


def get_consult_snapshot_mode() -> str:
    raw = (os.environ.get("KNOWLEDGE_SNAPSHOT_CONSULT_MODE") or "").strip().lower()
    if raw in {"fallback", "strict", "shadow"}:
        return raw
    return "shadow"


def _parse_allowlist(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def is_consult_snapshot_allowlisted(client_slug: str | None) -> bool:
    allowlist = _parse_allowlist(os.environ.get("KNOWLEDGE_SNAPSHOT_CONSULT_ALLOWLIST"))
    if not allowlist:
        return False
    if "*" in allowlist or "all" in allowlist:
        return True
    normalized = (client_slug or "").strip().lower()
    return bool(normalized and normalized in allowlist)


@dataclass(frozen=True)
class ConsultSnapshotShadowResult:
    playbook: ConsultPlaybook | None
    error: str | None
    snapshot_id: str | None
    version_id: str | None
    sha256: str | None
    playbook_error: str | None
    playbook_present: bool


def _build_consult_snapshot(
    db,
    *,
    client_id: str | None,
    branch_id: str | None,
    client_slug: str | None = None,
    source: str,
) -> ConsultSnapshotShadowResult:
    if not client_id:
        return ConsultSnapshotShadowResult(
            playbook=None,
            error="missing_client_id",
            snapshot_id=None,
            version_id=None,
            sha256=None,
            playbook_error=None,
            playbook_present=False,
        )

    tenant_context = TenantContext(
        client_id=client_id,
        branch_id=branch_id,
        client_slug=client_slug,
        source=source,
    )
    snapshot, error = build_knowledge_snapshot(db, tenant_context=tenant_context)
    if error:
        return ConsultSnapshotShadowResult(
            playbook=None,
            error=error,
            snapshot_id=None,
            version_id=None,
            sha256=None,
            playbook_error=None,
            playbook_present=False,
        )
    if not isinstance(snapshot, dict):
        return ConsultSnapshotShadowResult(
            playbook=None,
            error="snapshot_invalid",
            snapshot_id=None,
            version_id=None,
            sha256=None,
            playbook_error=None,
            playbook_present=False,
        )

    snapshot_id = snapshot.get("snapshot_id")
    version_id = snapshot.get("version_id")
    sha256_value = snapshot.get("sha256")
    packs = snapshot.get("packs") if isinstance(snapshot, dict) else None
    if not isinstance(packs, dict):
        return ConsultSnapshotShadowResult(
            playbook=None,
            error=None,
            snapshot_id=snapshot_id,
            version_id=version_id,
            sha256=sha256_value,
            playbook_error="snapshot_packs_missing",
            playbook_present=False,
        )

    playbook_payload = packs.get("consult_playbook")
    if not isinstance(playbook_payload, dict):
        return ConsultSnapshotShadowResult(
            playbook=None,
            error=None,
            snapshot_id=snapshot_id,
            version_id=version_id,
            sha256=sha256_value,
            playbook_error="consult_playbook_missing",
            playbook_present=False,
        )

    playbook, playbook_error = validate_consult_playbook(playbook_payload)
    return ConsultSnapshotShadowResult(
        playbook=playbook,
        error=None,
        snapshot_id=snapshot_id,
        version_id=version_id,
        sha256=sha256_value,
        playbook_error=playbook_error,
        playbook_present=playbook is not None,
    )


def build_consult_snapshot(
    db,
    *,
    client_id: str | None,
    branch_id: str | None,
    client_slug: str | None = None,
) -> ConsultSnapshotShadowResult:
    return _build_consult_snapshot(
        db,
        client_id=client_id,
        branch_id=branch_id,
        client_slug=client_slug,
        source="consult_snapshot_consumer",
    )


def build_consult_snapshot_shadow(
    db,
    *,
    client_id: str | None,
    branch_id: str | None,
    client_slug: str | None = None,
) -> ConsultSnapshotShadowResult:
    return _build_consult_snapshot(
        db,
        client_id=client_id,
        branch_id=branch_id,
        client_slug=client_slug,
        source="consult_snapshot_shadow",
    )


__all__ = [
    "ConsultSnapshotShadowResult",
    "build_consult_snapshot",
    "build_consult_snapshot_shadow",
    "get_consult_snapshot_mode",
    "is_consult_snapshot_allowlisted",
    "is_snapshot_consumer_enabled",
]
