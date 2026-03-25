from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.compliance_lifecycle_artifact import ComplianceLifecycleArtifact
from app.models.compliance_lifecycle_record import ComplianceLifecycleRecord
from app.models.compliance_lifecycle_run import ComplianceLifecycleRun

COMPLIANCE_LIFECYCLE_ARTIFACT_TYPE = "compliance_lifecycle_evidence"


def _normalize_scope(scope: str, *, branch_id: UUID | None) -> str:
    normalized = str(scope or "").strip().lower()
    if normalized not in {"client", "branch"}:
        raise ValueError("scope must be client|branch")
    if normalized == "client" and branch_id is not None:
        raise ValueError("branch_id is only valid for branch scope")
    if normalized == "branch" and branch_id is None:
        raise ValueError("branch_id required for branch scope")
    return normalized


def _record_sort_key(record: ComplianceLifecycleRecord) -> tuple[str, str]:
    occurred_at = (
        record.occurred_at.isoformat()
        if isinstance(record.occurred_at, datetime)
        else ""
    )
    return occurred_at, str(record.id)


def _build_artifact_payload(
    *,
    run: ComplianceLifecycleRun,
    records: Iterable[ComplianceLifecycleRecord],
) -> dict[str, Any]:
    summary = run.summary_json if isinstance(run.summary_json, dict) else {}
    serialized_records: list[dict[str, Any]] = []
    for row in sorted(records, key=_record_sort_key):
        payload = row.payload_json if isinstance(row.payload_json, dict) else {}
        serialized_records.append(
            {
                "record_id": str(row.id),
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "action": row.action,
                "result": row.result,
                "payload": payload,
                "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
            }
        )
    return {
        "run": {
            "run_id": str(run.id),
            "scope": run.scope,
            "data_class": run.data_class,
            "operation": run.operation,
            "run_mode": run.run_mode,
            "status": run.status,
            "client_id": str(run.client_id) if run.client_id else None,
            "branch_id": str(run.branch_id) if run.branch_id else None,
            "policy_version_id": str(run.policy_version_id) if run.policy_version_id else None,
        },
        "summary": summary,
        "records": serialized_records,
    }


def _compute_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def publish_lifecycle_artifact(
    db: Session,
    *,
    run: ComplianceLifecycleRun,
    records: Iterable[ComplianceLifecycleRecord],
    actor_id: UUID | None,
) -> ComplianceLifecycleArtifact:
    normalized_scope = _normalize_scope(run.scope, branch_id=run.branch_id)
    payload = _build_artifact_payload(run=run, records=records)
    digest = _compute_digest(payload)
    summary = run.summary_json if isinstance(run.summary_json, dict) else {}
    evidence_count_raw = summary.get("evidence_record_count")
    evidence_count = (
        int(evidence_count_raw)
        if isinstance(evidence_count_raw, int) and evidence_count_raw >= 0
        else len(payload.get("records") or [])
    )
    now = datetime.now(timezone.utc)

    record = (
        db.query(ComplianceLifecycleArtifact)
        .filter(ComplianceLifecycleArtifact.run_id == run.id)
        .first()
    )

    if record is None:
        record = ComplianceLifecycleArtifact(
            run_id=run.id,
            scope=normalized_scope,
            data_class=run.data_class,
            operation=run.operation,
            run_mode=run.run_mode,
            status=run.status,
            client_id=run.client_id,
            branch_id=run.branch_id,
            artifact_type=COMPLIANCE_LIFECYCLE_ARTIFACT_TYPE,
            artifact_digest=digest,
            payload_json=payload,
            records_count=len(payload.get("records") or []),
            evidence_record_count=evidence_count,
            published_by=actor_id,
            published_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(record)
    else:
        record.scope = normalized_scope
        record.data_class = run.data_class
        record.operation = run.operation
        record.run_mode = run.run_mode
        record.status = run.status
        record.client_id = run.client_id
        record.branch_id = run.branch_id
        record.artifact_type = COMPLIANCE_LIFECYCLE_ARTIFACT_TYPE
        record.artifact_digest = digest
        record.payload_json = payload
        record.records_count = len(payload.get("records") or [])
        record.evidence_record_count = evidence_count
        record.published_by = actor_id
        record.published_at = now
        record.updated_at = now

    db.flush()
    return record


def get_lifecycle_artifact(
    db: Session,
    *,
    run_id: UUID,
    client_id: UUID,
    scope: str,
    branch_id: UUID | None,
) -> ComplianceLifecycleArtifact | None:
    normalized_scope = _normalize_scope(scope, branch_id=branch_id)
    query = db.query(ComplianceLifecycleArtifact).filter(
        ComplianceLifecycleArtifact.run_id == run_id,
        ComplianceLifecycleArtifact.client_id == client_id,
        ComplianceLifecycleArtifact.scope == normalized_scope,
    )
    if normalized_scope == "branch":
        query = query.filter(ComplianceLifecycleArtifact.branch_id == branch_id)
    else:
        query = query.filter(ComplianceLifecycleArtifact.branch_id.is_(None))
    return query.first()


__all__ = [
    "COMPLIANCE_LIFECYCLE_ARTIFACT_TYPE",
    "publish_lifecycle_artifact",
    "get_lifecycle_artifact",
]
