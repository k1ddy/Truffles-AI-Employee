from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Query, Session

from app.models.compliance_lifecycle_record import ComplianceLifecycleRecord
from app.models.compliance_lifecycle_run import ComplianceLifecycleRun
from app.models.learned_response import LearnedResponse

COMPLIANCE_LIFECYCLE_SCOPES = ("client", "branch")
COMPLIANCE_LIFECYCLE_OPERATIONS = (
    "retention_scan",
    "export_preview",
    "destruction_preview",
)
COMPLIANCE_LIFECYCLE_MODES = ("preview", "manual")
COMPLIANCE_LIFECYCLE_STATUSES = ("running", "completed", "failed")
COMPLIANCE_LIFECYCLE_RECORD_RESULTS = ("candidate", "skipped", "error")
_COMPLIANCE_DATA_CLASS_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,63}$")
_DESTRUCTION_EXECUTION_ACTIONS = {
    "delete": "deactivate_record",
    "anonymize": "anonymize_record",
    "archive": "archive_record",
}


def _normalize_scope(scope: str, *, branch_id: UUID | None) -> str:
    normalized = str(scope or "").strip().lower()
    if normalized not in COMPLIANCE_LIFECYCLE_SCOPES:
        raise ValueError("scope must be client|branch")
    if normalized == "branch" and branch_id is None:
        raise ValueError("branch_id required for branch scope")
    if normalized == "client" and branch_id is not None:
        raise ValueError("branch_id is only valid for branch scope")
    return normalized


def _normalize_data_class(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if not _COMPLIANCE_DATA_CLASS_RE.match(normalized):
        raise ValueError("data_class must match [a-z][a-z0-9_.-]{1,63}")
    return normalized


def _normalize_operation(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in COMPLIANCE_LIFECYCLE_OPERATIONS:
        raise ValueError(
            "operation must be retention_scan|export_preview|destruction_preview"
        )
    return normalized


def _normalize_mode(value: str | None) -> str:
    normalized = str(value or "preview").strip().lower()
    if normalized not in COMPLIANCE_LIFECYCLE_MODES:
        raise ValueError("run_mode must be preview|manual")
    return normalized


def _normalize_status(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in COMPLIANCE_LIFECYCLE_STATUSES:
        raise ValueError("status must be running|completed|failed")
    return normalized


def create_lifecycle_run(
    db: Session,
    *,
    scope: str,
    data_class: str,
    operation: str,
    client_id: UUID,
    branch_id: UUID | None,
    company_id: UUID | None,
    domain_key: str | None,
    policy_version_id: UUID | None,
    policy_scope: str | None,
    policy_schema_version: str | None,
    policy_snapshot: dict[str, Any] | None,
    actor_id: UUID | None,
    run_mode: str | None = None,
) -> ComplianceLifecycleRun:
    normalized_scope = _normalize_scope(scope, branch_id=branch_id)
    normalized_data_class = _normalize_data_class(data_class)
    normalized_operation = _normalize_operation(operation)
    normalized_mode = _normalize_mode(run_mode)
    normalized_domain = (
        str(domain_key).strip().lower()
        if isinstance(domain_key, str) and str(domain_key).strip()
        else None
    )
    now = datetime.now(timezone.utc)
    record = ComplianceLifecycleRun(
        scope=normalized_scope,
        data_class=normalized_data_class,
        operation=normalized_operation,
        run_mode=normalized_mode,
        status="running",
        company_id=company_id,
        domain_key=normalized_domain,
        client_id=client_id,
        branch_id=branch_id,
        policy_version_id=policy_version_id,
        policy_scope=policy_scope,
        policy_schema_version=policy_schema_version,
        policy_snapshot_json=policy_snapshot or {},
        summary_json={},
        started_at=now,
        finished_at=now,
        triggered_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    db.flush()
    return record


def append_lifecycle_record(
    db: Session,
    *,
    run_id: UUID,
    entity_type: str,
    entity_id: str | UUID | None,
    action: str,
    result: str,
    payload: dict[str, Any] | None,
) -> ComplianceLifecycleRecord:
    normalized_result = str(result or "").strip().lower()
    if normalized_result not in COMPLIANCE_LIFECYCLE_RECORD_RESULTS:
        raise ValueError("result must be candidate|skipped|error")
    now = datetime.now(timezone.utc)
    record = ComplianceLifecycleRecord(
        run_id=run_id,
        entity_type=str(entity_type or "").strip() or "unknown",
        entity_id=str(entity_id) if entity_id is not None else None,
        action=str(action or "").strip() or "unknown",
        result=normalized_result,
        payload_json=payload or {},
        occurred_at=now,
    )
    db.add(record)
    db.flush()
    return record


def finalize_lifecycle_run(
    db: Session,
    *,
    run: ComplianceLifecycleRun,
    status: str,
    summary: dict[str, Any] | None,
    error_message: str | None = None,
) -> ComplianceLifecycleRun:
    now = datetime.now(timezone.utc)
    run.status = _normalize_status(status)
    run.summary_json = summary or {}
    run.error_message = (
        str(error_message).strip()
        if isinstance(error_message, str) and str(error_message).strip()
        else None
    )
    run.finished_at = now
    run.updated_at = now
    db.flush()
    return run


def list_lifecycle_runs(
    db: Session,
    *,
    client_id: UUID,
    scope: str,
    branch_id: UUID | None,
    data_class: str | None,
    operation: str | None,
    limit: int = 20,
) -> list[ComplianceLifecycleRun]:
    normalized_scope = _normalize_scope(scope, branch_id=branch_id)
    query = db.query(ComplianceLifecycleRun).filter(
        ComplianceLifecycleRun.client_id == client_id,
        ComplianceLifecycleRun.scope == normalized_scope,
    )
    if normalized_scope == "branch":
        query = query.filter(ComplianceLifecycleRun.branch_id == branch_id)
    else:
        query = query.filter(ComplianceLifecycleRun.branch_id.is_(None))
    if data_class:
        query = query.filter(
            ComplianceLifecycleRun.data_class == _normalize_data_class(data_class)
        )
    if operation:
        query = query.filter(
            ComplianceLifecycleRun.operation == _normalize_operation(operation)
        )
    return query.order_by(ComplianceLifecycleRun.created_at.desc()).limit(
        max(1, min(limit, 200))
    ).all()


def get_lifecycle_run(
    db: Session,
    *,
    run_id: UUID,
    client_id: UUID,
    scope: str,
    branch_id: UUID | None,
) -> ComplianceLifecycleRun | None:
    normalized_scope = _normalize_scope(scope, branch_id=branch_id)
    query = db.query(ComplianceLifecycleRun).filter(
        ComplianceLifecycleRun.id == run_id,
        ComplianceLifecycleRun.client_id == client_id,
        ComplianceLifecycleRun.scope == normalized_scope,
    )
    if normalized_scope == "branch":
        query = query.filter(ComplianceLifecycleRun.branch_id == branch_id)
    else:
        query = query.filter(ComplianceLifecycleRun.branch_id.is_(None))
    return query.first()


def list_lifecycle_records(
    db: Session,
    *,
    run_id: UUID,
    limit: int = 200,
) -> list[ComplianceLifecycleRecord]:
    return (
        db.query(ComplianceLifecycleRecord)
        .filter(ComplianceLifecycleRecord.run_id == run_id)
        .order_by(ComplianceLifecycleRecord.occurred_at.desc())
        .limit(max(1, min(limit, 1000)))
        .all()
    )


def _due_learned_responses_query(
    db: Session,
    *,
    client_id: UUID,
    branch_id: UUID | None,
    now: datetime,
) -> Query:
    query = db.query(LearnedResponse).filter(
        LearnedResponse.client_id == client_id,
        LearnedResponse.is_active.is_(True),
        LearnedResponse.retention_expires_at.isnot(None),
        LearnedResponse.retention_expires_at <= now,
    )
    if branch_id is not None:
        query = query.filter(LearnedResponse.branch_id == branch_id)
    return query


def _resolve_execution_action(
    *,
    operation: str,
    run_mode: str,
    destruction_mode: str | None,
) -> str:
    if operation == "retention_scan":
        return "retention_scan"
    if operation == "export_preview":
        return "export_preview" if run_mode == "preview" else "export_package"
    if operation == "destruction_preview":
        if run_mode == "preview":
            return "destruction_preview"
        token = str(destruction_mode or "delete").strip().lower()
        return _DESTRUCTION_EXECUTION_ACTIONS.get(token, "deactivate_record")
    return operation


def _apply_learned_response_action(
    *,
    item: LearnedResponse,
    operation: str,
    destruction_mode: str | None,
    now: datetime,
) -> dict[str, Any]:
    if operation == "retention_scan":
        return {"applied": False, "action_status": "scan_only"}
    if operation == "export_preview":
        export_ref = f"learned_response:{item.id}:{int(now.timestamp())}"
        return {"applied": True, "action_status": "exported", "export_ref": export_ref}

    normalized_mode = str(destruction_mode or "delete").strip().lower()
    if normalized_mode == "anonymize":
        item.question_text = "[anonymized]"
        item.response_text = "[anonymized]"
        item.source_name = None
        item.source_channel = None
        item.redaction_summary = {
            "mode": "anonymize",
            "applied_at": now.isoformat(),
        }
        item.is_active = False
        item.updated_at = now
        return {"applied": True, "action_status": "anonymized"}
    if normalized_mode == "archive":
        item.is_active = False
        item.status = "rejected"
        item.updated_at = now
        return {"applied": True, "action_status": "archived"}

    item.is_active = False
    item.updated_at = now
    return {"applied": True, "action_status": "deactivated"}


def execute_lifecycle_preview(
    db: Session,
    *,
    run: ComplianceLifecycleRun,
    max_items: int,
    apply_actions: bool = False,
) -> dict[str, Any]:
    if run.data_class != "learned_responses":
        raise ValueError("unsupported data_class")

    now = datetime.now(timezone.utc)
    capped_limit = max(1, min(int(max_items), 500))
    due_items = (
        _due_learned_responses_query(
            db,
            client_id=run.client_id,
            branch_id=run.branch_id,
            now=now,
        )
        .order_by(LearnedResponse.retention_expires_at.asc(), LearnedResponse.created_at.asc())
        .limit(capped_limit)
        .all()
    )

    run_mode = str(getattr(run, "run_mode", "preview") or "preview").strip().lower()
    if run_mode not in COMPLIANCE_LIFECYCLE_MODES:
        run_mode = "preview"

    action = run.operation
    policy_mode = (run.policy_snapshot_json or {}).get("destruction_mode")
    execution_action = _resolve_execution_action(
        operation=run.operation,
        run_mode=run_mode,
        destruction_mode=str(policy_mode) if policy_mode is not None else None,
    )
    should_apply_actions = bool(apply_actions and run_mode == "manual")
    created = 0
    applied_count = 0
    skipped_count = 0
    error_count = 0
    for item in due_items:
        payload = {
            "retention_expires_at": (
                item.retention_expires_at.isoformat()
                if item.retention_expires_at
                else None
            ),
            "consent_status": item.consent_status,
            "anonymization_mode": item.anonymization_mode,
            "execution_action": execution_action,
            "apply_actions": should_apply_actions,
        }
        if run.operation == "destruction_preview":
            payload["planned_destruction_mode"] = policy_mode or "delete"
        result = "candidate"
        if should_apply_actions:
            try:
                apply_result = _apply_learned_response_action(
                    item=item,
                    operation=run.operation,
                    destruction_mode=str(policy_mode) if policy_mode is not None else None,
                    now=now,
                )
                payload.update(apply_result)
                if apply_result.get("applied") is True:
                    applied_count += 1
                else:
                    result = "skipped"
                    skipped_count += 1
            except Exception as exc:
                payload["apply_error"] = str(exc)
                result = "error"
                error_count += 1
        else:
            payload["applied"] = False
        append_lifecycle_record(
            db,
            run_id=run.id,
            entity_type="learned_response",
            entity_id=item.id,
            action=action,
            result=result,
            payload=payload,
        )
        if result == "candidate":
            created += 1

    return {
        "candidate_count": created,
        "applied_count": applied_count,
        "skipped_count": skipped_count,
        "error_count": error_count,
        "max_items": capped_limit,
        "evaluated_at": now.isoformat(),
        "operation": run.operation,
        "run_mode": run_mode,
        "execution_action": execution_action,
        "apply_actions": should_apply_actions,
        "data_class": run.data_class,
        "scope": run.scope,
    }


__all__ = [
    "create_lifecycle_run",
    "append_lifecycle_record",
    "finalize_lifecycle_run",
    "list_lifecycle_runs",
    "get_lifecycle_run",
    "list_lifecycle_records",
    "execute_lifecycle_preview",
]
