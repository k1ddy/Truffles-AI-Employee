from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import ConsoleBranchChangePublishRequest, ConsoleBranchChangeRollbackRequest
from app.services.console_branch_changes import (
    build_branch_change_diff,
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
