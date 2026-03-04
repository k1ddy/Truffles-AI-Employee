import json
from typing import Mapping
from uuid import UUID

from app.models import Branch, ConsoleBranchChange
from app.schemas.console import ConsoleBranchChangeRecord, ConsoleBranchUpdateRequest

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


def build_branch_update_request(
    *,
    normalized_patch: Mapping[str, object],
    confirmation_id: UUID | None = None,
) -> ConsoleBranchUpdateRequest:
    payload = dict(normalized_patch)
    if confirmation_id:
        payload["confirmation_id"] = confirmation_id
    return ConsoleBranchUpdateRequest.model_validate(payload)
