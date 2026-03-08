from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.console_saved_view import ConsoleSavedView
from app.services.console_errors import ConsoleAPIError
from app.services.console_queue_state import ConsoleQueueSurface

SavedViewScope = Literal["personal", "team"]

_MAX_SAVED_VIEW_NAME_LENGTH = 120
_ALLOWED_SAVED_VIEW_SCOPES = {"personal", "team"}
_UNSET = object()


def normalize_saved_view_name(name: Any) -> str:
    if not isinstance(name, str):
        raise ConsoleAPIError(400, "INVALID_PARAM", "name is invalid")
    cleaned = name.strip()
    if not cleaned:
        raise ConsoleAPIError(400, "INVALID_PARAM", "name is required")
    if len(cleaned) > _MAX_SAVED_VIEW_NAME_LENGTH:
        raise ConsoleAPIError(400, "INVALID_PARAM", "name is too long")
    return cleaned


def normalize_saved_view_scope(scope: Any) -> SavedViewScope:
    cleaned = str(scope or "personal").strip().lower()
    if cleaned not in _ALLOWED_SAVED_VIEW_SCOPES:
        raise ConsoleAPIError(400, "INVALID_PARAM", "scope is invalid")
    return cleaned  # type: ignore[return-value]


def get_saved_view_for_client(
    db: Session,
    *,
    client_id: UUID,
    view_id: UUID,
) -> Optional[ConsoleSavedView]:
    return (
        db.query(ConsoleSavedView)
        .filter(
            ConsoleSavedView.id == view_id,
            ConsoleSavedView.client_id == client_id,
        )
        .first()
    )


def get_saved_view_for_owner(
    db: Session,
    *,
    client_id: UUID,
    agent_id: UUID,
    view_id: UUID,
) -> Optional[ConsoleSavedView]:
    return (
        db.query(ConsoleSavedView)
        .filter(
            ConsoleSavedView.id == view_id,
            ConsoleSavedView.client_id == client_id,
            ConsoleSavedView.scope == "personal",
            ConsoleSavedView.agent_id == agent_id,
        )
        .first()
    )


def saved_view_applies_to_context(
    record: ConsoleSavedView,
    *,
    role: str,
    current_branch_id: Optional[UUID],
) -> bool:
    scope = normalize_saved_view_scope(getattr(record, "scope", "personal"))
    if scope == "personal":
        return True
    target_role = getattr(record, "target_role", None)
    if target_role and target_role != role:
        return False
    target_branch_id = getattr(record, "target_branch_id", None)
    if target_branch_id is not None and target_branch_id != current_branch_id:
        return False
    return True


def saved_view_target_specificity(
    record: ConsoleSavedView,
    *,
    role: str,
    current_branch_id: Optional[UUID],
) -> int:
    if not saved_view_applies_to_context(record, role=role, current_branch_id=current_branch_id):
        return -1
    score = 0
    if getattr(record, "target_role", None) == role:
        score += 2
    if getattr(record, "target_branch_id", None) == current_branch_id and current_branch_id is not None:
        score += 1
    return score


def _updated_at_value(record: ConsoleSavedView) -> float:
    updated_at = getattr(record, "updated_at", None)
    if not updated_at:
        return 0
    return updated_at.timestamp()


def list_saved_views(
    db: Session,
    *,
    client_id: UUID,
    agent_id: UUID,
    surface: ConsoleQueueSurface,
    role: str,
    current_branch_id: Optional[UUID],
    include_all_team_presets: bool = False,
) -> list[ConsoleSavedView]:
    personal_views = (
        db.query(ConsoleSavedView)
        .filter(
            ConsoleSavedView.client_id == client_id,
            ConsoleSavedView.agent_id == agent_id,
            ConsoleSavedView.surface == surface,
            ConsoleSavedView.scope == "personal",
        )
        .all()
    )
    team_views = (
        db.query(ConsoleSavedView)
        .filter(
            ConsoleSavedView.client_id == client_id,
            ConsoleSavedView.surface == surface,
            ConsoleSavedView.scope == "team",
        )
        .all()
    )
    if not include_all_team_presets:
        team_views = [
            item
            for item in team_views
            if saved_view_applies_to_context(
                item,
                role=role,
                current_branch_id=current_branch_id,
            )
        ]

    personal_sorted = sorted(
        personal_views,
        key=lambda item: (
            0 if item.is_default else 1,
            -_updated_at_value(item),
            item.name.lower(),
        ),
    )
    team_sorted = sorted(
        team_views,
        key=lambda item: (
            0 if saved_view_applies_to_context(item, role=role, current_branch_id=current_branch_id) else 1,
            0 if item.is_default else 1,
            -saved_view_target_specificity(item, role=role, current_branch_id=current_branch_id),
            -_updated_at_value(item),
            item.name.lower(),
        ),
    )
    return team_sorted + personal_sorted


def _get_saved_view_by_name(
    db: Session,
    *,
    client_id: UUID,
    surface: ConsoleQueueSurface,
    scope: SavedViewScope,
    name: str,
    agent_id: Optional[UUID],
    target_branch_id: Optional[UUID],
    target_role: Optional[str],
) -> Optional[ConsoleSavedView]:
    query = (
        db.query(ConsoleSavedView)
        .filter(
            ConsoleSavedView.client_id == client_id,
            ConsoleSavedView.surface == surface,
            ConsoleSavedView.scope == scope,
            ConsoleSavedView.name == name,
        )
    )
    if scope == "personal":
        query = query.filter(ConsoleSavedView.agent_id == agent_id)
    else:
        if target_branch_id is None:
            query = query.filter(ConsoleSavedView.target_branch_id.is_(None))
        else:
            query = query.filter(ConsoleSavedView.target_branch_id == target_branch_id)
        if target_role is None:
            query = query.filter(ConsoleSavedView.target_role.is_(None))
        else:
            query = query.filter(ConsoleSavedView.target_role == target_role)
    return query.first()


def _clear_default_saved_views(
    db: Session,
    *,
    client_id: UUID,
    surface: ConsoleQueueSurface,
    scope: SavedViewScope,
    agent_id: Optional[UUID] = None,
    target_branch_id: Optional[UUID] = None,
    target_role: Optional[str] = None,
    exclude_view_id: Optional[UUID] = None,
) -> None:
    query = (
        db.query(ConsoleSavedView)
        .filter(
            ConsoleSavedView.client_id == client_id,
            ConsoleSavedView.surface == surface,
            ConsoleSavedView.scope == scope,
            ConsoleSavedView.is_default.is_(True),
        )
    )
    if scope == "personal":
        query = query.filter(ConsoleSavedView.agent_id == agent_id)
    else:
        if target_branch_id is None:
            query = query.filter(ConsoleSavedView.target_branch_id.is_(None))
        else:
            query = query.filter(ConsoleSavedView.target_branch_id == target_branch_id)
        if target_role is None:
            query = query.filter(ConsoleSavedView.target_role.is_(None))
        else:
            query = query.filter(ConsoleSavedView.target_role == target_role)

    current_default_views = query.all()
    now = datetime.now(timezone.utc)
    for item in current_default_views:
        if exclude_view_id and item.id == exclude_view_id:
            continue
        item.is_default = False
        item.updated_at = now
        db.add(item)


def create_saved_view(
    db: Session,
    *,
    client_id: UUID,
    agent_id: Optional[UUID],
    created_by_agent_id: UUID,
    surface: ConsoleQueueSurface,
    scope: SavedViewScope,
    name: str,
    version: int,
    query_state: dict[str, Any],
    is_default: bool,
    target_branch_id: Optional[UUID] = None,
    target_role: Optional[str] = None,
) -> ConsoleSavedView:
    normalized_scope = normalize_saved_view_scope(scope)
    normalized_name = normalize_saved_view_name(name)
    if normalized_scope == "personal":
        if agent_id is None:
            raise ConsoleAPIError(400, "INVALID_PARAM", "agent_id is required for personal saved views")
        target_branch_id = None
        target_role = None
    else:
        agent_id = None

    existing = _get_saved_view_by_name(
        db,
        client_id=client_id,
        surface=surface,
        scope=normalized_scope,
        name=normalized_name,
        agent_id=agent_id,
        target_branch_id=target_branch_id,
        target_role=target_role,
    )
    if existing is not None:
        raise ConsoleAPIError(409, "CONFLICT", "Saved view name already exists")
    if is_default:
        _clear_default_saved_views(
            db,
            client_id=client_id,
            surface=surface,
            scope=normalized_scope,
            agent_id=agent_id,
            target_branch_id=target_branch_id,
            target_role=target_role,
        )
    record = ConsoleSavedView(
        client_id=client_id,
        agent_id=agent_id,
        created_by_agent_id=created_by_agent_id,
        surface=surface,
        scope=normalized_scope,
        name=normalized_name,
        version=version,
        query_state=query_state,
        is_default=is_default,
        target_branch_id=target_branch_id,
        target_role=target_role,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_saved_view(
    db: Session,
    *,
    record: ConsoleSavedView,
    name: Optional[str] = None,
    version: Optional[int] = None,
    query_state: Optional[dict[str, Any]] = None,
    is_default: Optional[bool] = None,
    target_branch_id: Optional[UUID] | object = _UNSET,
    target_role: Optional[str] | object = _UNSET,
) -> ConsoleSavedView:
    scope = normalize_saved_view_scope(getattr(record, "scope", "personal"))
    next_name = record.name
    if name is not None:
        next_name = normalize_saved_view_name(name)

    if scope == "personal":
        next_target_branch_id = None
        next_target_role = None
        if target_branch_id is not _UNSET or target_role is not _UNSET:
            raise ConsoleAPIError(400, "INVALID_PARAM", "Personal saved views do not support team targeting")
    else:
        next_target_branch_id = record.target_branch_id if target_branch_id is _UNSET else target_branch_id
        next_target_role = record.target_role if target_role is _UNSET else target_role

    if (
        next_name != record.name
        or next_target_branch_id != record.target_branch_id
        or next_target_role != record.target_role
    ):
        existing = _get_saved_view_by_name(
            db,
            client_id=record.client_id,
            surface=record.surface,
            scope=scope,
            name=next_name,
            agent_id=record.agent_id if scope == "personal" else None,
            target_branch_id=next_target_branch_id,
            target_role=next_target_role,
        )
        if existing is not None and existing.id != record.id:
            raise ConsoleAPIError(409, "CONFLICT", "Saved view name already exists")
        record.name = next_name

    if version is not None:
        record.version = version
    if query_state is not None:
        record.query_state = query_state
    if scope == "team":
        if target_branch_id is not _UNSET:
            record.target_branch_id = next_target_branch_id
        if target_role is not _UNSET:
            record.target_role = next_target_role
    if is_default is not None:
        if is_default:
            _clear_default_saved_views(
                db,
                client_id=record.client_id,
                surface=record.surface,
                scope=scope,
                agent_id=record.agent_id if scope == "personal" else None,
                target_branch_id=record.target_branch_id if scope == "team" else None,
                target_role=record.target_role if scope == "team" else None,
                exclude_view_id=record.id,
            )
        record.is_default = is_default
    elif record.is_default:
        _clear_default_saved_views(
            db,
            client_id=record.client_id,
            surface=record.surface,
            scope=scope,
            agent_id=record.agent_id if scope == "personal" else None,
            target_branch_id=record.target_branch_id if scope == "team" else None,
            target_role=record.target_role if scope == "team" else None,
            exclude_view_id=record.id,
        )
    record.updated_at = datetime.now(timezone.utc)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_saved_view(
    db: Session,
    *,
    record: ConsoleSavedView,
) -> None:
    db.delete(record)
    db.commit()
