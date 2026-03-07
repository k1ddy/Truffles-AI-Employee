from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.console_saved_view import ConsoleSavedView
from app.services.console_errors import ConsoleAPIError
from app.services.console_queue_state import ConsoleQueueSurface

_MAX_SAVED_VIEW_NAME_LENGTH = 120


def normalize_saved_view_name(name: Any) -> str:
    if not isinstance(name, str):
        raise ConsoleAPIError(400, "INVALID_PARAM", "name is invalid")
    cleaned = name.strip()
    if not cleaned:
        raise ConsoleAPIError(400, "INVALID_PARAM", "name is required")
    if len(cleaned) > _MAX_SAVED_VIEW_NAME_LENGTH:
        raise ConsoleAPIError(400, "INVALID_PARAM", "name is too long")
    return cleaned


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
            ConsoleSavedView.agent_id == agent_id,
        )
        .first()
    )


def list_saved_views(
    db: Session,
    *,
    client_id: UUID,
    agent_id: UUID,
    surface: ConsoleQueueSurface,
) -> list[ConsoleSavedView]:
    return (
        db.query(ConsoleSavedView)
        .filter(
            ConsoleSavedView.client_id == client_id,
            ConsoleSavedView.agent_id == agent_id,
            ConsoleSavedView.surface == surface,
        )
        .order_by(ConsoleSavedView.is_default.desc(), ConsoleSavedView.updated_at.desc(), ConsoleSavedView.name.asc())
        .all()
    )


def _get_saved_view_by_name(
    db: Session,
    *,
    client_id: UUID,
    agent_id: UUID,
    surface: ConsoleQueueSurface,
    name: str,
) -> Optional[ConsoleSavedView]:
    return (
        db.query(ConsoleSavedView)
        .filter(
            ConsoleSavedView.client_id == client_id,
            ConsoleSavedView.agent_id == agent_id,
            ConsoleSavedView.surface == surface,
            ConsoleSavedView.name == name,
        )
        .first()
    )


def _clear_default_saved_views(
    db: Session,
    *,
    client_id: UUID,
    agent_id: UUID,
    surface: ConsoleQueueSurface,
    exclude_view_id: Optional[UUID] = None,
) -> None:
    current_default_views = (
        db.query(ConsoleSavedView)
        .filter(
            ConsoleSavedView.client_id == client_id,
            ConsoleSavedView.agent_id == agent_id,
            ConsoleSavedView.surface == surface,
            ConsoleSavedView.is_default.is_(True),
        )
        .all()
    )
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
    agent_id: UUID,
    surface: ConsoleQueueSurface,
    name: str,
    version: int,
    query_state: dict[str, Any],
    is_default: bool,
) -> ConsoleSavedView:
    normalized_name = normalize_saved_view_name(name)
    existing = _get_saved_view_by_name(
        db,
        client_id=client_id,
        agent_id=agent_id,
        surface=surface,
        name=normalized_name,
    )
    if existing is not None:
        raise ConsoleAPIError(409, "CONFLICT", "Saved view name already exists")
    if is_default:
        _clear_default_saved_views(
            db,
            client_id=client_id,
            agent_id=agent_id,
            surface=surface,
        )
    record = ConsoleSavedView(
        client_id=client_id,
        agent_id=agent_id,
        surface=surface,
        name=normalized_name,
        version=version,
        query_state=query_state,
        is_default=is_default,
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
) -> ConsoleSavedView:
    if name is not None:
        normalized_name = normalize_saved_view_name(name)
        if normalized_name != record.name:
            existing = _get_saved_view_by_name(
                db,
                client_id=record.client_id,
                agent_id=record.agent_id,
                surface=record.surface,
                name=normalized_name,
            )
            if existing is not None and existing.id != record.id:
                raise ConsoleAPIError(409, "CONFLICT", "Saved view name already exists")
            record.name = normalized_name
    if version is not None:
        record.version = version
    if query_state is not None:
        record.query_state = query_state
    if is_default is not None:
        if is_default:
            _clear_default_saved_views(
                db,
                client_id=record.client_id,
                agent_id=record.agent_id,
                surface=record.surface,
                exclude_view_id=record.id,
            )
        record.is_default = is_default
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
