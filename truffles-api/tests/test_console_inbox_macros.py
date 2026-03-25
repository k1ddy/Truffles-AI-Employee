from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy.sql.elements import BinaryExpression

from app.routers import console as console_router
from app.schemas.console import (
    ConsoleCase,
    ConsoleCaseActionResponse,
    ConsoleMacroAction,
    ConsoleMacroCreateRequest,
    ConsoleMacroExecuteRequest,
    ConsoleMacroUpdateRequest,
    ConsoleSyncStatus,
)
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


def _mock_macro(
    label: str,
    *,
    is_active: bool,
    scope: str = "team",
    action_config: dict | None = None,
    client_id=None,
    branch_id=None,
    agent_id=None,
):
    return SimpleNamespace(
        id=uuid4(),
        client_id=client_id or uuid4(),
        branch_id=branch_id or uuid4(),
        agent_id=agent_id,
        scope=scope,
        label=label,
        body="Body",
        action_config=action_config,
        is_active=is_active,
        created_at=None,
        updated_at=None,
    )


def _mock_case_action_response(case_id):
    return ConsoleCaseActionResponse(
        success=True,
        case=ConsoleCase(
            id=case_id,
            conversation_id=uuid4(),
            status="active",
            trigger_type="bot_request",
            created_at="2026-03-06T09:00:00+00:00",
            assigned_to_name="Agent",
            branch_id=uuid4(),
        ),
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
async def test_create_macro_persists_action_config(monkeypatch):
    context = _mock_context(role="manager")
    branch = _mock_branch()
    db = Mock()

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda *_args, **_kwargs: branch)

    response = await console_router.create_inbox_macro(
        request=Mock(),
        body=ConsoleMacroCreateRequest(
            scope="team",
            label="Отложить час",
            body="Вернусь позже",
            action=ConsoleMacroAction(type="snooze_case", minutes=60, reason="follow_up"),
        ),
        db=db,
    )

    created = db.add.call_args[0][0]
    assert created.action_config == {
        "type": "snooze_case",
        "minutes": 60,
        "reason": "follow_up",
    }
    assert response.macro.action is not None
    assert response.macro.action.type == "snooze_case"
    assert response.macro.action.minutes == 60


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
async def test_update_macro_can_clear_action(monkeypatch):
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
        action_config={"type": "take_case"},
        is_active=True,
        created_at=None,
        updated_at=None,
    )

    db = Mock()
    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda *_args, **_kwargs: branch)
    monkeypatch.setattr(
        console_router,
        "_resolve_inbox_macro_for_context",
        lambda *_args, **_kwargs: macro,
    )

    response = await console_router.update_inbox_macro(
        macro.id,
        request=Mock(),
        body=ConsoleMacroUpdateRequest(action=None),
        db=db,
    )

    assert macro.action_config is None
    assert response.action is None
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


@pytest.mark.asyncio
async def test_execute_inbox_macro_take_case_returns_case_response(monkeypatch):
    context = _mock_context(role="manager")
    branch = _mock_branch()
    macro = _mock_macro(
        "Взять заявку",
        is_active=True,
        action_config={"type": "take_case"},
        client_id=context.client.id,
        branch_id=branch.id,
    )
    case = SimpleNamespace(
        id=uuid4(),
        status="pending",
        assigned_to=None,
        assigned_to_name=None,
        conversation_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        trigger_type="bot_request",
        meta=None,
    )
    conversation = SimpleNamespace(id=case.conversation_id, branch_id=branch.id)
    db = Mock()
    state_result = SimpleNamespace(ok=True, error=None)
    audit_events: list[str] = []

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda *_args, **_kwargs: branch)
    monkeypatch.setattr(
        console_router,
        "_resolve_inbox_macro_for_context",
        lambda *_args, **_kwargs: macro,
    )
    monkeypatch.setattr(
        console_router,
        "_resolve_case_action_context",
        lambda *_args, **_kwargs: (case, conversation),
    )
    monkeypatch.setattr(console_router, "start_idempotency", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "state_manager_take", Mock(return_value=state_result))
    monkeypatch.setattr(
        console_router,
        "_sync_telegram_after_take",
        lambda *args, **kwargs: ConsoleSyncStatus(status="ok"),
    )
    monkeypatch.setattr(
        console_router,
        "_notify_client_status",
        lambda *args, **kwargs: ConsoleSyncStatus(status="ok"),
    )
    monkeypatch.setattr(console_router, "_build_case_action_response", lambda **kwargs: _mock_case_action_response(case.id))
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: audit_events.append(kwargs["event_type"]))

    response = await console_router.execute_inbox_macro(
        macro.id,
        body=ConsoleMacroExecuteRequest(case_id=case.id),
        request=Mock(),
        db=db,
    )

    assert response.success is True
    assert response.macro.id == macro.id
    assert response.macro.action is not None
    assert response.macro.action.type == "take_case"
    assert response.case.id == case.id
    console_router.state_manager_take.assert_called_once()
    assert "macro_executed" in audit_events


@pytest.mark.asyncio
async def test_execute_inbox_macro_snooze_uses_action_payload(monkeypatch):
    context = _mock_context(role="manager")
    branch = _mock_branch()
    macro = _mock_macro(
        "Отложить",
        is_active=True,
        action_config={"type": "snooze_case", "minutes": 45, "reason": "follow_up"},
        client_id=context.client.id,
        branch_id=branch.id,
    )
    case = SimpleNamespace(
        id=uuid4(),
        status="active",
        assigned_to=context.agent.id,
        assigned_to_name=context.agent.name,
        conversation_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        trigger_type="bot_request",
        meta=None,
    )
    conversation = SimpleNamespace(id=case.conversation_id, branch_id=branch.id)
    db = Mock()
    captured: dict = {}

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda *_args, **_kwargs: branch)
    monkeypatch.setattr(
        console_router,
        "_resolve_inbox_macro_for_context",
        lambda *_args, **_kwargs: macro,
    )
    monkeypatch.setattr(
        console_router,
        "_resolve_case_action_context",
        lambda *_args, **_kwargs: (case, conversation),
    )
    monkeypatch.setattr(console_router, "start_idempotency", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        console_router,
        "_set_case_snooze_meta",
        lambda *_args, **kwargs: captured.update(kwargs),
    )
    monkeypatch.setattr(console_router, "_build_case_action_response", lambda **kwargs: _mock_case_action_response(case.id))
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    response = await console_router.execute_inbox_macro(
        macro.id,
        body=ConsoleMacroExecuteRequest(case_id=case.id),
        request=Mock(),
        db=db,
    )

    assert response.macro.action is not None
    assert response.macro.action.type == "snooze_case"
    assert captured["reason"] == "follow_up"
    assert captured["agent_id"] == context.agent.id


@pytest.mark.asyncio
async def test_execute_inbox_macro_reopen_skips_external_sync(monkeypatch):
    context = _mock_context(role="manager")
    branch = _mock_branch()
    macro = _mock_macro(
        "Вернуть в работу",
        is_active=True,
        action_config={"type": "reopen_case"},
        client_id=context.client.id,
        branch_id=branch.id,
    )
    case = SimpleNamespace(
        id=uuid4(),
        status="resolved",
        assigned_to=None,
        assigned_to_name=None,
        conversation_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        trigger_type="bot_request",
        first_response_at=None,
        resolved_at=None,
        resolution_time_seconds=None,
        meta=None,
    )
    conversation = SimpleNamespace(id=case.conversation_id, branch_id=branch.id)
    db = Mock()
    audit_events: list[str] = []
    telegram_sync = Mock(side_effect=AssertionError("macro reopen must not edit telegram markup"))
    client_notify = Mock(side_effect=AssertionError("macro reopen must not notify client as new handoff"))

    def fake_reopen(*_args, **_kwargs):
        case.status = "active"
        case.assigned_to = context.agent.id
        case.assigned_to_name = context.agent.name
        return SimpleNamespace(ok=True, error=None)

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda *_args, **_kwargs: branch)
    monkeypatch.setattr(
        console_router,
        "_resolve_inbox_macro_for_context",
        lambda *_args, **_kwargs: macro,
    )
    monkeypatch.setattr(
        console_router,
        "_resolve_case_action_context",
        lambda *_args, **_kwargs: (case, conversation),
    )
    monkeypatch.setattr(console_router, "start_idempotency", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "state_manager_reopen", fake_reopen)
    monkeypatch.setattr(console_router, "_sync_telegram_after_take", telegram_sync)
    monkeypatch.setattr(console_router, "_notify_client_status", client_notify)
    monkeypatch.setattr(
        console_router,
        "record_audit_event",
        lambda *args, **kwargs: audit_events.append(kwargs["event_type"]),
    )

    response = await console_router.execute_inbox_macro(
        macro.id,
        body=ConsoleMacroExecuteRequest(case_id=case.id),
        request=Mock(),
        db=db,
    )

    assert response.success is True
    assert response.macro.action is not None
    assert response.macro.action.type == "reopen_case"
    assert response.case.status == "active"
    assert response.sync is not None
    assert response.sync.telegram.status == "skipped"
    assert response.sync.telegram.detail == "reopen_internal_only"
    assert response.sync.telegram.operator_message is None
    assert response.sync.client_notify.status == "skipped"
    assert response.sync.client_notify.detail == "reopen_internal_only"
    assert response.sync.client_notify.operator_message is None
    telegram_sync.assert_not_called()
    client_notify.assert_not_called()
    assert "case_reopened" in audit_events
    assert "case_reopen_sync" in audit_events
    assert "macro_executed" in audit_events


@pytest.mark.asyncio
async def test_execute_inbox_macro_rejects_inactive_macro(monkeypatch):
    context = _mock_context(role="manager")
    branch = _mock_branch()
    macro = _mock_macro(
        "Inactive",
        is_active=False,
        action_config={"type": "take_case"},
        client_id=context.client.id,
        branch_id=branch.id,
    )
    db = Mock()

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda *_args, **_kwargs: branch)
    monkeypatch.setattr(
        console_router,
        "_resolve_inbox_macro_for_context",
        lambda *_args, **_kwargs: macro,
    )
    monkeypatch.setattr(console_router, "start_idempotency", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.execute_inbox_macro(
            macro.id,
            body=ConsoleMacroExecuteRequest(case_id=uuid4()),
            request=Mock(),
            db=db,
        )

    assert exc_info.value.code == "MACRO_INACTIVE"


@pytest.mark.asyncio
async def test_execute_inbox_macro_rejects_branch_mismatch(monkeypatch):
    context = _mock_context(role="manager")
    branch = _mock_branch()
    macro = _mock_macro(
        "Take",
        is_active=True,
        action_config={"type": "take_case"},
        client_id=context.client.id,
        branch_id=branch.id,
    )
    case = SimpleNamespace(
        id=uuid4(),
        status="pending",
        assigned_to=None,
        assigned_to_name=None,
        conversation_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        trigger_type="bot_request",
        meta=None,
    )
    conversation = SimpleNamespace(id=case.conversation_id, branch_id=uuid4())
    db = Mock()

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_from_context", lambda *_args, **_kwargs: branch)
    monkeypatch.setattr(
        console_router,
        "_resolve_inbox_macro_for_context",
        lambda *_args, **_kwargs: macro,
    )
    monkeypatch.setattr(
        console_router,
        "_resolve_case_action_context",
        lambda *_args, **_kwargs: (case, conversation),
    )
    monkeypatch.setattr(console_router, "start_idempotency", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.execute_inbox_macro(
            macro.id,
            body=ConsoleMacroExecuteRequest(case_id=case.id),
            request=Mock(),
            db=db,
        )

    assert exc_info.value.code == "MACRO_BRANCH_MISMATCH"
