from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.models.sla_profile_version import SlaProfileVersion
from app.schemas.sla_profile import SlaProfilePayload

SLA_PROFILE_SCHEMA_VERSION = "v1"
SLA_PROFILE_SCOPES = ("global", "domain", "client", "branch")
SLA_PROFILE_STATUSES = ("published", "archived")


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


def _normalize_scope_key(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in SLA_PROFILE_SCOPES:
        raise ValueError("scope must be global|domain|client|branch")
    return normalized


def _normalize_scope_target(
    *,
    scope: str,
    company_id: UUID | None,
    domain_key: str | None,
    client_id: UUID | None,
    branch_id: UUID | None,
) -> tuple[str, UUID | None, str | None, UUID | None, UUID | None]:
    normalized_scope = _normalize_scope_key(scope)
    normalized_domain = (
        str(domain_key).strip().lower()
        if isinstance(domain_key, str) and str(domain_key).strip()
        else None
    )

    if normalized_scope == "global":
        if any(value is not None for value in (company_id, normalized_domain, client_id, branch_id)):
            raise ValueError("global scope does not accept company_id/domain_key/client_id/branch_id")
    elif normalized_scope == "domain":
        if normalized_domain is None:
            raise ValueError("domain_key is required for domain scope")
        if any(value is not None for value in (company_id, client_id, branch_id)):
            raise ValueError("domain scope accepts only domain_key")
    elif normalized_scope == "client":
        if company_id is None or client_id is None:
            raise ValueError("company_id and client_id are required for client scope")
        if normalized_domain is not None or branch_id is not None:
            raise ValueError("client scope does not accept domain_key/branch_id")
    elif normalized_scope == "branch":
        if company_id is None or client_id is None or branch_id is None:
            raise ValueError("company_id, client_id and branch_id are required for branch scope")
        if normalized_domain is not None:
            raise ValueError("branch scope does not accept domain_key")

    return normalized_scope, company_id, normalized_domain, client_id, branch_id


def _normalize_payload(payload: SlaProfilePayload | dict[str, Any] | None) -> SlaProfilePayload:
    if isinstance(payload, SlaProfilePayload):
        return payload
    if payload is None:
        return SlaProfilePayload()
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    try:
        return SlaProfilePayload.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid SLA profile payload: {_summarize_validation_error(exc)}") from exc


def _scope_query(
    db: Session,
    *,
    scope: str,
    company_id: UUID | None,
    domain_key: str | None,
    client_id: UUID | None,
    branch_id: UUID | None,
) -> Query:
    query = db.query(SlaProfileVersion).filter(SlaProfileVersion.scope == scope)
    if scope == "global":
        return query.filter(
            SlaProfileVersion.company_id.is_(None),
            SlaProfileVersion.domain_key.is_(None),
            SlaProfileVersion.client_id.is_(None),
            SlaProfileVersion.branch_id.is_(None),
        )
    if scope == "domain":
        return query.filter(
            SlaProfileVersion.company_id.is_(None),
            SlaProfileVersion.domain_key == domain_key,
            SlaProfileVersion.client_id.is_(None),
            SlaProfileVersion.branch_id.is_(None),
        )
    if scope == "client":
        return query.filter(
            SlaProfileVersion.company_id == company_id,
            SlaProfileVersion.domain_key.is_(None),
            SlaProfileVersion.client_id == client_id,
            SlaProfileVersion.branch_id.is_(None),
        )
    return query.filter(
        SlaProfileVersion.company_id == company_id,
        SlaProfileVersion.domain_key.is_(None),
        SlaProfileVersion.client_id == client_id,
        SlaProfileVersion.branch_id == branch_id,
    )


def get_latest_profile_version(
    db: Session,
    *,
    scope: str,
    company_id: UUID | None = None,
    domain_key: str | None = None,
    client_id: UUID | None = None,
    branch_id: UUID | None = None,
    status: str = "published",
) -> SlaProfileVersion | None:
    normalized_scope, normalized_company_id, normalized_domain, normalized_client_id, normalized_branch_id = _normalize_scope_target(
        scope=scope,
        company_id=company_id,
        domain_key=domain_key,
        client_id=client_id,
        branch_id=branch_id,
    )
    query = _scope_query(
        db,
        scope=normalized_scope,
        company_id=normalized_company_id,
        domain_key=normalized_domain,
        client_id=normalized_client_id,
        branch_id=normalized_branch_id,
    )
    if status:
        normalized_status = str(status).strip().lower()
        if normalized_status not in SLA_PROFILE_STATUSES:
            raise ValueError("status must be published|archived")
        query = query.filter(SlaProfileVersion.status == normalized_status)
    return query.order_by(
        SlaProfileVersion.version_number.desc(),
        SlaProfileVersion.published_at.desc().nullslast(),
        SlaProfileVersion.created_at.desc(),
    ).first()


def list_profile_history(
    db: Session,
    *,
    scope: str,
    company_id: UUID | None = None,
    domain_key: str | None = None,
    client_id: UUID | None = None,
    branch_id: UUID | None = None,
    statuses: Iterable[str] = ("published", "archived"),
    limit: int = 20,
) -> list[SlaProfileVersion]:
    normalized_scope, normalized_company_id, normalized_domain, normalized_client_id, normalized_branch_id = _normalize_scope_target(
        scope=scope,
        company_id=company_id,
        domain_key=domain_key,
        client_id=client_id,
        branch_id=branch_id,
    )
    query = _scope_query(
        db,
        scope=normalized_scope,
        company_id=normalized_company_id,
        domain_key=normalized_domain,
        client_id=normalized_client_id,
        branch_id=normalized_branch_id,
    )
    statuses_list = [str(item).strip().lower() for item in statuses if str(item).strip()]
    if statuses_list:
        unsupported = [item for item in statuses_list if item not in SLA_PROFILE_STATUSES]
        if unsupported:
            raise ValueError("statuses must contain only published|archived")
        query = query.filter(SlaProfileVersion.status.in_(statuses_list))
    return query.order_by(
        SlaProfileVersion.version_number.desc(),
        SlaProfileVersion.published_at.desc().nullslast(),
        SlaProfileVersion.created_at.desc(),
    ).limit(max(1, min(limit, 200))).all()


def _next_version_number(
    db: Session,
    *,
    scope: str,
    company_id: UUID | None,
    domain_key: str | None,
    client_id: UUID | None,
    branch_id: UUID | None,
) -> int:
    query = _scope_query(
        db,
        scope=scope,
        company_id=company_id,
        domain_key=domain_key,
        client_id=client_id,
        branch_id=branch_id,
    ).with_entities(func.max(SlaProfileVersion.version_number))
    current = query.scalar()
    return int(current or 0) + 1


def publish_profile_version(
    db: Session,
    *,
    scope: str,
    company_id: UUID | None = None,
    domain_key: str | None = None,
    client_id: UUID | None = None,
    branch_id: UUID | None = None,
    payload: SlaProfilePayload | dict[str, Any] | None,
    actor_id: UUID | None,
    reason: str | None,
    schema_version: str = SLA_PROFILE_SCHEMA_VERSION,
    source_version_id: UUID | None = None,
) -> SlaProfileVersion:
    normalized_scope, normalized_company_id, normalized_domain, normalized_client_id, normalized_branch_id = _normalize_scope_target(
        scope=scope,
        company_id=company_id,
        domain_key=domain_key,
        client_id=client_id,
        branch_id=branch_id,
    )
    if schema_version != SLA_PROFILE_SCHEMA_VERSION:
        raise ValueError("Unsupported SLA profile schema_version")
    payload_model = _normalize_payload(payload)
    payload_json = payload_model.model_dump(exclude_none=True)
    now = datetime.now(timezone.utc)

    active = get_latest_profile_version(
        db,
        scope=normalized_scope,
        company_id=normalized_company_id,
        domain_key=normalized_domain,
        client_id=normalized_client_id,
        branch_id=normalized_branch_id,
        status="published",
    )
    if active is not None:
        active.status = "archived"
        active.updated_at = now

    record = SlaProfileVersion(
        scope=normalized_scope,
        company_id=normalized_company_id,
        domain_key=normalized_domain,
        client_id=normalized_client_id,
        branch_id=normalized_branch_id,
        status="published",
        schema_version=schema_version,
        version_number=_next_version_number(
            db,
            scope=normalized_scope,
            company_id=normalized_company_id,
            domain_key=normalized_domain,
            client_id=normalized_client_id,
            branch_id=normalized_branch_id,
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


def rollback_profile_version(
    db: Session,
    *,
    scope: str,
    target_version_id: UUID,
    actor_id: UUID | None,
    reason: str | None,
    company_id: UUID | None = None,
    domain_key: str | None = None,
    client_id: UUID | None = None,
    branch_id: UUID | None = None,
) -> tuple[SlaProfileVersion, SlaProfileVersion]:
    normalized_scope, normalized_company_id, normalized_domain, normalized_client_id, normalized_branch_id = _normalize_scope_target(
        scope=scope,
        company_id=company_id,
        domain_key=domain_key,
        client_id=client_id,
        branch_id=branch_id,
    )

    target = _scope_query(
        db,
        scope=normalized_scope,
        company_id=normalized_company_id,
        domain_key=normalized_domain,
        client_id=normalized_client_id,
        branch_id=normalized_branch_id,
    ).filter(SlaProfileVersion.id == target_version_id).first()
    if target is None:
        raise ValueError("SLA profile version not found")

    restored = publish_profile_version(
        db,
        scope=normalized_scope,
        company_id=normalized_company_id,
        domain_key=normalized_domain,
        client_id=normalized_client_id,
        branch_id=normalized_branch_id,
        payload=target.payload_json or {},
        actor_id=actor_id,
        reason=reason,
        schema_version=target.schema_version or SLA_PROFILE_SCHEMA_VERSION,
        source_version_id=target.id,
    )
    return restored, target


def _deep_merge_dicts(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in patch.items():
        if (
            isinstance(value, dict)
            and isinstance(merged.get(key), dict)
        ):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def resolve_effective_profile_version(
    db: Session,
    *,
    company_id: UUID | None,
    domain_key: str | None,
    client_id: UUID | None,
    branch_id: UUID | None,
) -> SlaProfileVersion | None:
    lookup_plan = [
        ("branch", company_id, None, client_id, branch_id),
        ("client", company_id, None, client_id, None),
        ("domain", None, domain_key, None, None),
        ("global", None, None, None, None),
    ]
    for scope, resolved_company_id, resolved_domain, resolved_client_id, resolved_branch_id in lookup_plan:
        if scope == "branch" and (resolved_company_id is None or resolved_client_id is None or resolved_branch_id is None):
            continue
        if scope == "client" and (resolved_company_id is None or resolved_client_id is None):
            continue
        if scope == "domain" and resolved_domain is None:
            continue
        record = get_latest_profile_version(
            db,
            scope=scope,
            company_id=resolved_company_id,
            domain_key=resolved_domain,
            client_id=resolved_client_id,
            branch_id=resolved_branch_id,
            status="published",
        )
        if record is not None:
            return record
    return None


def resolve_effective_profile_payload(
    db: Session,
    *,
    company_id: UUID | None,
    domain_key: str | None,
    client_id: UUID | None,
    branch_id: UUID | None,
) -> SlaProfilePayload | None:
    layered_payload: dict[str, Any] = {}
    lookup_plan = [
        ("global", None, None, None, None),
        ("domain", None, domain_key, None, None),
        ("client", company_id, None, client_id, None),
        ("branch", company_id, None, client_id, branch_id),
    ]
    found_any = False
    for scope, resolved_company_id, resolved_domain, resolved_client_id, resolved_branch_id in lookup_plan:
        if scope == "domain" and resolved_domain is None:
            continue
        if scope == "client" and (resolved_company_id is None or resolved_client_id is None):
            continue
        if scope == "branch" and (resolved_company_id is None or resolved_client_id is None or resolved_branch_id is None):
            continue
        record = get_latest_profile_version(
            db,
            scope=scope,
            company_id=resolved_company_id,
            domain_key=resolved_domain,
            client_id=resolved_client_id,
            branch_id=resolved_branch_id,
            status="published",
        )
        if record is None:
            continue
        payload_chunk = record.payload_json if isinstance(record.payload_json, dict) else {}
        layered_payload = _deep_merge_dicts(layered_payload, payload_chunk)
        found_any = True
    if not found_any:
        return None
    try:
        return SlaProfilePayload.model_validate(layered_payload)
    except ValidationError:
        # Fail-closed runtime behavior for invalid persisted payloads.
        return None


__all__ = [
    "SLA_PROFILE_SCHEMA_VERSION",
    "get_latest_profile_version",
    "list_profile_history",
    "publish_profile_version",
    "resolve_effective_profile_payload",
    "resolve_effective_profile_version",
    "rollback_profile_version",
]
