from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import ConsoleMacroCreateRequest, ConsoleMacroUpdateRequest
from app.services.console_errors import ConsoleAPIError


def _mock_context(role="manager"):
    agent = SimpleNamespace(id=uuid4(), name="Agent")
    client = SimpleNamespace(id=uuid4())
    return SimpleNamespace(agent=agent, role=role, client=client)


def _mock_branch():
    return SimpleNamespace(id=uuid4())


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
