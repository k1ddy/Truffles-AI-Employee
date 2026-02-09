from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import ConsoleBranchChangePublishRequest, ConsoleBranchChangeRollbackRequest
from app.services.console_errors import ConsoleAPIError


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
    diff = console_router._build_branch_change_diff(base, patch)

    assert "slug" not in diff
    assert diff["name"] == {"before": "Branch A", "after": "Branch B"}
    assert diff["is_active"] == {"before": True, "after": False}


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

    normalized, errors = console_router._normalize_branch_change_patch(
        db=SimpleNamespace(),
        branch=branch,
        patch_payload={"is_active": True},
    )

    assert normalized["is_active"] is True
    assert "instance_id required to activate branch" in errors


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
