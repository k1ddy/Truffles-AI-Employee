from __future__ import annotations

import os

_TRUE_VALUES = {"1", "true", "yes", "on"}
_VALID_EVAL_MODES = {"local", "livecheck", "acceptance", "prod"}
_VALID_TRANSPORT_SEND_MODES = {"off", "allowlist", "prod"}
_VALID_OUTBOX_WORKER_MODES = {"off", "local_debug", "prod"}


def _source_env(env: dict[str, str] | None) -> dict[str, str]:
    return env if env is not None else os.environ


def _normalize_mode(raw: str | None, *, valid: set[str]) -> str | None:
    value = str(raw or "").strip().lower()
    if not value:
        return None
    if value in valid:
        return value
    return None


def _is_env_enabled(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in _TRUE_VALUES


def is_legacy_test_mode_enabled(env: dict[str, str] | None = None) -> bool:
    return _is_env_enabled(_source_env(env).get("TEST_MODE"), default=False)


def get_outbound_allowlist(env: dict[str, str] | None = None) -> set[str]:
    raw = _source_env(env).get("OUTBOUND_ALLOWLIST_JIDS") or ""
    return {jid.strip() for jid in raw.split(",") if jid.strip()}


def get_eval_mode(env: dict[str, str] | None = None) -> str:
    source_env = _source_env(env)
    if is_legacy_test_mode_enabled(source_env):
        return "local"
    explicit = _normalize_mode(source_env.get("EVAL_MODE"), valid=_VALID_EVAL_MODES)
    if explicit:
        return explicit
    return "prod"


def is_local_eval_mode(env: dict[str, str] | None = None) -> bool:
    return get_eval_mode(env) == "local"


def is_nonprod_eval_mode(env: dict[str, str] | None = None) -> bool:
    return get_eval_mode(env) != "prod"


def get_transport_send_mode(env: dict[str, str] | None = None) -> str:
    source_env = _source_env(env)
    explicit = _normalize_mode(
        source_env.get("TRANSPORT_SEND_MODE"),
        valid=_VALID_TRANSPORT_SEND_MODES,
    )
    if explicit:
        return explicit

    eval_mode = get_eval_mode(source_env)
    if eval_mode == "livecheck":
        return "allowlist"
    if eval_mode != "prod":
        return "off"
    return "prod"


def should_block_outbound(
    remote_jid: str | None,
    *,
    env: dict[str, str] | None = None,
) -> tuple[bool, str]:
    source_env = _source_env(env)
    transport_send_mode = get_transport_send_mode(source_env)
    jid = str(remote_jid or "").strip()
    if transport_send_mode == "off":
        return True, "transport_send_off"
    if transport_send_mode == "allowlist":
        if jid and jid in get_outbound_allowlist(source_env):
            return False, "ok"
        return True, "transport_allowlist_guard"
    return False, "ok"


def get_outbox_worker_mode(env: dict[str, str] | None = None) -> str:
    source_env = _source_env(env)
    eval_mode = get_eval_mode(source_env)
    enabled_token = source_env.get("OUTBOX_WORKER_ENABLED")
    if is_legacy_test_mode_enabled(source_env) and enabled_token is not None:
        return "local_debug" if _is_env_enabled(enabled_token, default=False) else "off"
    explicit = _normalize_mode(
        source_env.get("OUTBOX_WORKER_MODE"),
        valid=_VALID_OUTBOX_WORKER_MODES,
    )
    if explicit:
        return explicit

    enabled_by_default = eval_mode == "prod"
    if not _is_env_enabled(source_env.get("OUTBOX_WORKER_ENABLED"), default=enabled_by_default):
        return "off"

    if eval_mode != "prod":
        return "local_debug"
    return "prod"


def is_outbox_worker_enabled(env: dict[str, str] | None = None) -> bool:
    return get_outbox_worker_mode(env) in {"local_debug", "prod"}


def should_use_outbox_send(env: dict[str, str] | None = None) -> bool:
    return get_outbox_worker_mode(env) == "prod"
