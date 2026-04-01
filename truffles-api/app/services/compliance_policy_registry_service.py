from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.models.compliance_policy_version import CompliancePolicyVersion
from app.schemas.compliance_policy import CompliancePolicyPayload

COMPLIANCE_POLICY_SCHEMA_VERSION = "v1"
COMPLIANCE_POLICY_SCOPES = ("global", "domain", "client", "branch")
COMPLIANCE_POLICY_STATUSES = ("published", "archived")
_COMPLIANCE_DATA_CLASS_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,63}$")


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
    if normalized not in COMPLIANCE_POLICY_SCOPES:
        raise ValueError("scope must be global|domain|client|branch")
    return normalized


def _normalize_data_class(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if not _COMPLIANCE_DATA_CLASS_RE.match(normalized):
        raise ValueError("data_class must match [a-z][a-z0-9_.-]{1,63}")
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


def _normalize_payload(
    payload: CompliancePolicyPayload | dict[str, Any] | None,
) -> CompliancePolicyPayload:
    if isinstance(payload, CompliancePolicyPayload):
        return payload
    if payload is None:
        return CompliancePolicyPayload()
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    try:
        return CompliancePolicyPayload.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(
            f"Invalid compliance policy payload: {_summarize_validation_error(exc)}"
        ) from exc


def _scope_query(
    db: Session,
    *,
    scope: str,
    data_class: str,
    company_id: UUID | None,
    domain_key: str | None,
    client_id: UUID | None,
    branch_id: UUID | None,
) -> Query:
    query = db.query(CompliancePolicyVersion).filter(
        CompliancePolicyVersion.scope == scope,
        CompliancePolicyVersion.data_class == data_class,
    )
    if scope == "global":
        return query.filter(
            CompliancePolicyVersion.company_id.is_(None),
            CompliancePolicyVersion.domain_key.is_(None),
            CompliancePolicyVersion.client_id.is_(None),
            CompliancePolicyVersion.branch_id.is_(None),
        )
    if scope == "domain":
        return query.filter(
            CompliancePolicyVersion.company_id.is_(None),
            CompliancePolicyVersion.domain_key == domain_key,
            CompliancePolicyVersion.client_id.is_(None),
            CompliancePolicyVersion.branch_id.is_(None),
        )
    if scope == "client":
        return query.filter(
            CompliancePolicyVersion.company_id == company_id,
            CompliancePolicyVersion.domain_key.is_(None),
            CompliancePolicyVersion.client_id == client_id,
            CompliancePolicyVersion.branch_id.is_(None),
        )
    return query.filter(
        CompliancePolicyVersion.company_id == company_id,
        CompliancePolicyVersion.domain_key.is_(None),
        CompliancePolicyVersion.client_id == client_id,
        CompliancePolicyVersion.branch_id == branch_id,
    )


def get_latest_compliance_policy_version(
    db: Session,
    *,
    scope: str,
    data_class: str,
    company_id: UUID | None = None,
    domain_key: str | None = None,
    client_id: UUID | None = None,
    branch_id: UUID | None = None,
    status: str = "published",
) -> CompliancePolicyVersion | None:
    normalized_scope, normalized_company_id, normalized_domain, normalized_client_id, normalized_branch_id = _normalize_scope_target(
        scope=scope,
        company_id=company_id,
        domain_key=domain_key,
        client_id=client_id,
        branch_id=branch_id,
    )
    normalized_data_class = _normalize_data_class(data_class)
    query = _scope_query(
        db,
        scope=normalized_scope,
        data_class=normalized_data_class,
        company_id=normalized_company_id,
        domain_key=normalized_domain,
        client_id=normalized_client_id,
        branch_id=normalized_branch_id,
    )
    if status:
        normalized_status = str(status).strip().lower()
        if normalized_status not in COMPLIANCE_POLICY_STATUSES:
            raise ValueError("status must be published|archived")
        query = query.filter(CompliancePolicyVersion.status == normalized_status)
    return query.order_by(
        CompliancePolicyVersion.version_number.desc(),
        CompliancePolicyVersion.published_at.desc().nullslast(),
        CompliancePolicyVersion.created_at.desc(),
    ).first()


def list_compliance_policy_history(
    db: Session,
    *,
    scope: str,
    data_class: str,
    company_id: UUID | None = None,
    domain_key: str | None = None,
    client_id: UUID | None = None,
    branch_id: UUID | None = None,
    statuses: Iterable[str] = ("published", "archived"),
    limit: int = 20,
) -> list[CompliancePolicyVersion]:
    normalized_scope, normalized_company_id, normalized_domain, normalized_client_id, normalized_branch_id = _normalize_scope_target(
        scope=scope,
        company_id=company_id,
        domain_key=domain_key,
        client_id=client_id,
        branch_id=branch_id,
    )
    normalized_data_class = _normalize_data_class(data_class)
    query = _scope_query(
        db,
        scope=normalized_scope,
        data_class=normalized_data_class,
        company_id=normalized_company_id,
        domain_key=normalized_domain,
        client_id=normalized_client_id,
        branch_id=normalized_branch_id,
    )
    statuses_list = [str(item).strip().lower() for item in statuses if str(item).strip()]
    if statuses_list:
        unsupported = [item for item in statuses_list if item not in COMPLIANCE_POLICY_STATUSES]
        if unsupported:
            raise ValueError("statuses must contain only published|archived")
        query = query.filter(CompliancePolicyVersion.status.in_(statuses_list))
    return query.order_by(
        CompliancePolicyVersion.version_number.desc(),
        CompliancePolicyVersion.published_at.desc().nullslast(),
        CompliancePolicyVersion.created_at.desc(),
    ).limit(max(1, min(limit, 200))).all()


def _next_version_number(
    db: Session,
    *,
    scope: str,
    data_class: str,
    company_id: UUID | None,
    domain_key: str | None,
    client_id: UUID | None,
    branch_id: UUID | None,
) -> int:
    query = _scope_query(
        db,
        scope=scope,
        data_class=data_class,
        company_id=company_id,
        domain_key=domain_key,
        client_id=client_id,
        branch_id=branch_id,
    ).with_entities(func.max(CompliancePolicyVersion.version_number))
    current = query.scalar()
    return int(current or 0) + 1


def publish_compliance_policy_version(
    db: Session,
    *,
    scope: str,
    data_class: str,
    company_id: UUID | None = None,
    domain_key: str | None = None,
    client_id: UUID | None = None,
    branch_id: UUID | None = None,
    payload: CompliancePolicyPayload | dict[str, Any] | None,
    actor_id: UUID | None,
    reason: str | None,
    schema_version: str = COMPLIANCE_POLICY_SCHEMA_VERSION,
    source_version_id: UUID | None = None,
) -> CompliancePolicyVersion:
    normalized_scope, normalized_company_id, normalized_domain, normalized_client_id, normalized_branch_id = _normalize_scope_target(
        scope=scope,
        company_id=company_id,
        domain_key=domain_key,
        client_id=client_id,
        branch_id=branch_id,
    )
    normalized_data_class = _normalize_data_class(data_class)
    if schema_version != COMPLIANCE_POLICY_SCHEMA_VERSION:
        raise ValueError("Unsupported compliance policy schema_version")
    payload_model = _normalize_payload(payload)
    payload_json = payload_model.model_dump(exclude_none=True)
    now = datetime.now(timezone.utc)

    active = get_latest_compliance_policy_version(
        db,
        scope=normalized_scope,
        data_class=normalized_data_class,
        company_id=normalized_company_id,
        domain_key=normalized_domain,
        client_id=normalized_client_id,
        branch_id=normalized_branch_id,
        status="published",
    )
    if active is not None:
        active.status = "archived"
        active.updated_at = now

    record = CompliancePolicyVersion(
        scope=normalized_scope,
        data_class=normalized_data_class,
        company_id=normalized_company_id,
        domain_key=normalized_domain,
        client_id=normalized_client_id,
        branch_id=normalized_branch_id,
        status="published",
        schema_version=schema_version,
        version_number=_next_version_number(
            db,
            scope=normalized_scope,
            data_class=normalized_data_class,
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


def rollback_compliance_policy_version(
    db: Session,
    *,
    scope: str,
    data_class: str,
    target_version_id: UUID,
    actor_id: UUID | None,
    reason: str | None,
    company_id: UUID | None = None,
    domain_key: str | None = None,
    client_id: UUID | None = None,
    branch_id: UUID | None = None,
) -> tuple[CompliancePolicyVersion, CompliancePolicyVersion]:
    normalized_scope, normalized_company_id, normalized_domain, normalized_client_id, normalized_branch_id = _normalize_scope_target(
        scope=scope,
        company_id=company_id,
        domain_key=domain_key,
        client_id=client_id,
        branch_id=branch_id,
    )
    normalized_data_class = _normalize_data_class(data_class)

    target = _scope_query(
        db,
        scope=normalized_scope,
        data_class=normalized_data_class,
        company_id=normalized_company_id,
        domain_key=normalized_domain,
        client_id=normalized_client_id,
        branch_id=normalized_branch_id,
    ).filter(CompliancePolicyVersion.id == target_version_id).first()
    if target is None:
        raise ValueError("Compliance policy version not found")

    restored = publish_compliance_policy_version(
        db,
        scope=normalized_scope,
        data_class=normalized_data_class,
        company_id=normalized_company_id,
        domain_key=normalized_domain,
        client_id=normalized_client_id,
        branch_id=normalized_branch_id,
        payload=target.payload_json or {},
        actor_id=actor_id,
        reason=reason,
        schema_version=target.schema_version or COMPLIANCE_POLICY_SCHEMA_VERSION,
        source_version_id=target.id,
    )
    return restored, target


def _deep_merge_dicts(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def resolve_effective_compliance_policy_version(
    db: Session,
    *,
    data_class: str,
    company_id: UUID | None,
    domain_key: str | None,
    client_id: UUID | None,
    branch_id: UUID | None,
) -> CompliancePolicyVersion | None:
    normalized_data_class = _normalize_data_class(data_class)
    lookup_plan = [
        ("branch", company_id, None, client_id, branch_id),
        ("client", company_id, None, client_id, None),
        ("domain", None, domain_key, None, None),
        ("global", None, None, None, None),
    ]
    for scope, resolved_company_id, resolved_domain, resolved_client_id, resolved_branch_id in lookup_plan:
        if scope == "branch" and (
            resolved_company_id is None or resolved_client_id is None or resolved_branch_id is None
        ):
            continue
        if scope == "client" and (resolved_company_id is None or resolved_client_id is None):
            continue
        if scope == "domain" and resolved_domain is None:
            continue
        record = get_latest_compliance_policy_version(
            db,
            scope=scope,
            data_class=normalized_data_class,
            company_id=resolved_company_id,
            domain_key=resolved_domain,
            client_id=resolved_client_id,
            branch_id=resolved_branch_id,
            status="published",
        )
        if record is not None:
            return record
    return None


def resolve_effective_compliance_policy_payload(
    db: Session,
    *,
    data_class: str,
    company_id: UUID | None,
    domain_key: str | None,
    client_id: UUID | None,
    branch_id: UUID | None,
) -> CompliancePolicyPayload | None:
    normalized_data_class = _normalize_data_class(data_class)
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
        if scope == "branch" and (
            resolved_company_id is None or resolved_client_id is None or resolved_branch_id is None
        ):
            continue
        record = get_latest_compliance_policy_version(
            db,
            scope=scope,
            data_class=normalized_data_class,
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
        return CompliancePolicyPayload.model_validate(layered_payload)
    except ValidationError:
        # Fail-closed runtime behavior for invalid persisted payloads.
        return None


__all__ = [
    "COMPLIANCE_POLICY_SCHEMA_VERSION",
    "get_latest_compliance_policy_version",
    "list_compliance_policy_history",
    "publish_compliance_policy_version",
    "resolve_effective_compliance_policy_payload",
    "resolve_effective_compliance_policy_version",
    "rollback_compliance_policy_version",
]
