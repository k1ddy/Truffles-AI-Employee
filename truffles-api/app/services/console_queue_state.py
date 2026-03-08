from dataclasses import dataclass
from datetime import date as dt_date
from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.console_queue_state import ConsoleQueueState
from app.services.console_auth import ConsoleAuthContext
from app.services.console_errors import ConsoleAPIError

ConsoleQueueSurface = Literal["cases", "calendar"]

_CASE_MODE_SCOPE_VALUES = {"open", "resolved", "all"}
_CASE_BASE_VIEW_VALUES = {"all_open", "needs_reply", "waiting_client", "snoozed", "delivery"}
_CASE_OWNER_SCOPE_VALUES = {"all", "mine", "unassigned", "agent"}
_CASE_SORT_VALUES = {"activity", "created_at", "sla", "resolved_at"}
_CALENDAR_QUEUE_MODE_VALUES = {"ops", "history"}
_CALENDAR_QUEUE_LANE_VALUES = {"attention", "all"}
_CALENDAR_STATUS_FILTER_VALUES = {"all", "scheduled", "completed", "no_show", "cancelled"}


@dataclass(frozen=True)
class QueueStateScope:
    surface: ConsoleQueueSurface
    scope_key: str
    selected_branch_id: Optional[UUID]
    case_id: Optional[UUID]
    conversation_id: Optional[UUID]


def _normalize_uuid_like(value: Any, *, field_name: str) -> Optional[UUID]:
    if value in (None, ""):
        return None
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError as exc:  # pragma: no cover - exercised via router tests
            raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} is invalid") from exc
    raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} is invalid")


def _normalize_optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConsoleAPIError(400, "INVALID_PARAM", "query_state contains invalid text value")
    cleaned = value.strip()
    return cleaned or None


def _normalize_optional_date(value: Any, *, field_name: str) -> Optional[str]:
    cleaned = _normalize_optional_text(value)
    if cleaned is None:
        return None
    try:
        dt_date.fromisoformat(cleaned)
    except ValueError as exc:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} is invalid") from exc
    return cleaned


def _normalize_bool(value: Any, *, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} is invalid")


def _normalize_scope_branch_id(context: ConsoleAuthContext) -> Optional[UUID]:
    selected_branch_id = getattr(context, "selected_branch_id", None)
    if selected_branch_id:
        return selected_branch_id
    return getattr(getattr(context, "agent", None), "branch_id", None)


def build_queue_state_scope(
    context: ConsoleAuthContext,
    *,
    surface: str,
    case_id: Optional[UUID] = None,
    conversation_id: Optional[UUID] = None,
) -> QueueStateScope:
    if surface not in {"cases", "calendar"}:
        raise ConsoleAPIError(400, "INVALID_PARAM", "surface is invalid")
    if surface == "cases" and (case_id is not None or conversation_id is not None):
        raise ConsoleAPIError(400, "INVALID_PARAM", "cases queue state does not support case_id or conversation_id")

    selected_branch_id = _normalize_scope_branch_id(context)
    normalized_case_id = case_id if surface == "calendar" else None
    normalized_conversation_id = conversation_id if surface == "calendar" else None
    scope_key = "|".join(
        [
            f"role:{getattr(context, 'role', 'unknown') or 'unknown'}",
            f"branch:{selected_branch_id or 'all'}",
            f"case:{normalized_case_id or 'all'}",
            f"conversation:{normalized_conversation_id or 'all'}",
        ]
    )
    return QueueStateScope(
        surface=surface,
        scope_key=scope_key,
        selected_branch_id=selected_branch_id,
        case_id=normalized_case_id,
        conversation_id=normalized_conversation_id,
    )


def normalize_queue_state_payload(
    context: ConsoleAuthContext,
    *,
    surface: str,
    query_state: Optional[dict[str, Any]],
) -> dict[str, Any]:
    payload = query_state or {}
    if not isinstance(payload, dict):
        raise ConsoleAPIError(400, "INVALID_PARAM", "query_state must be an object")
    if surface == "cases":
        return _normalize_cases_queue_state(context, payload)
    if surface == "calendar":
        return _normalize_calendar_queue_state(payload)
    raise ConsoleAPIError(400, "INVALID_PARAM", "surface is invalid")


def _normalize_cases_queue_state(context: ConsoleAuthContext, payload: dict[str, Any]) -> dict[str, Any]:
    mode_scope = str(payload.get("mode_scope") or "open").strip().lower()
    if mode_scope not in _CASE_MODE_SCOPE_VALUES:
        raise ConsoleAPIError(400, "INVALID_PARAM", "query_state.mode_scope is invalid")

    base_view = str(payload.get("base_view") or "all_open").strip().lower()
    if base_view not in _CASE_BASE_VIEW_VALUES:
        raise ConsoleAPIError(400, "INVALID_PARAM", "query_state.base_view is invalid")

    owner_scope_raw = payload.get("owner_scope") or {}
    if not isinstance(owner_scope_raw, dict):
        raise ConsoleAPIError(400, "INVALID_PARAM", "query_state.owner_scope is invalid")
    owner_scope_kind = str(owner_scope_raw.get("kind") or "all").strip().lower()
    if owner_scope_kind not in _CASE_OWNER_SCOPE_VALUES:
        raise ConsoleAPIError(400, "INVALID_PARAM", "query_state.owner_scope.kind is invalid")

    privileged = getattr(context, "role", None) in {"platform_admin", "owner", "admin"}
    owner_scope_agent_id = _normalize_uuid_like(owner_scope_raw.get("agent_id"), field_name="query_state.owner_scope.agent_id")
    if owner_scope_kind == "agent" and owner_scope_agent_id is None:
        owner_scope_kind = "all"
    elif owner_scope_kind in {"unassigned", "agent"} and not privileged:
        owner_scope_kind = "all"
        owner_scope_agent_id = None
    elif owner_scope_kind != "agent":
        owner_scope_agent_id = None

    refinements_raw = payload.get("refinements") or {}
    if not isinstance(refinements_raw, dict):
        raise ConsoleAPIError(400, "INVALID_PARAM", "query_state.refinements is invalid")

    branch_id = _normalize_uuid_like(refinements_raw.get("branch_id"), field_name="query_state.refinements.branch_id")
    allowed_branch_ids = {branch_id_value for branch_id_value in getattr(context, "allowed_branch_ids", set()) if branch_id_value}
    if branch_id and allowed_branch_ids and branch_id not in allowed_branch_ids and not privileged:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Access to this branch denied")

    sort_by = _normalize_optional_text(refinements_raw.get("sort_by"))
    if sort_by is not None:
        sort_by = sort_by.lower()
        if sort_by not in _CASE_SORT_VALUES:
            raise ConsoleAPIError(400, "INVALID_PARAM", "query_state.refinements.sort_by is invalid")
        if mode_scope != "open" and sort_by == "sla":
            sort_by = None
        if mode_scope != "resolved" and sort_by == "resolved_at":
            sort_by = None

    return {
        "mode_scope": mode_scope,
        "base_view": base_view,
        "owner_scope": {
            "kind": owner_scope_kind,
            "agent_id": str(owner_scope_agent_id) if owner_scope_agent_id else None,
        },
        "refinements": {
            "branch_id": str(branch_id) if branch_id else None,
            "query": _normalize_optional_text(refinements_raw.get("query")),
            "has_delivery_error": _normalize_bool(
                refinements_raw.get("has_delivery_error"),
                field_name="query_state.refinements.has_delivery_error",
            ) if mode_scope == "open" else False,
            "has_pending_outbox": _normalize_bool(
                refinements_raw.get("has_pending_outbox"),
                field_name="query_state.refinements.has_pending_outbox",
            ) if mode_scope == "open" else False,
            "has_human_lock": _normalize_bool(
                refinements_raw.get("has_human_lock"),
                field_name="query_state.refinements.has_human_lock",
            ) if mode_scope == "open" else False,
            "date_from": _normalize_optional_date(
                refinements_raw.get("date_from"),
                field_name="query_state.refinements.date_from",
            ),
            "date_to": _normalize_optional_date(
                refinements_raw.get("date_to"),
                field_name="query_state.refinements.date_to",
            ),
            "sort_by": sort_by,
        },
    }


def _normalize_calendar_queue_state(payload: dict[str, Any]) -> dict[str, Any]:
    queue_mode = str(payload.get("queue_mode") or "ops").strip().lower()
    if queue_mode not in _CALENDAR_QUEUE_MODE_VALUES:
        raise ConsoleAPIError(400, "INVALID_PARAM", "query_state.queue_mode is invalid")

    queue_lane_default = "all" if queue_mode == "history" else "attention"
    queue_lane = str(payload.get("queue_lane") or queue_lane_default).strip().lower()
    if queue_lane not in _CALENDAR_QUEUE_LANE_VALUES:
        raise ConsoleAPIError(400, "INVALID_PARAM", "query_state.queue_lane is invalid")
    if queue_mode == "history":
        queue_lane = "all"

    status_filter = str(payload.get("status_filter") or "all").strip().lower()
    if status_filter not in _CALENDAR_STATUS_FILTER_VALUES:
        raise ConsoleAPIError(400, "INVALID_PARAM", "query_state.status_filter is invalid")
    follow_up_owner_id = _normalize_uuid_like(
        payload.get("follow_up_owner_id"),
        field_name="query_state.follow_up_owner_id",
    )

    return {
        "selected_date": _normalize_optional_date(
            payload.get("selected_date"),
            field_name="query_state.selected_date",
        ),
        "queue_mode": queue_mode,
        "queue_lane": queue_lane,
        "status_filter": status_filter,
        "query": _normalize_optional_text(payload.get("query")),
        "follow_up_owner_id": str(follow_up_owner_id) if follow_up_owner_id else None,
        "follow_up_overdue_only": _normalize_bool(
            payload.get("follow_up_overdue_only"),
            field_name="query_state.follow_up_overdue_only",
        ),
    }


def get_current_queue_state(
    db: Session,
    *,
    client_id: UUID,
    agent_id: UUID,
    surface: ConsoleQueueSurface,
    scope_key: str,
) -> Optional[ConsoleQueueState]:
    return (
        db.query(ConsoleQueueState)
        .filter(
            ConsoleQueueState.client_id == client_id,
            ConsoleQueueState.agent_id == agent_id,
            ConsoleQueueState.surface == surface,
            ConsoleQueueState.scope_key == scope_key,
        )
        .first()
    )


def upsert_current_queue_state(
    db: Session,
    *,
    client_id: UUID,
    agent_id: UUID,
    scope: QueueStateScope,
    version: int,
    query_state: dict[str, Any],
) -> ConsoleQueueState:
    record = get_current_queue_state(
        db,
        client_id=client_id,
        agent_id=agent_id,
        surface=scope.surface,
        scope_key=scope.scope_key,
    )
    if record is None:
        record = ConsoleQueueState(
            client_id=client_id,
            agent_id=agent_id,
            surface=scope.surface,
            scope_key=scope.scope_key,
        )
        db.add(record)

    record.selected_branch_id = scope.selected_branch_id
    record.case_id = scope.case_id
    record.conversation_id = scope.conversation_id
    record.version = version
    record.query_state = query_state
    record.updated_at = datetime.now(timezone.utc)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
