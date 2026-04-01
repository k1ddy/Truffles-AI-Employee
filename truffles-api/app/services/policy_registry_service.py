from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.models.client_policy_version import ClientPolicyVersion
from app.schemas.capabilities import CapabilityPolicyOverrides

POLICY_REGISTRY_SCHEMA_VERSION = "v1"


def _summarize_validation_error(exc: ValidationError, *, limit: int = 3) -> str:
    parts: list[str] = []
    for item in exc.errors():
        loc = item.get("loc") or []
        loc_text = ".".join(str(entry) for entry in loc) if loc else ""
        msg = item.get("msg") or "invalid"
        parts.append(f"{loc_text}:{msg}" if loc_text else msg)
        if len(parts) >= limit:
            break
    return "; ".join(parts) or "invalid_payload"


def _normalize_scope(*, scope: str, branch_id: UUID | None) -> str:
    normalized = str(scope or "").strip().lower()
    if normalized not in {"client", "branch"}:
        raise ValueError("scope must be client|branch")
    if normalized == "branch" and not branch_id:
        raise ValueError("branch_id required for branch scope")
    if normalized == "client" and branch_id is not None:
        raise ValueError("branch_id is only valid for branch scope")
    return normalized


def _normalize_payload(
    payload: CapabilityPolicyOverrides | dict[str, Any] | None,
) -> CapabilityPolicyOverrides:
    if isinstance(payload, CapabilityPolicyOverrides):
        return payload
    if payload is None:
        return CapabilityPolicyOverrides()
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    try:
        return CapabilityPolicyOverrides.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(
            f"Invalid policy payload: {_summarize_validation_error(exc)}"
        ) from exc


def _scope_query(
    db: Session,
    *,
    client_id: UUID,
    scope: str,
    branch_id: UUID | None,
) -> Query:
    query = db.query(ClientPolicyVersion).filter(
        ClientPolicyVersion.client_id == client_id,
        ClientPolicyVersion.scope == scope,
    )
    if scope == "branch":
        query = query.filter(ClientPolicyVersion.branch_id == branch_id)
    else:
        query = query.filter(ClientPolicyVersion.branch_id.is_(None))
    return query


def get_latest_policy_version(
    db: Session,
    *,
    client_id: UUID,
    scope: str,
    branch_id: UUID | None,
    status: str = "published",
) -> ClientPolicyVersion | None:
    normalized_scope = _normalize_scope(scope=scope, branch_id=branch_id)
    query = _scope_query(
        db,
        client_id=client_id,
        scope=normalized_scope,
        branch_id=branch_id,
    )
    if status:
        query = query.filter(ClientPolicyVersion.status == status)
    return query.order_by(
        ClientPolicyVersion.version_number.desc(),
        ClientPolicyVersion.published_at.desc().nullslast(),
        ClientPolicyVersion.created_at.desc(),
    ).first()


def list_policy_history(
    db: Session,
    *,
    client_id: UUID,
    scope: str,
    branch_id: UUID | None,
    statuses: Iterable[str] = ("published", "archived"),
    limit: int = 20,
) -> list[ClientPolicyVersion]:
    normalized_scope = _normalize_scope(scope=scope, branch_id=branch_id)
    query = _scope_query(
        db,
        client_id=client_id,
        scope=normalized_scope,
        branch_id=branch_id,
    )
    statuses_list = [str(item).strip().lower() for item in statuses if str(item).strip()]
    if statuses_list:
        query = query.filter(ClientPolicyVersion.status.in_(statuses_list))
    return query.order_by(
        ClientPolicyVersion.version_number.desc(),
        ClientPolicyVersion.published_at.desc().nullslast(),
        ClientPolicyVersion.created_at.desc(),
    ).limit(max(1, min(limit, 200))).all()


def _next_version_number(
    db: Session,
    *,
    client_id: UUID,
    scope: str,
    branch_id: UUID | None,
) -> int:
    query = _scope_query(
        db,
        client_id=client_id,
        scope=scope,
        branch_id=branch_id,
    ).with_entities(func.max(ClientPolicyVersion.version_number))
    current = query.scalar()
    return int(current or 0) + 1


def publish_policy_version(
    db: Session,
    *,
    client_id: UUID,
    scope: str,
    branch_id: UUID | None,
    payload: CapabilityPolicyOverrides | dict[str, Any] | None,
    actor_id: UUID | None,
    reason: str | None,
    schema_version: str = POLICY_REGISTRY_SCHEMA_VERSION,
    source_version_id: UUID | None = None,
) -> ClientPolicyVersion:
    normalized_scope = _normalize_scope(scope=scope, branch_id=branch_id)
    if schema_version != POLICY_REGISTRY_SCHEMA_VERSION:
        raise ValueError("Unsupported policy registry schema_version")
    payload_model = _normalize_payload(payload)
    payload_json = payload_model.model_dump(exclude_none=True)
    now = datetime.now(timezone.utc)

    active = get_latest_policy_version(
        db,
        client_id=client_id,
        scope=normalized_scope,
        branch_id=branch_id,
        status="published",
    )
    if active is not None:
        active.status = "archived"
        active.updated_at = now

    record = ClientPolicyVersion(
        client_id=client_id,
        branch_id=branch_id,
        scope=normalized_scope,
        status="published",
        schema_version=schema_version,
        version_number=_next_version_number(
            db,
            client_id=client_id,
            scope=normalized_scope,
            branch_id=branch_id,
        ),
        payload_json=payload_json,
        reason=reason.strip() if isinstance(reason, str) and reason.strip() else None,
        source_version_id=source_version_id,
        created_by=actor_id,
        published_by=actor_id,
        created_at=now,
        published_at=now,
        updated_at=now,
    )
    db.add(record)
    db.flush()
    return record


def rollback_policy_version(
    db: Session,
    *,
    client_id: UUID,
    scope: str,
    branch_id: UUID | None,
    target_version_id: UUID,
    actor_id: UUID | None,
    reason: str | None,
) -> tuple[ClientPolicyVersion, ClientPolicyVersion]:
    normalized_scope = _normalize_scope(scope=scope, branch_id=branch_id)
    target = _scope_query(
        db,
        client_id=client_id,
        scope=normalized_scope,
        branch_id=branch_id,
    ).filter(ClientPolicyVersion.id == target_version_id).first()
    if target is None:
        raise ValueError("Policy version not found")

    restored = publish_policy_version(
        db,
        client_id=client_id,
        scope=normalized_scope,
        branch_id=branch_id,
        payload=target.payload_json or {},
        actor_id=actor_id,
        reason=reason,
        source_version_id=target.id,
    )
    return restored, target


def resolve_effective_policy_version(
    db: Session,
    *,
    client_id: UUID | None,
    branch_id: UUID | None,
) -> ClientPolicyVersion | None:
    if client_id is None:
        return None
    if branch_id is not None:
        branch_version = get_latest_policy_version(
            db,
            client_id=client_id,
            scope="branch",
            branch_id=branch_id,
            status="published",
        )
        if branch_version is not None:
            return branch_version
    return get_latest_policy_version(
        db,
        client_id=client_id,
        scope="client",
        branch_id=None,
        status="published",
    )


def resolve_effective_policy_overrides(
    db: Session,
    *,
    client_id: UUID | None,
    branch_id: UUID | None,
) -> CapabilityPolicyOverrides | None:
    record = resolve_effective_policy_version(
        db,
        client_id=client_id,
        branch_id=branch_id,
    )
    if record is None:
        return None
    try:
        return CapabilityPolicyOverrides.model_validate(record.payload_json or {})
    except ValidationError:
        # Fail-closed runtime behavior: ignore invalid persisted override payload.
        return None


__all__ = [
    "POLICY_REGISTRY_SCHEMA_VERSION",
    "get_latest_policy_version",
    "list_policy_history",
    "publish_policy_version",
    "resolve_effective_policy_overrides",
    "resolve_effective_policy_version",
    "rollback_policy_version",
]
