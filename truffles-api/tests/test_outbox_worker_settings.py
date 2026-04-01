from datetime import datetime, timedelta, timezone

import pytest

from app.services import outbox_runtime_service as outbox_runtime
from app.workers import outbox


def test_outbox_worker_settings_parses_max_wait(monkeypatch):
    monkeypatch.setenv("OUTBOX_MAX_WAIT_SECONDS", "12")
    _, settings = outbox._get_outbox_worker_settings()
    assert settings.max_wait_seconds == 12


def test_outbox_worker_settings_clamps_negative_max_wait(monkeypatch):
    monkeypatch.setenv("OUTBOX_MAX_WAIT_SECONDS", "-5")
    _, settings = outbox._get_outbox_worker_settings()
    assert settings.max_wait_seconds == 0


@pytest.mark.asyncio
async def test_run_outbox_worker_cycle_uses_shared_runtime_helpers(monkeypatch):
    settings = outbox_runtime.OutboxProcessSettings(
        limit=2,
        idle_seconds=8,
        max_wait_seconds=10,
        max_attempts=5,
        retry_backoff_seconds=2.0,
        stale_seconds=120,
    )
    db = object()
    now = datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc)
    claim_calls: list[dict[str, object]] = []
    process_calls: list[list[dict[str, object]]] = []

    monkeypatch.setattr(
        outbox_runtime,
        "release_stale_processing",
        lambda *_args, **_kwargs: {"released": 1, "failed": 0},
    )
    monkeypatch.setattr(
        outbox_runtime,
        "schedule_inbound_syncs",
        lambda *_args, **_kwargs: {"interval_seconds": 120, "scheduled": 1, "errors": 0},
    )

    rows_queue = [
        [{"id": "row-1"}],
        [],
    ]

    def _claim_rows(*_args, **kwargs):
        claim_calls.append(kwargs)
        return rows_queue.pop(0)

    async def _process_rows(_db, rows, *, settings):
        process_calls.append(rows)
        assert settings.limit == 2
        return {"sent": len(rows), "failed": 0}

    monkeypatch.setattr(outbox_runtime, "claim_pending_outbox_batches", _claim_rows)
    monkeypatch.setattr(outbox_runtime, "process_claimed_outbox_rows", _process_rows)
    monkeypatch.setattr(outbox_runtime.time, "monotonic", lambda: 0.05)

    result = await outbox_runtime.run_outbox_worker_cycle(
        db,
        settings=settings,
        interval_seconds=1.0,
        next_inbound_schedule_at=None,
        now=now,
        loop_started_at=0.0,
    )

    assert result.next_inbound_schedule_at == now + timedelta(seconds=120)
    assert result.released_stale == {"released": 1, "failed": 0}
    assert result.inbound_results == {"interval_seconds": 120, "scheduled": 1, "errors": 0}
    assert result.processed_batches == 1
    assert process_calls == [[{"id": "row-1"}]]
    assert claim_calls == [
        {
            "limit": 2,
            "idle_seconds": 8,
            "max_wait_seconds": 10,
            "include_without_conversation": True,
        },
        {
            "limit": 2,
            "idle_seconds": 8,
            "max_wait_seconds": 10,
            "include_without_conversation": True,
        },
    ]


@pytest.mark.asyncio
async def test_run_default_outbox_process_uses_canonical_runtime_helper(monkeypatch):
    settings = outbox_runtime.OutboxProcessSettings(
        limit=10,
        idle_seconds=8,
        max_wait_seconds=10,
        max_attempts=5,
        retry_backoff_seconds=2.0,
        stale_seconds=120,
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(outbox_runtime, "load_outbox_process_settings", lambda: settings)
    monkeypatch.setattr(
        outbox_runtime,
        "release_stale_processing",
        lambda *_args, **_kwargs: {"released": 1, "failed": 0},
    )
    monkeypatch.setattr(
        outbox_runtime,
        "schedule_inbound_syncs",
        lambda *_args, **_kwargs: {"scheduled": 1, "errors": 0},
    )
    monkeypatch.setattr(
        outbox_runtime,
        "process_reminder_jobs",
        lambda *_args, **_kwargs: {"total": 1, "processed": 1},
    )

    async def _fake_run_canonical(_db, *, settings, claim_rows):
        captured["settings"] = settings
        captured["rows"] = claim_rows()
        return captured["rows"], {"sent": 1, "failed": 0}

    monkeypatch.setattr(outbox_runtime, "run_canonical_outbox_process", _fake_run_canonical)
    monkeypatch.setattr(
        outbox_runtime,
        "claim_pending_outbox_batches",
        lambda *_args, **kwargs: [kwargs],
    )

    result = await outbox_runtime.run_default_outbox_process(object(), include_reminders=True)

    assert captured["settings"] is settings
    assert captured["rows"] == [
        {
            "limit": 10,
            "idle_seconds": 8,
            "max_wait_seconds": 10,
            "include_without_conversation": True,
        }
    ]
    assert result["sent"] == 1
    assert result["calendar_inbound"] == {"scheduled": 1, "errors": 0}
    assert result["reminder_jobs"] == {"total": 1, "processed": 1}
    assert result["released_stale"] == 1
    assert result["failed_stale"] == 0


@pytest.mark.asyncio
async def test_run_scoped_outbox_process_uses_shared_runtime_helpers(monkeypatch):
    client_id = object()
    allowed_branch_ids = [object()]
    settings = outbox_runtime.OutboxProcessSettings(
        limit=10,
        idle_seconds=8,
        max_wait_seconds=10,
        max_attempts=5,
        retry_backoff_seconds=2.0,
        stale_seconds=120,
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(outbox_runtime, "load_outbox_process_settings", lambda: settings)

    def _fake_archive(*_args, **kwargs):
        captured["archive"] = kwargs
        return {"matched": 2, "archived": 2}

    async def _fake_run_canonical(_db, *, settings, claim_rows):
        captured["settings"] = settings
        captured["rows"] = claim_rows()
        return captured["rows"], {"sent": 1, "failed": 0}

    monkeypatch.setattr(outbox_runtime, "archive_pending_outbox", _fake_archive)
    monkeypatch.setattr(outbox_runtime, "run_canonical_outbox_process", _fake_run_canonical)
    monkeypatch.setattr(
        outbox_runtime,
        "claim_scoped_outbox_rows",
        lambda *_args, **kwargs: [{**kwargs, "id": "row-1"}],
    )

    result = await outbox_runtime.run_scoped_outbox_process(
        object(),
        client_id=client_id,
        allowed_branch_ids=allowed_branch_ids,
        limit=5,
        idle_seconds=12,
        max_wait_seconds=34,
        include_without_conversation=False,
        archive_pending_older_than_hours=24,
        archive_pending_limit=7,
        archive_pending_without_conversation_only=True,
    )

    assert result["processed"] == 1
    assert result["results"] == {"sent": 1, "failed": 0}
    assert result["archive"] == {"matched": 2, "archived": 2}
    assert captured["archive"]["client_id"] is client_id
    assert captured["archive"]["older_than_seconds"] == 24 * 3600
    assert captured["archive"]["limit"] == 7
    assert captured["archive"]["branch_ids"] == allowed_branch_ids
    assert captured["archive"]["only_without_conversation"] is True
    assert captured["rows"] == [
        {
            "client_id": client_id,
            "allowed_branch_ids": allowed_branch_ids,
            "limit": 5,
            "idle_seconds": 12,
            "max_wait_seconds": 34,
            "include_without_conversation": False,
            "id": "row-1",
        }
    ]
    assert captured["settings"] is settings


def test_outbox_worker_startup_guard_blocks_unsafe_mode(monkeypatch):
    monkeypatch.setenv("OUTBOX_WORKER_ENABLED", "1")
    monkeypatch.setenv("TEST_MODE", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@prod-db.internal:5432/chatbot")
    monkeypatch.delenv("OUTBOUND_ALLOWLIST_JIDS", raising=False)
    monkeypatch.delenv("OUTBOX_WORKER_UNSAFE_ALLOW", raising=False)

    with pytest.raises(RuntimeError):
        outbox.assert_outbox_worker_startup_safe()


def test_outbox_worker_startup_guard_can_be_overridden(monkeypatch):
    monkeypatch.setenv("OUTBOX_WORKER_ENABLED", "1")
    monkeypatch.setenv("TEST_MODE", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@prod-db.internal:5432/chatbot")
    monkeypatch.delenv("OUTBOUND_ALLOWLIST_JIDS", raising=False)
    monkeypatch.setenv("OUTBOX_WORKER_UNSAFE_ALLOW", "1")

    snapshot = outbox.assert_outbox_worker_startup_safe()

    assert "test_mode_outbox_worker_on_nonlocal_db" in snapshot.danger_flags
