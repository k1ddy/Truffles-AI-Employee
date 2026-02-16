import pytest

from app import main as main_module


def test_float_env_parsing(monkeypatch):
    monkeypatch.setenv("TEST_HEALTH_FLOAT", "invalid")
    assert main_module._float_env("TEST_HEALTH_FLOAT", 1.25, 0.0) == 1.25

    monkeypatch.setenv("TEST_HEALTH_FLOAT", "0.1")
    assert main_module._float_env("TEST_HEALTH_FLOAT", 1.25, 0.5) == 0.5

    monkeypatch.setenv("TEST_HEALTH_FLOAT", "3.7")
    assert main_module._float_env("TEST_HEALTH_FLOAT", 1.25, 0.5) == 3.7


@pytest.mark.asyncio
async def test_health_check_uses_cached_payload(monkeypatch):
    calls = {"count": 0}

    async def fake_compute(_db):
        calls["count"] += 1
        return {
            "status": "healthy",
            "timestamp": "2026-02-16T00:00:00Z",
            "latency_ms": 7,
            "checks": {},
        }

    monkeypatch.setattr(main_module, "_compute_admin_health_payload", fake_compute)
    monkeypatch.setattr(main_module, "_ADMIN_HEALTH_CACHE_TTL_SECONDS", 60.0)

    main_module._admin_health_cache["payload"] = None
    main_module._admin_health_cache["expires_at"] = 0.0

    first = await main_module.health_check(db=object())
    second = await main_module.health_check(db=object())

    assert calls["count"] == 1
    assert first["cached"] is False
    assert second["cached"] is True
    assert second["cache_ttl_seconds"] == 60.0

    main_module._admin_health_cache["payload"] = None
    main_module._admin_health_cache["expires_at"] = 0.0
