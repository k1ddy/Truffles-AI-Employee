import pytest

from app.services.runtime_safety import (
    assert_outbox_worker_startup_safe,
    build_runtime_safety_snapshot,
    classify_database_target,
)


def test_classify_database_target_treats_sqlite_as_local():
    host, is_local = classify_database_target("sqlite:///tmp/test.db")
    assert host == "sqlite"
    assert is_local is True


def test_classify_database_target_accepts_configured_local_cidr():
    host, is_local = classify_database_target(
        "postgresql://n8n:pass@172.24.0.6:5432/chatbot",
        env={"DATABASE_LOCAL_CIDRS": "172.24.0.0/16"},
    )

    assert host == "172.24.0.6"
    assert is_local is True


def test_runtime_safety_marks_nonlocal_test_mode_outbox_as_danger():
    snapshot = build_runtime_safety_snapshot(
        env={
            "TEST_MODE": "1",
            "OUTBOX_WORKER_ENABLED": "1",
            "DATABASE_URL": "postgresql://user:pass@prod-db.internal:5432/chatbot",
            "OUTBOUND_ALLOWLIST_JIDS": "77015705555@s.whatsapp.net",
        }
    )

    assert "test_mode_outbox_worker_on_nonlocal_db" in snapshot.danger_flags
    assert snapshot.status == "danger"


def test_runtime_safety_marks_test_mode_without_allowlist_as_danger():
    snapshot = build_runtime_safety_snapshot(
        env={
            "TEST_MODE": "1",
            "OUTBOX_WORKER_ENABLED": "1",
            "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/chatbot",
            "OUTBOUND_ALLOWLIST_JIDS": "",
        }
    )

    assert "test_mode_outbox_worker_without_allowlist" in snapshot.danger_flags


def test_runtime_safety_warns_about_provider_gateway_without_callback():
    snapshot = build_runtime_safety_snapshot(
        env={
            "TEST_MODE": "0",
            "OUTBOX_WORKER_ENABLED": "1",
            "PROVIDER_GATEWAY_OUTBOUND_ENABLED": "1",
            "PROVIDER_GATEWAY_STATUS_CALLBACK_URL": "",
            "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/chatbot",
            "OUTBOUND_ALLOWLIST_JIDS": "77015705555@s.whatsapp.net",
        }
    )

    assert snapshot.danger_flags == []
    assert snapshot.warning_flags == ["provider_gateway_outbound_missing_status_callback"]
    assert snapshot.status == "warning"


def test_assert_outbox_worker_startup_safe_raises_without_override():
    with pytest.raises(RuntimeError):
        assert_outbox_worker_startup_safe(
            env={
                "TEST_MODE": "1",
                "OUTBOX_WORKER_ENABLED": "1",
                "DATABASE_URL": "postgresql://user:pass@prod-db.internal:5432/chatbot",
                "OUTBOUND_ALLOWLIST_JIDS": "",
            }
        )


def test_assert_outbox_worker_startup_safe_allows_override():
    snapshot = assert_outbox_worker_startup_safe(
        env={
            "TEST_MODE": "1",
            "OUTBOX_WORKER_ENABLED": "1",
            "DATABASE_URL": "postgresql://user:pass@prod-db.internal:5432/chatbot",
            "OUTBOUND_ALLOWLIST_JIDS": "",
            "OUTBOX_WORKER_UNSAFE_ALLOW": "1",
        }
    )

    assert snapshot.status == "danger"
    assert len(snapshot.danger_flags) == 2
