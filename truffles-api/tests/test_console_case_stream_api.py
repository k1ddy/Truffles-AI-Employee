from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.models.conversation import Conversation
from app.models.handover import Handover
from app.models.message import Message
from app.routers import console as console_router


class _QueryStub:
    def __init__(self, result):
        self._result = result

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._result


@pytest.mark.asyncio
async def test_stream_case_updates_handles_cases_without_updated_at(monkeypatch) -> None:
    branch_id = uuid4()
    conversation_id = uuid4()
    case_id = uuid4()
    message_id = uuid4()
    now = datetime.now(timezone.utc)

    context = SimpleNamespace(
        agent=SimpleNamespace(id=uuid4(), name="Agent"),
        client=SimpleNamespace(id=uuid4()),
        branches=[SimpleNamespace(id=branch_id)],
        branch_restricted=False,
        allowed_branch_ids={branch_id},
    )
    case = SimpleNamespace(
        id=case_id,
        client_id=context.client.id,
        conversation_id=conversation_id,
        created_at=now,
    )
    conversation = SimpleNamespace(id=conversation_id, branch_id=branch_id)
    latest_message = SimpleNamespace(id=message_id, created_at=now)
    request = SimpleNamespace(is_disconnected=Mock(return_value=False))

    def _fake_query(*entities):
        if len(entities) == 1 and entities[0] is Handover:
            return _QueryStub(case)
        if len(entities) == 1 and entities[0] is Conversation:
            return _QueryStub(conversation)
        if len(entities) == 2 and entities[0] is Message.id and entities[1] is Message.created_at:
            return _QueryStub(latest_message)
        raise AssertionError(f"unexpected query: {entities!r}")

    db = Mock()
    db.query.side_effect = _fake_query

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_reject_unknown_query_params", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(console_router, "_require_branch_access", lambda *_args, **_kwargs: None)

    response = await console_router.stream_case_updates(case_id=case_id, request=request, db=db)

    assert response.media_type == "text/event-stream"
