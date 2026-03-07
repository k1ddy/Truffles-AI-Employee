from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import ConsoleQueueStateCurrentRequest
from app.services import console_queue_state as queue_state_service
from app.services.console_errors import ConsoleAPIError


def _mock_context(
    *,
    role: str = "manager",
    client_id=None,
    agent_id=None,
    selected_branch_id=None,
    agent_branch_id=None,
    allowed_branch_ids=None,
):
    selected_branch_id = selected_branch_id or uuid4()
    return SimpleNamespace(
        role=role,
        agent=SimpleNamespace(
            id=agent_id or uuid4(),
            branch_id=agent_branch_id or selected_branch_id,
        ),
        client=SimpleNamespace(id=client_id or uuid4()),
        selected_branch_id=selected_branch_id,
        allowed_branch_ids=allowed_branch_ids
        if allowed_branch_ids is not None
        else {selected_branch_id},
        branch_restricted=False,
    )


def test_normalize_cases_queue_state_downgrades_non_privileged_owner_scope() -> None:
    branch_id = uuid4()
    context = _mock_context(role="manager", selected_branch_id=branch_id, allowed_branch_ids={branch_id})

    normalized = queue_state_service.normalize_queue_state_payload(
        context,
        surface="cases",
        query_state={
            "mode_scope": "open",
            "base_view": "needs_reply",
            "owner_scope": {
                "kind": "agent",
                "agent_id": str(uuid4()),
            },
            "refinements": {
                "branch_id": str(branch_id),
                "query": "  late reply  ",
                "has_delivery_error": True,
                "has_pending_outbox": False,
                "has_human_lock": True,
                "sort_by": "sla",
            },
        },
    )

    assert normalized["mode_scope"] == "open"
    assert normalized["base_view"] == "needs_reply"
    assert normalized["owner_scope"] == {"kind": "all", "agent_id": None}
    assert normalized["refinements"]["branch_id"] == str(branch_id)
    assert normalized["refinements"]["query"] == "late reply"
    assert normalized["refinements"]["has_delivery_error"] is True
    assert normalized["refinements"]["has_human_lock"] is True
    assert normalized["refinements"]["sort_by"] == "sla"


def test_normalize_cases_queue_state_rejects_invalid_sort() -> None:
    context = _mock_context()

    with pytest.raises(ConsoleAPIError) as exc_info:
        queue_state_service.normalize_queue_state_payload(
            context,
            surface="cases",
            query_state={
                "refinements": {
                    "sort_by": "priority",
                }
            },
        )

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_put_current_queue_state_returns_normalized_cases_payload(monkeypatch) -> None:
    branch_id = uuid4()
    context = _mock_context(role="manager", selected_branch_id=branch_id, allowed_branch_ids={branch_id})
    body = ConsoleQueueStateCurrentRequest(
        surface="cases",
        query_state={
            "mode_scope": "open",
            "base_view": "needs_reply",
            "owner_scope": {
                "kind": "unassigned",
            },
            "refinements": {
                "branch_id": str(branch_id),
                "query": "  follow up  ",
                "has_delivery_error": True,
            },
        },
    )
    saved_at = datetime.now(timezone.utc)

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    captured = {}

    def _fake_upsert(db, *, client_id, agent_id, scope, version, query_state):
        captured["client_id"] = client_id
        captured["agent_id"] = agent_id
        captured["scope"] = scope
        captured["version"] = version
        captured["query_state"] = query_state
        return SimpleNamespace(
            selected_branch_id=scope.selected_branch_id,
            case_id=scope.case_id,
            conversation_id=scope.conversation_id,
            version=version,
            query_state=query_state,
            updated_at=saved_at,
        )

    monkeypatch.setattr(console_router, "_upsert_current_queue_state_record", _fake_upsert)

    response = await console_router.put_current_queue_state(
        body=body,
        request=Mock(),
        db=Mock(),
    )

    assert captured["client_id"] == context.client.id
    assert captured["agent_id"] == context.agent.id
    assert captured["scope"].surface == "cases"
    assert captured["query_state"]["owner_scope"] == {"kind": "all", "agent_id": None}
    assert captured["query_state"]["refinements"]["branch_id"] == str(branch_id)
    assert captured["query_state"]["refinements"]["query"] == "follow up"
    assert response.found is True
    assert response.surface == "cases"
    assert response.updated_at == saved_at.isoformat()


@pytest.mark.asyncio
async def test_get_current_queue_state_uses_calendar_scope_and_permission(monkeypatch) -> None:
    context = _mock_context(role="viewer")
    case_id = uuid4()
    conversation_id = uuid4()
    saved_at = datetime.now(timezone.utc)

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)

    permission_calls = []

    def _fake_require_permission(context_arg, section, action, **_kwargs):
        permission_calls.append((section, action, context_arg.role))

    monkeypatch.setattr(console_router, "require_console_permission", _fake_require_permission)

    captured = {}

    def _fake_get(db, *, client_id, agent_id, surface, scope_key):
        captured["client_id"] = client_id
        captured["agent_id"] = agent_id
        captured["surface"] = surface
        captured["scope_key"] = scope_key
        return SimpleNamespace(
            selected_branch_id=context.selected_branch_id,
            case_id=case_id,
            conversation_id=conversation_id,
            version=1,
            query_state={
                "selected_date": "2026-03-07",
                "queue_lane": "attention",
                "status_filter": "no_show",
                "query": "almaty",
            },
            updated_at=saved_at,
        )

    monkeypatch.setattr(console_router, "_get_current_queue_state_record", _fake_get)

    response = await console_router.get_current_queue_state(
        request=Mock(query_params={"surface": "calendar", "case_id": str(case_id), "conversation_id": str(conversation_id)}),
        surface="calendar",
        case_id=str(case_id),
        conversation_id=str(conversation_id),
        db=Mock(),
    )

    assert permission_calls == [("calendar", "read", "viewer")]
    assert captured["client_id"] == context.client.id
    assert captured["agent_id"] == context.agent.id
    assert captured["surface"] == "calendar"
    assert f"case:{case_id}" in captured["scope_key"]
    assert f"conversation:{conversation_id}" in captured["scope_key"]
    assert response.found is True
    assert response.query_state["status_filter"] == "no_show"


@pytest.mark.asyncio
async def test_get_current_queue_state_rejects_case_scope_for_cases(monkeypatch) -> None:
    context = _mock_context()

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_current_queue_state(
            request=Mock(query_params={"surface": "cases", "case_id": str(uuid4())}),
            surface="cases",
            case_id=str(uuid4()),
            conversation_id=None,
            db=Mock(),
        )

    assert exc_info.value.code == "INVALID_PARAM"
