from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

from app.config import settings

LOCAL_DB_HOSTS = {
    "",
    "localhost",
    "127.0.0.1",
    "::1",
    "db",
    "postgres",
    "truffles_postgres_1",
    "host.docker.internal",
}


def _is_env_enabled(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_allowlist(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [jid.strip() for jid in raw.split(",") if jid.strip()]


@dataclass(frozen=True)
class RuntimeSafetySnapshot:
    test_mode_enabled: bool
    outbox_worker_enabled: bool
    provider_gateway_outbound_enabled: bool
    provider_gateway_status_callback_set: bool
    outbound_allowlist_count: int
    database_host: str
    database_is_local: bool
    danger_flags: list[str]
    warning_flags: list[str]

    @property
    def status(self) -> str:
        if self.danger_flags:
            return "danger"
        if self.warning_flags:
            return "warning"
        return "ok"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "test_mode_enabled": self.test_mode_enabled,
            "outbox_worker_enabled": self.outbox_worker_enabled,
            "provider_gateway_outbound_enabled": self.provider_gateway_outbound_enabled,
            "provider_gateway_status_callback_set": self.provider_gateway_status_callback_set,
            "outbound_allowlist_count": self.outbound_allowlist_count,
            "database_host": self.database_host,
            "database_is_local": self.database_is_local,
            "danger_flags": list(self.danger_flags),
            "warning_flags": list(self.warning_flags),
        }


def classify_database_target(database_url: str | None) -> tuple[str, bool]:
    raw = (database_url or "").strip()
    if not raw:
        return "", True
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme.startswith("sqlite"):
        return "sqlite", True
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return "", True
    return host, host in LOCAL_DB_HOSTS


def build_runtime_safety_snapshot(
    *,
    env: dict[str, str] | None = None,
    database_url: str | None = None,
) -> RuntimeSafetySnapshot:
    source_env = env if env is not None else os.environ
    test_mode_enabled = _is_env_enabled(source_env.get("TEST_MODE"), default=False)
    outbox_worker_enabled = _is_env_enabled(source_env.get("OUTBOX_WORKER_ENABLED"), default=True)
    provider_gateway_outbound_enabled = _is_env_enabled(
        source_env.get("PROVIDER_GATEWAY_OUTBOUND_ENABLED"),
        default=False,
    )
    callback_url = (source_env.get("PROVIDER_GATEWAY_STATUS_CALLBACK_URL") or "").strip()
    allowlist = _parse_allowlist(source_env.get("OUTBOUND_ALLOWLIST_JIDS"))

    resolved_database_url = database_url if database_url is not None else source_env.get("DATABASE_URL")
    if resolved_database_url is None:
        resolved_database_url = getattr(settings, "database_url", None)
    database_host, database_is_local = classify_database_target(resolved_database_url)

    danger_flags: list[str] = []
    warning_flags: list[str] = []

    if test_mode_enabled and outbox_worker_enabled and not database_is_local:
        danger_flags.append("test_mode_outbox_worker_on_nonlocal_db")

    if test_mode_enabled and outbox_worker_enabled and not allowlist:
        danger_flags.append("test_mode_outbox_worker_without_allowlist")

    if provider_gateway_outbound_enabled and not callback_url:
        warning_flags.append("provider_gateway_outbound_missing_status_callback")

    return RuntimeSafetySnapshot(
        test_mode_enabled=test_mode_enabled,
        outbox_worker_enabled=outbox_worker_enabled,
        provider_gateway_outbound_enabled=provider_gateway_outbound_enabled,
        provider_gateway_status_callback_set=bool(callback_url),
        outbound_allowlist_count=len(allowlist),
        database_host=database_host,
        database_is_local=database_is_local,
        danger_flags=danger_flags,
        warning_flags=warning_flags,
    )


def assert_outbox_worker_startup_safe(
    *,
    env: dict[str, str] | None = None,
    database_url: str | None = None,
) -> RuntimeSafetySnapshot:
    source_env = env if env is not None else os.environ
    snapshot = build_runtime_safety_snapshot(env=source_env, database_url=database_url)
    allow_unsafe = _is_env_enabled(source_env.get("OUTBOX_WORKER_UNSAFE_ALLOW"), default=False)
    if snapshot.danger_flags and not allow_unsafe:
        details = ", ".join(snapshot.danger_flags)
        raise RuntimeError(
            "Unsafe outbox worker startup blocked "
            f"(danger_flags={details}). "
            "Set OUTBOX_WORKER_UNSAFE_ALLOW=1 only for explicit local debugging."
        )
    return snapshot
