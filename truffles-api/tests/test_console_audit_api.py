from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.services.console_errors import ConsoleAPIError


class _Query:
    def __init__(self, rows):
        self._rows = list(rows)
        self.filters = []
        self.limit_value = None

    def filter(self, *exprs):
        self.filters.extend(exprs)
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def all(self):
        return list(self._rows)


def _mock_context(*, client_id, branch_ids=(), branch_restricted=True):
    return SimpleNamespace(
        role="owner",
        agent=SimpleNamespace(id=uuid4(), name="Agent"),
        client=SimpleNamespace(id=client_id),
        branch_restricted=branch_restricted,
        branches=[SimpleNamespace(id=branch_id) for branch_id in branch_ids],
    )


def _has_filter(query: _Query, column_name: str) -> bool:
    for expr in query.filters:
        if getattr(getattr(expr, "left", None), "name", None) == column_name:
            return True
    return False


@pytest.mark.asyncio
async def test_list_audit_events_applies_client_and_branch_filters(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    now = datetime.now(timezone.utc)
    row = SimpleNamespace(
        id=uuid4(),
        created_at=now,
        event_type="case_taken",
        actor_name="Agent",
        entity_type="case",
        entity_id=uuid4(),
        payload={"ok": True},
    )
    query = _Query([row])
    db = Mock()
    db.query.return_value = query

    context = _mock_context(client_id=client_id, branch_ids=(branch_id,), branch_restricted=True)
    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    response = await console_router.list_audit_events(
        request=Mock(query_params={}),
        db=db,
        limit=50,
    )

    assert len(response.items) == 1
    assert response.items[0].event_type == "case_taken"
    assert response.has_more is False
    assert query.limit_value == 51
    assert _has_filter(query, "client_id")
    assert _has_filter(query, "branch_id")


@pytest.mark.asyncio
async def test_list_audit_events_branch_restricted_without_branches_returns_empty(monkeypatch):
    client_id = uuid4()
    query = _Query([])
    db = Mock()
    db.query.return_value = query

    context = _mock_context(client_id=client_id, branch_ids=(), branch_restricted=True)
    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    response = await console_router.list_audit_events(
        request=Mock(query_params={}),
        db=db,
        limit=50,
    )

    assert response.items == []
    assert response.cursor is None
    assert response.has_more is False
    assert _has_filter(query, "client_id")
    assert query.limit_value is None


@pytest.mark.asyncio
async def test_list_audit_events_rejects_invalid_entity_type(monkeypatch):
    client_id = uuid4()
    query = _Query([])
    db = Mock()
    db.query.return_value = query

    context = _mock_context(client_id=client_id, branch_ids=(), branch_restricted=False)
    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.list_audit_events(
            request=Mock(query_params={}),
            db=db,
            entity_type="invalid",
            limit=50,
        )

    assert exc_info.value.code == "INVALID_PARAM"
