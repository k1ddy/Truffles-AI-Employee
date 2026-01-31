from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy.sql.elements import BinaryExpression

from app.routers import console as console_router
from app.schemas.console import ConsoleMacroCreateRequest, ConsoleMacroUpdateRequest
from app.services.console_errors import ConsoleAPIError


class _FakeQuery:
    def __init__(self, items):
        self._items = list(items)
        self._only_active = False

    def filter(self, *criteria):
        for criterion in criteria:
            if isinstance(criterion, BinaryExpression) and getattr(criterion.left, "name", None) == "is_active":
                self._only_active = True
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        if self._only_active:
            return [item for item in self._items if item.is_active]
        return list(self._items)


def _mock_context(role="manager"):
    agent = SimpleNamespace(id=uuid4(), name="Agent")
    client = SimpleNamespace(id=uuid4())
    return SimpleNamespace(agent=agent, role=role, client=client)


def _mock_branch():
    return SimpleNamespace(id=uuid4())


def _mock_macro(label: str, *, is_active: bool, scope: str = "team"):
    return SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        branch_id=uuid4(),
        agent_id=None,
        scope=scope,
        label=label,
        body="Body",
        is_active=is_active,
        created_at=None,
        updated_at=None,
    )


@pytest.mark.asyncio
async def test_create_personal_macro_sets_agent_id(monkeypatch):
    context = _mock_context(role="manager")
    branch = _mock_branch()
    db = Mock()

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda *_args, **_kwargs: branch)

    response = await console_router.create_inbox_macro(
        request=Mock(),
        body=ConsoleMacroCreateRequest(
            scope="personal",
            label="Мой ответ",
            body="Текст макроса",
        ),
        db=db,
    )

    created = db.add.call_args[0][0]
    assert created.agent_id == context.agent.id
    assert created.branch_id == branch.id
    assert response.macro.scope == "personal"
    assert response.macro.label == "Мой ответ"


@pytest.mark.asyncio
async def test_list_inbox_macros_filters_inactive_by_default(monkeypatch):
    context = _mock_context(role="manager")
    branch = _mock_branch()
    active = _mock_macro("Active", is_active=True)
    inactive = _mock_macro("Inactive", is_active=False)

    db = Mock()
    db.query.return_value = _FakeQuery([active, inactive])

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda *_args, **_kwargs: branch)

    response = await console_router.list_inbox_macros(
        request=Mock(query_params={}),
        include_inactive=False,
        db=db,
    )

    assert [item.label for item in response.items] == ["Active"]


@pytest.mark.asyncio
async def test_list_inbox_macros_includes_inactive(monkeypatch):
    context = _mock_context(role="manager")
    branch = _mock_branch()
    active = _mock_macro("Active", is_active=True)
    inactive = _mock_macro("Inactive", is_active=False)

    db = Mock()
    db.query.return_value = _FakeQuery([active, inactive])

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda *_args, **_kwargs: branch)

    response = await console_router.list_inbox_macros(
        request=Mock(query_params={}),
        include_inactive=True,
        db=db,
    )

    assert {item.label for item in response.items} == {"Active", "Inactive"}


@pytest.mark.asyncio
async def test_update_macro_rejects_other_agent(monkeypatch):
    context = _mock_context(role="manager")
    branch = _mock_branch()
    macro = SimpleNamespace(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=branch.id,
        agent_id=uuid4(),
        scope="personal",
        label="Old",
        body="Body",
        is_active=True,
        created_at=None,
        updated_at=None,
    )

    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = macro

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda *_args, **_kwargs: branch)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.update_inbox_macro(
            macro.id,
            request=Mock(),
            body=ConsoleMacroUpdateRequest(label="New"),
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_update_team_macro_allows_manager(monkeypatch):
    context = _mock_context(role="manager")
    branch = _mock_branch()
    macro = SimpleNamespace(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=branch.id,
        agent_id=None,
        scope="team",
        label="Old",
        body="Body",
        is_active=True,
        created_at=None,
        updated_at=None,
    )

    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = macro

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda *_args, **_kwargs: branch)

    response = await console_router.update_inbox_macro(
        macro.id,
        request=Mock(),
        body=ConsoleMacroUpdateRequest(label="Updated", body="Updated", is_active=False),
        db=db,
    )

    assert response.label == "Updated"
    assert response.is_active is False
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_macro_allows_privileged_user(monkeypatch):
    context = _mock_context(role="admin")
    branch = _mock_branch()
    macro = SimpleNamespace(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=branch.id,
        agent_id=uuid4(),
        scope="personal",
        label="Old",
        body="Body",
        is_active=True,
        created_at=None,
        updated_at=None,
    )

    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = macro

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda *_args, **_kwargs: branch)

    response = await console_router.update_inbox_macro(
        macro.id,
        request=Mock(),
        body=ConsoleMacroUpdateRequest(label="New", body="Updated", is_active=False),
        db=db,
    )

    assert response.label == "New"
    assert response.body == "Updated"
    assert response.is_active is False
    db.commit.assert_called_once()
