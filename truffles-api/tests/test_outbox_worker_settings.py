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
