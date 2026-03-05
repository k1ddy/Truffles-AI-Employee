import json
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Branch, ConsoleBranchChange
from app.schemas.console import (
    ConsoleBranchChangeListResponse,
    ConsoleBranchChangeRecord,
    ConsoleBranchUpdateRequest,
)

BRANCH_CHANGE_MANAGED_FIELDS: tuple[str, ...] = (
    "slug",
    "name",
    "timezone",
    "instance_id",
    "phone",
    "telegram_chat_id",
    "knowledge_tag",
    "working_hours",
    "booking_settings",
    "is_active",
)

BRANCH_CHANGE_MUTABLE_STATUSES = {"draft", "validated", "publish_failed"}
BRANCH_CHANGE_ALLOWED_STATUSES = {"draft", "validated", "publish_failed", "published", "rolled_back"}


def _jsonable_payload(value: object) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        raw = value
    else:
        raw = {"value": value}
    return json.loads(json.dumps(raw, default=str))


def snapshot_branch_for_change(branch: Branch) -> dict:
    return {
        "slug": branch.slug,
        "name": branch.name,
        "timezone": branch.timezone,
        "instance_id": branch.instance_id,
        "phone": branch.phone,
        "telegram_chat_id": branch.telegram_chat_id,
        "knowledge_tag": branch.knowledge_tag,
        "working_hours": _jsonable_payload(branch.working_hours if isinstance(branch.working_hours, dict) else {}),
        "booking_settings": _jsonable_payload(branch.booking_settings if isinstance(branch.booking_settings, dict) else {}),
        "is_active": bool(branch.is_active),
    }


def build_branch_change_diff(base_snapshot: Mapping[str, object], patch_payload: Mapping[str, object]) -> dict[str, dict[str, object]]:
    diff: dict[str, dict[str, object]] = {}
    for field in BRANCH_CHANGE_MANAGED_FIELDS:
        if field not in patch_payload:
            continue
        before = base_snapshot.get(field)
        after = patch_payload.get(field)
        if before == after:
            continue
        diff[field] = {
            "before": before,
            "after": after,
        }
    return diff


def serialize_branch_change_record(change: ConsoleBranchChange) -> ConsoleBranchChangeRecord:
    return ConsoleBranchChangeRecord(
        id=change.id,
        branch_id=change.branch_id,
        status=change.status,
        reason=change.reason,
        draft_payload=change.draft_payload if isinstance(change.draft_payload, dict) else {},
        diff_payload=change.diff_payload if isinstance(change.diff_payload, dict) else {},
        validation_payload=change.validation_payload if isinstance(change.validation_payload, dict) else None,
        base_snapshot=change.base_snapshot if isinstance(change.base_snapshot, dict) else {},
        published_snapshot=change.published_snapshot if isinstance(change.published_snapshot, dict) else None,
        rollback_snapshot=change.rollback_snapshot if isinstance(change.rollback_snapshot, dict) else None,
        publish_error=change.publish_error,
        rollback_error=change.rollback_error,
        created_at=change.created_at.isoformat() if change.created_at else "",
        updated_at=change.updated_at.isoformat() if change.updated_at else None,
        validated_at=change.validated_at.isoformat() if change.validated_at else None,
        published_at=change.published_at.isoformat() if change.published_at else None,
        rolled_back_at=change.rolled_back_at.isoformat() if change.rolled_back_at else None,
    )


def query_branch_changes_for_context(
    *,
    db: Session,
    client_id: UUID,
    branch_id: UUID | None = None,
    allowed_branch_ids: list[UUID] | None = None,
) -> Any:
    query = db.query(ConsoleBranchChange).filter(ConsoleBranchChange.client_id == client_id)
    if branch_id is not None:
        query = query.filter(ConsoleBranchChange.branch_id == branch_id)
    if allowed_branch_ids is not None:
        if not allowed_branch_ids:
            return None
        query = query.filter(ConsoleBranchChange.branch_id.in_(allowed_branch_ids))
    return query


def get_branch_change_for_context(
    *,
    db: Session,
    change_id: UUID,
    client_id: UUID,
    allowed_branch_ids: list[UUID] | None = None,
) -> ConsoleBranchChange | None:
    query = query_branch_changes_for_context(
        db=db,
        client_id=client_id,
        allowed_branch_ids=allowed_branch_ids,
    )
    if query is None:
        return None
    return query.filter(ConsoleBranchChange.id == change_id).first()


def build_branch_change_rollback_patch(
    *,
    base_snapshot: Mapping[str, object],
    current_snapshot: Mapping[str, object],
) -> dict[str, object]:
    return {
        field: base_snapshot.get(field)
        for field in BRANCH_CHANGE_MANAGED_FIELDS
        if field in base_snapshot and current_snapshot.get(field) != base_snapshot.get(field)
    }


def normalize_branch_change_status_filter(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in BRANCH_CHANGE_ALLOWED_STATUSES:
        raise ValueError("Invalid status")
    return normalized


def build_branch_change_list_response(
    *,
    query: Any,
    status: str | None,
    cursor_date: datetime | None,
    limit: int,
) -> ConsoleBranchChangeListResponse:
    normalized_status = normalize_branch_change_status_filter(status)
    if normalized_status:
        query = query.filter(ConsoleBranchChange.status == normalized_status)
    if cursor_date is not None:
        query = query.filter(ConsoleBranchChange.created_at < cursor_date)

    rows = (
        query.order_by(ConsoleBranchChange.created_at.desc(), ConsoleBranchChange.id.desc())
        .limit(limit + 1)
        .all()
    )
    has_more = len(rows) > limit
    items_rows = rows[:limit]
    next_cursor = items_rows[-1].created_at.isoformat() if has_more and items_rows else None
    return ConsoleBranchChangeListResponse(
        items=[serialize_branch_change_record(row) for row in items_rows],
        cursor=next_cursor,
        has_more=has_more,
    )


def build_branch_update_request(
    *,
    normalized_patch: Mapping[str, object],
    confirmation_id: UUID | None = None,
) -> ConsoleBranchUpdateRequest:
    payload = dict(normalized_patch)
    if confirmation_id:
        payload["confirmation_id"] = confirmation_id
    return ConsoleBranchUpdateRequest.model_validate(payload)


def apply_branch_change_validation_result(
    *,
    change: ConsoleBranchChange,
    branch: Branch,
    normalized_patch: Mapping[str, object],
    diff_payload: Mapping[str, Mapping[str, object]],
    base_snapshot: Mapping[str, object],
    errors: list[str],
    now: datetime,
) -> None:
    change.draft_payload = _jsonable_payload(normalized_patch)
    change.diff_payload = _jsonable_payload(diff_payload)
    change.base_snapshot = _jsonable_payload(base_snapshot)
    change.base_branch_updated_at = branch.updated_at
    change.validation_payload = {
        "ok": len(errors) == 0,
        "errors": errors,
    }
    change.status = "validated" if not errors else "draft"
    change.validated_at = now if not errors else None
    change.updated_at = now


def apply_branch_change_publish_failed_state(
    *,
    change: ConsoleBranchChange,
    errors: list[str],
    now: datetime,
) -> str:
    message = "; ".join(errors)
    change.status = "publish_failed"
    change.publish_error = message
    change.validation_payload = {"ok": False, "errors": errors}
    change.updated_at = now
    return message


def apply_branch_change_publish_runtime_error_state(
    *,
    change: ConsoleBranchChange,
    error_message: str,
    now: datetime,
) -> None:
    change.status = "publish_failed"
    change.publish_error = error_message
    change.updated_at = now


def apply_branch_change_published_state(
    *,
    change: ConsoleBranchChange,
    published_snapshot: Mapping[str, object] | None,
    actor_id: UUID,
    now: datetime,
) -> None:
    change.status = "published"
    change.publish_error = None
    change.published_snapshot = _jsonable_payload(published_snapshot) if published_snapshot is not None else None
    change.published_at = now
    change.published_by = actor_id
    change.updated_at = now


def apply_branch_change_rollback_failed_state(
    *,
    change: ConsoleBranchChange,
    error_message: str,
    now: datetime,
) -> None:
    change.rollback_error = error_message
    change.updated_at = now


def apply_branch_change_rolled_back_state(
    *,
    change: ConsoleBranchChange,
    rollback_snapshot: Mapping[str, object],
    actor_id: UUID,
    now: datetime,
) -> None:
    change.status = "rolled_back"
    change.rollback_error = None
    change.rollback_snapshot = _jsonable_payload(rollback_snapshot)
    change.rolled_back_at = now
    change.rolled_back_by = actor_id
    change.updated_at = now


def _error_message(exc: Exception) -> str:
    message = getattr(exc, "message", None)
    return str(message) if message else str(exc)


def normalize_branch_change_patch(
    *,
    db: Session,
    branch: Branch,
    patch_payload: Mapping[str, object],
    validation_error_type: type[Exception],
    ensure_unique_branch_field: Callable[..., None],
    normalize_slug: Callable[[str, str], str],
    normalize_required_text: Callable[[str, str], str],
    normalize_timezone_name: Callable[[str | None, str], str | None],
    normalize_optional_text: Callable[[str | None], str | None],
    normalize_branch_phone: Callable[[str | None, str], str | None],
    normalize_telegram_chat_id: Callable[[str | None, str], str | None],
    normalize_knowledge_tag: Callable[[str | None, str], str | None],
    require_branch_go_live_gate: Callable[[Branch], None],
    require_branch_scorecard_ready: Callable[[Session, Branch], None],
) -> tuple[dict[str, object], list[str]]:
    errors: list[str] = []
    normalized: dict[str, object] = {}

    if not isinstance(patch_payload, Mapping):
        return {}, ["patch must be an object"]

    if not any(field in patch_payload for field in BRANCH_CHANGE_MANAGED_FIELDS):
        return {}, ["patch has no supported fields"]

    if "slug" in patch_payload:
        raw_slug = patch_payload.get("slug")
        if raw_slug is None:
            errors.append("slug cannot be null")
        elif not isinstance(raw_slug, str):
            errors.append("slug must be string")
        else:
            try:
                slug = normalize_slug(raw_slug, "branch_slug")
            except validation_error_type as exc:
                errors.append(_error_message(exc))
            else:
                ensure_unique_branch_field(
                    db,
                    client_id=branch.client_id,
                    field_name="slug",
                    value=slug,
                    exclude_branch_id=branch.id,
                )
                normalized["slug"] = slug

    if "name" in patch_payload:
        raw_name = patch_payload.get("name")
        if raw_name is None:
            errors.append("name cannot be null")
        elif not isinstance(raw_name, str):
            errors.append("name must be string")
        else:
            try:
                normalized["name"] = normalize_required_text(raw_name, "name")
            except validation_error_type as exc:
                errors.append(_error_message(exc))

    if "timezone" in patch_payload:
        raw_timezone = patch_payload.get("timezone")
        if raw_timezone is not None and not isinstance(raw_timezone, str):
            errors.append("timezone must be string")
        else:
            try:
                normalized["timezone"] = normalize_timezone_name(raw_timezone, "timezone")
            except validation_error_type as exc:
                errors.append(_error_message(exc))

    if "instance_id" in patch_payload:
        raw_instance_id = patch_payload.get("instance_id")
        if raw_instance_id is not None and not isinstance(raw_instance_id, str):
            errors.append("instance_id must be string")
        else:
            instance_id = normalize_optional_text(raw_instance_id)
            ensure_unique_branch_field(
                db,
                client_id=branch.client_id,
                field_name="instance_id",
                value=instance_id,
                exclude_branch_id=branch.id,
            )
            normalized["instance_id"] = instance_id

    if "phone" in patch_payload:
        raw_phone = patch_payload.get("phone")
        if raw_phone is not None and not isinstance(raw_phone, str):
            errors.append("phone must be string")
        else:
            try:
                phone = normalize_branch_phone(raw_phone, "phone")
            except validation_error_type as exc:
                errors.append(_error_message(exc))
            else:
                ensure_unique_branch_field(
                    db,
                    client_id=branch.client_id,
                    field_name="phone",
                    value=phone,
                    exclude_branch_id=branch.id,
                )
                normalized["phone"] = phone

    if "telegram_chat_id" in patch_payload:
        raw_chat_id = patch_payload.get("telegram_chat_id")
        if raw_chat_id is not None and not isinstance(raw_chat_id, str):
            errors.append("telegram_chat_id must be string")
        else:
            try:
                normalized["telegram_chat_id"] = normalize_telegram_chat_id(raw_chat_id, "telegram_chat_id")
            except validation_error_type as exc:
                errors.append(_error_message(exc))

    if "knowledge_tag" in patch_payload:
        raw_knowledge_tag = patch_payload.get("knowledge_tag")
        if raw_knowledge_tag is not None and not isinstance(raw_knowledge_tag, str):
            errors.append("knowledge_tag must be string")
        else:
            try:
                normalized["knowledge_tag"] = normalize_knowledge_tag(raw_knowledge_tag, "knowledge_tag")
            except validation_error_type as exc:
                errors.append(_error_message(exc))

    if "working_hours" in patch_payload:
        value = patch_payload.get("working_hours")
        if value is None:
            normalized["working_hours"] = {}
        elif isinstance(value, dict):
            normalized["working_hours"] = value
        else:
            errors.append("working_hours must be an object")

    if "booking_settings" in patch_payload:
        value = patch_payload.get("booking_settings")
        if value is None:
            normalized["booking_settings"] = {}
        elif isinstance(value, dict):
            normalized["booking_settings"] = value
        else:
            errors.append("booking_settings must be an object")

    if "is_active" in patch_payload:
        value = patch_payload.get("is_active")
        if value is None:
            errors.append("is_active cannot be null")
        elif isinstance(value, bool):
            normalized["is_active"] = value
        else:
            errors.append("is_active must be boolean")

    final_instance_id = normalized.get("instance_id") if "instance_id" in normalized else branch.instance_id
    final_is_active = normalized.get("is_active") if "is_active" in normalized else bool(branch.is_active)
    if final_is_active and not final_instance_id:
        errors.append("instance_id required to activate branch")
    if final_is_active and not branch.is_active:
        try:
            require_branch_go_live_gate(branch)
            require_branch_scorecard_ready(db, branch)
        except validation_error_type as exc:
            errors.append(_error_message(exc))

    return normalized, errors


def prepare_branch_change_payload(
    *,
    db: Session,
    branch: Branch,
    patch_payload: Mapping[str, object],
    validation_error_type: type[Exception],
    ensure_unique_branch_field: Callable[..., None],
    normalize_slug: Callable[[str, str], str],
    normalize_required_text: Callable[[str, str], str],
    normalize_timezone_name: Callable[[str | None, str], str | None],
    normalize_optional_text: Callable[[str | None], str | None],
    normalize_branch_phone: Callable[[str | None, str], str | None],
    normalize_telegram_chat_id: Callable[[str | None, str], str | None],
    normalize_knowledge_tag: Callable[[str | None, str], str | None],
    require_branch_go_live_gate: Callable[[Branch], None],
    require_branch_scorecard_ready: Callable[[Session, Branch], None],
) -> tuple[dict[str, object], list[str], dict[str, dict[str, object]], dict[str, object]]:
    try:
        normalized_patch, errors = normalize_branch_change_patch(
            db=db,
            branch=branch,
            patch_payload=patch_payload,
            validation_error_type=validation_error_type,
            ensure_unique_branch_field=ensure_unique_branch_field,
            normalize_slug=normalize_slug,
            normalize_required_text=normalize_required_text,
            normalize_timezone_name=normalize_timezone_name,
            normalize_optional_text=normalize_optional_text,
            normalize_branch_phone=normalize_branch_phone,
            normalize_telegram_chat_id=normalize_telegram_chat_id,
            normalize_knowledge_tag=normalize_knowledge_tag,
            require_branch_go_live_gate=require_branch_go_live_gate,
            require_branch_scorecard_ready=require_branch_scorecard_ready,
        )
    except validation_error_type as exc:
        normalized_patch, errors = {}, [_error_message(exc)]

    base_snapshot = snapshot_branch_for_change(branch)
    diff_payload = build_branch_change_diff(base_snapshot, normalized_patch)
    if not diff_payload:
        errors.append("No effective branch changes detected")
    return normalized_patch, errors, diff_payload, base_snapshot
