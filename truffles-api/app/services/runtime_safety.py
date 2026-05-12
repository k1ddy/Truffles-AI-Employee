from __future__ import annotations

import os
from ipaddress import ip_address, ip_network
from dataclasses import dataclass
from urllib.parse import urlparse

from app.config import settings
from app.services.runtime_mode_service import (
    get_eval_mode,
    get_outbound_allowlist,
    get_outbox_worker_mode,
    get_transport_send_mode,
    is_legacy_test_mode_enabled,
    is_outbox_worker_enabled,
)

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
    eval_mode: str
    transport_send_mode: str
    outbox_worker_mode: str
    test_mode_enabled: bool
    outbox_worker_enabled: bool
    provider_gateway_outbound_enabled: bool
    provider_gateway_status_callback_set: bool
    integration_watchdog_enabled: bool
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
            "eval_mode": self.eval_mode,
            "transport_send_mode": self.transport_send_mode,
            "outbox_worker_mode": self.outbox_worker_mode,
            "test_mode_enabled": self.test_mode_enabled,
            "outbox_worker_enabled": self.outbox_worker_enabled,
            "provider_gateway_outbound_enabled": self.provider_gateway_outbound_enabled,
            "provider_gateway_status_callback_set": self.provider_gateway_status_callback_set,
            "integration_watchdog_enabled": self.integration_watchdog_enabled,
            "outbound_allowlist_count": self.outbound_allowlist_count,
            "database_host": self.database_host,
            "database_is_local": self.database_is_local,
            "danger_flags": list(self.danger_flags),
            "warning_flags": list(self.warning_flags),
        }


def _parse_local_database_cidrs(env: dict[str, str] | None) -> list:
    source_env = env if env is not None else os.environ
    raw = (source_env.get("DATABASE_LOCAL_CIDRS") or "").strip()
    networks = []
    for item in raw.split(","):
        token = item.strip()
        if not token:
            continue
        try:
            networks.append(ip_network(token, strict=False))
        except ValueError:
            continue
    return networks


def classify_database_target(database_url: str | None, *, env: dict[str, str] | None = None) -> tuple[str, bool]:
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
    if host in LOCAL_DB_HOSTS:
        return host, True
    try:
        host_ip = ip_address(host)
    except ValueError:
        return host, False

    for network in _parse_local_database_cidrs(env):
        if host_ip in network:
            return host, True
    return host, False


def build_runtime_safety_snapshot(
    *,
    env: dict[str, str] | None = None,
    database_url: str | None = None,
) -> RuntimeSafetySnapshot:
    source_env = env if env is not None else os.environ
    eval_mode = get_eval_mode(source_env)
    transport_send_mode = get_transport_send_mode(source_env)
    outbox_worker_mode = get_outbox_worker_mode(source_env)
    test_mode_enabled = is_legacy_test_mode_enabled(source_env)
    outbox_worker_enabled = is_outbox_worker_enabled(source_env)
    provider_gateway_outbound_enabled = _is_env_enabled(
        source_env.get("PROVIDER_GATEWAY_OUTBOUND_ENABLED"),
        default=False,
    )
    callback_url = (source_env.get("PROVIDER_GATEWAY_STATUS_CALLBACK_URL") or "").strip()
    integration_watchdog_enabled = _is_env_enabled(
        source_env.get("INTEGRATION_WATCHDOG_ENABLED"),
        default=True,
    )
    allowlist = sorted(get_outbound_allowlist(source_env))

    resolved_database_url = database_url if database_url is not None else source_env.get("DATABASE_URL")
    if resolved_database_url is None:
        resolved_database_url = getattr(settings, "database_url", None)
    database_host, database_is_local = classify_database_target(resolved_database_url, env=source_env)

    danger_flags: list[str] = []
    warning_flags: list[str] = []

    if outbox_worker_mode == "local_debug" and not database_is_local:
        danger_flags.append("test_mode_outbox_worker_on_nonlocal_db")

    if outbox_worker_mode == "local_debug" and not allowlist:
        danger_flags.append("test_mode_outbox_worker_without_allowlist")

    if eval_mode != "prod" and outbox_worker_mode == "prod":
        danger_flags.append("outbox_prod_mode_in_nonprod_eval")

    if eval_mode != "prod" and transport_send_mode == "prod":
        warning_flags.append("transport_prod_mode_in_nonprod_eval")

    if provider_gateway_outbound_enabled and not callback_url:
        warning_flags.append("provider_gateway_outbound_missing_status_callback")

    return RuntimeSafetySnapshot(
        eval_mode=eval_mode,
        transport_send_mode=transport_send_mode,
        outbox_worker_mode=outbox_worker_mode,
        test_mode_enabled=test_mode_enabled,
        outbox_worker_enabled=outbox_worker_enabled,
        provider_gateway_outbound_enabled=provider_gateway_outbound_enabled,
        provider_gateway_status_callback_set=bool(callback_url),
        integration_watchdog_enabled=integration_watchdog_enabled,
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
