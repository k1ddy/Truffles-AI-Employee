import pytest

from app.workers import outbox


def test_outbox_worker_settings_parses_max_wait(monkeypatch):
    monkeypatch.setenv("OUTBOX_MAX_WAIT_SECONDS", "12")
    settings = outbox._get_outbox_worker_settings()
    assert settings[3] == 12


def test_outbox_worker_settings_clamps_negative_max_wait(monkeypatch):
    monkeypatch.setenv("OUTBOX_MAX_WAIT_SECONDS", "-5")
    settings = outbox._get_outbox_worker_settings()
    assert settings[3] == 0


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
