from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services import worker_heartbeat_service as service


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def setex(self, key: str, _ttl: int, value: str) -> None:
        self.data[key] = value

    def get(self, key: str) -> str | None:
        return self.data.get(key)


def test_touch_worker_heartbeat_persists_timestamp(monkeypatch) -> None:
    fake = FakeRedis()
    monkeypatch.setattr(service, "_get_redis_client", lambda: fake)
    now = datetime(2026, 4, 19, 10, 0, tzinfo=timezone.utc)

    service.touch_worker_heartbeat("truffles-sentinel", now=now)

    assert fake.data[service._heartbeat_key("truffles-sentinel")] == str(int(now.timestamp()))


def test_build_worker_heartbeat_snapshot_marks_healthy_and_missing(monkeypatch) -> None:
    fake = FakeRedis()
    now = datetime(2026, 4, 19, 10, 0, tzinfo=timezone.utc)
    fake.data[service._heartbeat_key("truffles-sentinel")] = str(int((now - timedelta(seconds=10)).timestamp()))
    monkeypatch.setattr(service, "_get_redis_client", lambda: fake)

    snapshot = service.build_worker_heartbeat_snapshot(now=now)

    assert snapshot["truffles-sentinel"]["status"] == "healthy"
    assert snapshot["truffles-sentinel"]["age_seconds"] == 10
    assert snapshot["truffles-outbox"]["status"] == "missing"


def test_build_worker_heartbeat_snapshot_marks_stale(monkeypatch) -> None:
    fake = FakeRedis()
    now = datetime(2026, 4, 19, 10, 0, tzinfo=timezone.utc)
    stale_seconds = service._stale_after_seconds("truffles-outbox")
    fake.data[service._heartbeat_key("truffles-outbox")] = str(
        int((now - timedelta(seconds=stale_seconds + 5)).timestamp())
    )
    monkeypatch.setattr(service, "_get_redis_client", lambda: fake)

    snapshot = service.build_worker_heartbeat_snapshot(now=now)

    assert snapshot["truffles-outbox"]["status"] == "stale"
