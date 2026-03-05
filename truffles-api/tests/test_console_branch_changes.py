from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import ConsoleBranchChangePublishRequest, ConsoleBranchChangeRollbackRequest
from app.services.console_branch_changes import (
    apply_branch_change_publish_failed_state,
    apply_branch_change_publish_runtime_error_state,
    apply_branch_change_rollback_failed_state,
    apply_branch_change_rolled_back_state,
    apply_branch_change_validation_result,
    build_branch_change_diff,
    build_branch_change_list_response,
    normalize_branch_change_patch,
    prepare_branch_change_payload,
)
from app.services.console_errors import ConsoleAPIError


def _normalize_patch_for_branch_change(
    *,
    db: object,
    branch: object,
    patch_payload: dict,
) -> tuple[dict[str, object], list[str]]:
    return normalize_branch_change_patch(
        db=db,  # type: ignore[arg-type]
        branch=branch,  # type: ignore[arg-type]
        patch_payload=patch_payload,
        validation_error_type=ConsoleAPIError,
        ensure_unique_branch_field=console_router._ensure_unique_branch_field,
        normalize_slug=console_router._normalize_slug,
        normalize_required_text=console_router._normalize_required_text,
        normalize_timezone_name=console_router._normalize_timezone_name,
        normalize_optional_text=console_router._normalize_optional_text,
        normalize_branch_phone=console_router._normalize_branch_phone,
        normalize_telegram_chat_id=console_router._normalize_telegram_chat_id,
        normalize_knowledge_tag=console_router._normalize_knowledge_tag,
        require_branch_go_live_gate=lambda current_branch: console_router._require_branch_go_live_gate(
            current_branch,
            operation="branch_activate",
        ),
        require_branch_scorecard_ready=lambda current_db, current_branch: console_router._require_branch_scorecard_ready(
            current_db,
            current_branch,
            operation="branch_activate",
        ),
    )


def _build_branch_change_row(*, created_at: datetime, status: str = "draft") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        branch_id=uuid4(),
        status=status,
        reason="test",
        draft_payload={},
        diff_payload={},
        validation_payload={"ok": True, "errors": []},
        base_snapshot={},
        published_snapshot=None,
        rollback_snapshot=None,
        publish_error=None,
        rollback_error=None,
        created_at=created_at,
        updated_at=created_at,
        validated_at=None,
        published_at=None,
        rolled_back_at=None,
    )


def test_build_branch_change_diff_skips_unchanged_fields():
    base = {
        "slug": "branch-a",
        "name": "Branch A",
        "is_active": True,
    }
    patch = {
        "slug": "branch-a",
        "name": "Branch B",
        "is_active": False,
    }
    diff = build_branch_change_diff(base, patch)

    assert "slug" not in diff
    assert diff["name"] == {"before": "Branch A", "after": "Branch B"}
    assert diff["is_active"] == {"before": True, "after": False}


def test_build_branch_change_rollback_patch_only_includes_changed_fields():
    base_snapshot = {
        "slug": "branch-a",
        "name": "Branch A",
        "instance_id": "inst-a",
        "is_active": True,
    }
    current_snapshot = {
        "slug": "branch-a",
        "name": "Branch B",
        "instance_id": "inst-a",
        "is_active": False,
    }

    rollback_patch = console_router._build_branch_change_rollback_patch(
        base_snapshot=base_snapshot,
        current_snapshot=current_snapshot,
    )

    assert rollback_patch == {
        "name": "Branch A",
        "is_active": True,
    }


def test_build_branch_change_list_response_builds_page_and_cursor():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    rows = [
        _build_branch_change_row(created_at=now, status="draft"),
        _build_branch_change_row(created_at=now - timedelta(minutes=1), status="draft"),
        _build_branch_change_row(created_at=now - timedelta(minutes=2), status="draft"),
    ]
    query = Mock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = rows

    response = build_branch_change_list_response(
        query=query,
        status="draft",
        cursor_date=None,
        limit=2,
    )

    assert len(response.items) == 2
    assert response.has_more is True
    assert response.cursor == rows[1].created_at.isoformat()
    query.filter.assert_called_once()
    query.order_by.assert_called_once()
    query.limit.assert_called_once_with(3)


def test_build_branch_change_list_response_rejects_invalid_status():
    with pytest.raises(ValueError, match="Invalid status"):
        build_branch_change_list_response(
            query=Mock(),
            status="unknown",
            cursor_date=None,
            limit=10,
        )


def test_normalize_branch_change_status_filter():
    assert console_router._normalize_branch_change_status_filter(" validated ") == "validated"
    assert console_router._normalize_branch_change_status_filter(None) is None
    with pytest.raises(ValueError, match="Invalid status"):
        console_router._normalize_branch_change_status_filter("unknown")


def test_normalize_branch_change_patch_requires_instance_for_activation(monkeypatch):
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        instance_id=None,
        is_active=False,
        go_live_state="approved",
        go_live_reason=None,
        go_live_waiver_until=None,
    )
    monkeypatch.setattr(console_router, "_ensure_unique_branch_field", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_require_branch_go_live_gate", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_require_branch_scorecard_ready", lambda *args, **kwargs: None)

    normalized, errors = _normalize_patch_for_branch_change(
        db=SimpleNamespace(),
        branch=branch,
        patch_payload={"is_active": True},
    )

    assert normalized["is_active"] is True
    assert "instance_id required to activate branch" in errors


@pytest.mark.parametrize(
    ("patch", "expected_error"),
    [
        ({"timezone": "Mars/Phobos"}, "Invalid timezone"),
        ({"phone": "abc"}, "Invalid phone"),
        ({"phone": 12345}, "phone must be string"),
        ({"telegram_chat_id": "chat-1"}, "Invalid telegram_chat_id"),
        ({"knowledge_tag": "Bad Tag"}, "Invalid knowledge_tag"),
    ],
)
def test_normalize_branch_change_patch_rejects_invalid_inputs(monkeypatch, patch, expected_error):
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        instance_id="inst-1",
        is_active=False,
        go_live_state="approved",
        go_live_reason=None,
        go_live_waiver_until=None,
    )
    monkeypatch.setattr(console_router, "_ensure_unique_branch_field", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_require_branch_go_live_gate", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_require_branch_scorecard_ready", lambda *args, **kwargs: None)

    _normalized, errors = _normalize_patch_for_branch_change(
        db=SimpleNamespace(),
        branch=branch,
        patch_payload=patch,
    )

    assert expected_error in errors


def test_normalize_branch_change_patch_normalizes_knowledge_tag(monkeypatch):
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        instance_id="inst-1",
        is_active=False,
        go_live_state="approved",
        go_live_reason=None,
        go_live_waiver_until=None,
    )
    monkeypatch.setattr(console_router, "_ensure_unique_branch_field", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_require_branch_go_live_gate", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_require_branch_scorecard_ready", lambda *args, **kwargs: None)

    normalized, errors = _normalize_patch_for_branch_change(
        db=SimpleNamespace(),
        branch=branch,
        patch_payload={"knowledge_tag": "Demo_Tag"},
    )

    assert errors == []
    assert normalized["knowledge_tag"] == "demo_tag"


def test_prepare_branch_change_payload_reports_no_effective_changes(monkeypatch):
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        slug="branch-a",
        name="Branch A",
        timezone="UTC",
        instance_id="inst-1",
        phone="+77000000000",
        telegram_chat_id="123456",
        knowledge_tag="demo_tag",
        working_hours={"monday": ["09:00-18:00"]},
        booking_settings={"enabled": True},
        is_active=False,
        go_live_state="approved",
        go_live_reason=None,
        go_live_waiver_until=None,
    )
    monkeypatch.setattr(console_router, "_ensure_unique_branch_field", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_require_branch_go_live_gate", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_require_branch_scorecard_ready", lambda *args, **kwargs: None)

    normalized, errors, diff_payload, base_snapshot = prepare_branch_change_payload(
        db=SimpleNamespace(),
        branch=branch,
        patch_payload={"name": "Branch A"},
        validation_error_type=ConsoleAPIError,
        ensure_unique_branch_field=console_router._ensure_unique_branch_field,
        normalize_slug=console_router._normalize_slug,
        normalize_required_text=console_router._normalize_required_text,
        normalize_timezone_name=console_router._normalize_timezone_name,
        normalize_optional_text=console_router._normalize_optional_text,
        normalize_branch_phone=console_router._normalize_branch_phone,
        normalize_telegram_chat_id=console_router._normalize_telegram_chat_id,
        normalize_knowledge_tag=console_router._normalize_knowledge_tag,
        require_branch_go_live_gate=lambda current_branch: console_router._require_branch_go_live_gate(
            current_branch,
            operation="branch_activate",
        ),
        require_branch_scorecard_ready=lambda current_db, current_branch: console_router._require_branch_scorecard_ready(
            current_db,
            current_branch,
            operation="branch_activate",
        ),
    )

    assert normalized["name"] == "Branch A"
    assert diff_payload == {}
    assert "No effective branch changes detected" in errors
    assert base_snapshot["name"] == "Branch A"


def test_apply_branch_change_validation_result_marks_validated():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    change = SimpleNamespace(
        draft_payload=None,
        diff_payload=None,
        base_snapshot=None,
        base_branch_updated_at=None,
        validation_payload=None,
        status="draft",
        validated_at=None,
        updated_at=None,
    )
    branch = SimpleNamespace(updated_at=now)

    apply_branch_change_validation_result(
        change=change,
        branch=branch,
        normalized_patch={"name": "Branch B"},
        diff_payload={"name": {"before": "Branch A", "after": "Branch B"}},
        base_snapshot={"name": "Branch A"},
        errors=[],
        now=now,
    )

    assert change.status == "validated"
    assert change.validated_at == now
    assert change.updated_at == now
    assert change.base_branch_updated_at == now
    assert change.validation_payload == {"ok": True, "errors": []}
    assert change.draft_payload == {"name": "Branch B"}


def test_apply_branch_change_validation_result_marks_draft_on_errors():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    change = SimpleNamespace(
        draft_payload=None,
        diff_payload=None,
        base_snapshot=None,
        base_branch_updated_at=None,
        validation_payload=None,
        status="validated",
        validated_at=now,
        updated_at=None,
    )
    branch = SimpleNamespace(updated_at=now - timedelta(minutes=5))

    apply_branch_change_validation_result(
        change=change,
        branch=branch,
        normalized_patch={"is_active": True},
        diff_payload={"is_active": {"before": False, "after": True}},
        base_snapshot={"is_active": False},
        errors=["instance_id required to activate branch"],
        now=now,
    )

    assert change.status == "draft"
    assert change.validated_at is None
    assert change.updated_at == now
    assert change.base_branch_updated_at == branch.updated_at
    assert change.validation_payload == {
        "ok": False,
        "errors": ["instance_id required to activate branch"],
    }


def test_apply_branch_change_publish_failed_state_sets_error_payload():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    change = SimpleNamespace(
        status="validated",
        publish_error=None,
        validation_payload=None,
        updated_at=None,
    )

    message = apply_branch_change_publish_failed_state(
        change=change,
        errors=["err-1", "err-2"],
        now=now,
    )

    assert message == "err-1; err-2"
    assert change.status == "publish_failed"
    assert change.publish_error == "err-1; err-2"
    assert change.validation_payload == {"ok": False, "errors": ["err-1", "err-2"]}
    assert change.updated_at == now


def test_apply_branch_change_publish_runtime_error_state_sets_publish_failed():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    change = SimpleNamespace(
        status="validated",
        publish_error=None,
        updated_at=None,
    )

    apply_branch_change_publish_runtime_error_state(
        change=change,
        error_message="runtime-failed",
        now=now,
    )

    assert change.status == "publish_failed"
    assert change.publish_error == "runtime-failed"
    assert change.updated_at == now


def test_apply_branch_change_rollback_failed_state_sets_error():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    change = SimpleNamespace(
        rollback_error=None,
        updated_at=None,
    )

    apply_branch_change_rollback_failed_state(
        change=change,
        error_message="rollback-failed",
        now=now,
    )

    assert change.rollback_error == "rollback-failed"
    assert change.updated_at == now


def test_apply_branch_change_rolled_back_state_sets_snapshot_and_actor():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    actor_id = uuid4()
    change = SimpleNamespace(
        status="published",
        rollback_error="old-error",
        rollback_snapshot=None,
        rolled_back_at=None,
        rolled_back_by=None,
        updated_at=None,
    )

    apply_branch_change_rolled_back_state(
        change=change,
        rollback_snapshot={"name": "Branch A", "is_active": False},
        actor_id=actor_id,
        now=now,
    )

    assert change.status == "rolled_back"
    assert change.rollback_error is None
    assert change.rollback_snapshot == {"name": "Branch A", "is_active": False}
    assert change.rolled_back_at == now
    assert change.rolled_back_by == actor_id
    assert change.updated_at == now


@pytest.mark.asyncio
async def test_publish_branch_change_requires_validated_state(monkeypatch):
    context = SimpleNamespace(
        role="platform_admin",
        client=SimpleNamespace(id=uuid4()),
        branches=[],
        branch_restricted=False,
        agent=SimpleNamespace(id=uuid4()),
    )
    change = SimpleNamespace(
        id=uuid4(),
        status="draft",
        branch_id=uuid4(),
        client_id=context.client.id,
    )
    monkeypatch.setattr(console_router, "get_console_context", lambda *args, **kwargs: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_get_branch_change_for_context", lambda *args, **kwargs: change)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.publish_branch_change(
            change_id=change.id,
            body=ConsoleBranchChangePublishRequest(),
            request=SimpleNamespace(query_params={}),
            db=SimpleNamespace(),
        )

    assert exc_info.value.code == "INVALID_STATE"


@pytest.mark.asyncio
async def test_rollback_branch_change_requires_published_state(monkeypatch):
    context = SimpleNamespace(
        role="platform_admin",
        client=SimpleNamespace(id=uuid4()),
        branches=[],
        branch_restricted=False,
        agent=SimpleNamespace(id=uuid4()),
    )
    change = SimpleNamespace(
        id=uuid4(),
        status="validated",
        branch_id=uuid4(),
        client_id=context.client.id,
    )
    monkeypatch.setattr(console_router, "get_console_context", lambda *args, **kwargs: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_get_branch_change_for_context", lambda *args, **kwargs: change)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.rollback_branch_change(
            change_id=change.id,
            body=ConsoleBranchChangeRollbackRequest(reason="revert"),
            request=SimpleNamespace(query_params={}),
            db=SimpleNamespace(),
        )

    assert exc_info.value.code == "INVALID_STATE"
