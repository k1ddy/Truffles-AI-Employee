#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = "docs/PROVIDER_INTEGRATION_READINESS.yaml"
DEFAULT_ENV_CANDIDATES = (
    ROOT / "truffles-api" / ".env",
    Path("/home/zhan/truffles-main/truffles-api/.env"),
)


def load_config(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: invalid YAML mapping: {path}")
    return data


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_repo_contract(repo_root: Path, config: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    for rule in (config.get("repo_contract") or {}).get("required_file_tokens") or []:
        rel_path = rule.get("path")
        tokens = rule.get("tokens") or []
        if not rel_path:
            continue
        path = repo_root / str(rel_path)
        if not path.exists():
            violations.append(f"required contract file missing -> {rel_path}")
            continue
        text = _read_text(path)
        for token in tokens:
            if token not in text:
                violations.append(f"{rel_path} missing required provider integration token -> {token}")
    return violations


def parse_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            env[key] = value
    return env


def resolve_env_file(explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit)
    for candidate in DEFAULT_ENV_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def apply_env_file(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    env = parse_env_file(path)
    for key, value in env.items():
        os.environ.setdefault(key, value)
    return env


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _normalize(value: Any) -> str:
    return str(value or "").strip().lower()


def _env_enabled(env: dict[str, str], name: str, *, default: bool = False) -> bool:
    raw = env.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(env: dict[str, str], name: str, *, default: int) -> int:
    raw = env.get(name)
    if raw is None:
        return default
    try:
        return max(int(raw.strip()), 1)
    except (TypeError, ValueError):
        return default


def _fetch_json(url: str) -> dict[str, Any]:
    try:
        with request.urlopen(url, timeout=10) as response:
            body = response.read().decode("utf-8")
            status = response.getcode()
    except error.URLError as exc:
        return {"ok": False, "url": url, "error": str(exc)}
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        return {"ok": False, "url": url, "http_status": status, "error": f"invalid_json:{exc}"}
    if not isinstance(payload, dict):
        return {"ok": False, "url": url, "http_status": status, "error": "expected_json_object"}
    return {"ok": 200 <= status < 300, "url": url, "http_status": status, "payload": payload}


def _extract_instance_id_from_metadata(metadata: dict[str, Any] | None) -> str | None:
    if not isinstance(metadata, dict):
        return None
    direct = metadata.get("instanceId") or metadata.get("instance_id")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    nested = metadata.get("metadata")
    if isinstance(nested, dict):
        nested_value = nested.get("instanceId") or nested.get("instance_id")
        if isinstance(nested_value, str) and nested_value.strip():
            return nested_value.strip()
    return None


def _extract_origin(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        return {}
    tenant_context = metadata.get("tenant_context") if isinstance(metadata.get("tenant_context"), dict) else {}
    return {
        "source": metadata.get("source"),
        "origin_source": tenant_context.get("origin_source") if isinstance(tenant_context, dict) else None,
        "message_id": metadata.get("messageId") or metadata.get("message_id"),
    }


def _load_runtime_imports(repo_root: Path):
    api_root = repo_root / "truffles-api"
    if str(api_root) not in sys.path:
        sys.path.insert(0, str(api_root))
    import app.models  # noqa: F401
    from app.database import SessionLocal
    from app.models.branch import Branch
    from app.models.client import Client
    from app.models.conversation import Conversation
    from app.models.message import Message

    return {
        "SessionLocal": SessionLocal,
        "Branch": Branch,
        "Client": Client,
        "Conversation": Conversation,
        "Message": Message,
    }


def _latest_message(db: Any, imports: dict[str, Any], *, branch_id: Any, roles: tuple[str, ...]):
    Message = imports["Message"]
    Conversation = imports["Conversation"]
    return (
        db.query(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .filter(Conversation.branch_id == branch_id, Message.role.in_(list(roles)))
        .order_by(Message.created_at.desc())
        .first()
    )


def _message_count(db: Any, imports: dict[str, Any], *, branch_id: Any, roles: tuple[str, ...]) -> int:
    Message = imports["Message"]
    Conversation = imports["Conversation"]
    return int(
        db.query(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .filter(Conversation.branch_id == branch_id, Message.role.in_(list(roles)))
        .count()
    )


def _age_minutes(value: Any, *, now: datetime) -> float | None:
    if value is None:
        return None
    if getattr(value, "tzinfo", None) is None:
        value = value.replace(tzinfo=timezone.utc)
    return round((now - value).total_seconds() / 60, 2)


def collect_route_probes(base_url: str | None, *, client_slug: str) -> dict[str, Any]:
    if not base_url:
        return {"canonical_webhook_probe": {"ok": False, "skipped": True, "reason": "base_url_missing"}}
    url = f"{base_url.rstrip('/')}/webhook/{client_slug}"
    probe = _fetch_json(url)
    payload = probe.get("payload") if isinstance(probe.get("payload"), dict) else {}
    expected = payload.get("ok") is True and payload.get("client_slug") == client_slug
    probe["ok"] = bool(probe.get("ok")) and expected
    if not expected and "error" not in probe:
        probe["error"] = "unexpected_probe_payload"
    return {"canonical_webhook_probe": probe}


def collect_live_snapshot(
    repo_root: Path,
    config: dict[str, Any],
    *,
    env_file: Path | None,
    base_url: str | None,
) -> dict[str, Any]:
    loaded_env = apply_env_file(env_file)
    effective_env = {**loaded_env, **{key: value for key, value in os.environ.items() if key not in loaded_env}}
    imports = _load_runtime_imports(repo_root)
    SessionLocal = imports["SessionLocal"]
    Client = imports["Client"]
    Branch = imports["Branch"]

    target_config = config.get("target") or {}
    client_slug = str(target_config.get("client_slug") or "").strip()
    branch_slug = str(target_config.get("branch_slug") or "").strip()
    now = datetime.now(timezone.utc)
    stale_after_minutes = _env_int(effective_env, "INTEGRATION_WATCHDOG_STALE_MINUTES", default=120)

    with SessionLocal() as db:
        client = db.query(Client).filter(Client.name == client_slug).first() if client_slug else None
        branch = None
        if client is not None and branch_slug:
            branch = db.query(Branch).filter(Branch.client_id == client.id, Branch.slug == branch_slug).first()

        if client is None:
            target: dict[str, Any] = {"client_slug": client_slug, "branch_slug": branch_slug, "client_found": False, "branch_found": False}
        elif branch is None:
            target = {
                "client_id": str(client.id),
                "client_slug": client.name,
                "branch_slug": branch_slug,
                "client_found": True,
                "branch_found": False,
            }
        else:
            latest_inbound = _latest_message(db, imports, branch_id=branch.id, roles=("user",))
            latest_outbound = _latest_message(db, imports, branch_id=branch.id, roles=("assistant", "manager", "system"))
            latest_inbound_at = getattr(latest_inbound, "created_at", None) if latest_inbound is not None else None
            latest_outbound_at = getattr(latest_outbound, "created_at", None) if latest_outbound is not None else None
            inbound_metadata = getattr(latest_inbound, "message_metadata", None) if latest_inbound is not None else None
            target = {
                "client_id": str(client.id),
                "client_slug": client.name,
                "client_status": getattr(client, "status", None),
                "client_found": True,
                "branch_id": str(branch.id),
                "branch_slug": branch.slug,
                "branch_name": branch.name,
                "branch_found": True,
                "branch_active": bool(branch.is_active),
                "branch_phone_present": bool(getattr(branch, "phone", None)),
                "instance_id_present": bool(getattr(branch, "instance_id", None)),
                "webhook_secret_present": bool(getattr(branch, "webhook_secret", None)),
                "go_live_state": getattr(branch, "go_live_state", None),
                "integration_state": getattr(branch, "integration_state", None),
                "integration_reason": getattr(branch, "integration_reason", None),
                "integration_checked_at": _jsonable(getattr(branch, "integration_checked_at", None)),
                "integration_degraded_at": _jsonable(getattr(branch, "integration_degraded_at", None)),
                "integration_recovered_at": _jsonable(getattr(branch, "integration_recovered_at", None)),
                "latest_inbound_at": _jsonable(latest_inbound_at),
                "latest_inbound_age_minutes": _age_minutes(latest_inbound_at, now=now),
                "latest_inbound_instance_matches": (
                    _extract_instance_id_from_metadata(inbound_metadata) == getattr(branch, "instance_id", None)
                    if latest_inbound is not None and getattr(branch, "instance_id", None)
                    else None
                ),
                "latest_inbound_origin": _extract_origin(inbound_metadata),
                "latest_outbound_at": _jsonable(latest_outbound_at),
                "latest_outbound_age_minutes": _age_minutes(latest_outbound_at, now=now),
                "inbound_count": _message_count(db, imports, branch_id=branch.id, roles=("user",)),
                "outbound_count": _message_count(db, imports, branch_id=branch.id, roles=("assistant", "manager", "system")),
            }

    env_report = {
        "env_file": str(env_file) if env_file else None,
        "public_base_url": effective_env.get("PUBLIC_BASE_URL"),
        "provider_gateway_inbound_enabled": _env_enabled(effective_env, "PROVIDER_GATEWAY_INBOUND_ENABLED", default=False),
        "provider_gateway_status_enabled": _env_enabled(effective_env, "PROVIDER_GATEWAY_STATUS_ENABLED", default=False),
        "provider_gateway_inbox_enabled": _env_enabled(effective_env, "PROVIDER_GATEWAY_INBOX_ENABLED", default=False),
        "provider_gateway_outbound_enabled": _env_enabled(effective_env, "PROVIDER_GATEWAY_OUTBOUND_ENABLED", default=False),
        "integration_watchdog_enabled": _env_enabled(effective_env, "INTEGRATION_WATCHDOG_ENABLED", default=True),
        "integration_watchdog_stale_minutes": stale_after_minutes,
        "no_recent_inbound_hard_degrade_enabled": _env_enabled(
            effective_env,
            "INTEGRATION_WATCHDOG_NO_RECENT_INBOUND_DEGRADES",
            default=False,
        ),
    }

    return {
        "checked_at": now.isoformat(),
        "target": _jsonable(target),
        "env": env_report,
        "route_probes": collect_route_probes(base_url, client_slug=client_slug),
    }


def _target_errors(snapshot: dict[str, Any], config: dict[str, Any]) -> list[str]:
    target = snapshot.get("target") if isinstance(snapshot.get("target"), dict) else {}
    env = snapshot.get("env") if isinstance(snapshot.get("env"), dict) else {}
    probes = snapshot.get("route_probes") if isinstance(snapshot.get("route_probes"), dict) else {}
    required = config.get("required_target_checks") or {}
    errors: list[str] = []

    if not target.get("client_found"):
        errors.append("target client not found")
        return errors
    if not target.get("branch_found"):
        errors.append("target branch not found")
        return errors

    if required.get("client_status") and _normalize(target.get("client_status")) != _normalize(required.get("client_status")):
        errors.append(f"target client_status mismatch -> expected={required.get('client_status')} actual={target.get('client_status')}")
    if bool(target.get("branch_active")) is not bool(required.get("branch_active", True)):
        errors.append(f"target branch_active mismatch -> expected={required.get('branch_active', True)} actual={target.get('branch_active')}")
    if required.get("branch_go_live_state") and _normalize(target.get("go_live_state")) != _normalize(required.get("branch_go_live_state")):
        errors.append(f"target go_live_state mismatch -> expected={required.get('branch_go_live_state')} actual={target.get('go_live_state')}")
    if bool(target.get("instance_id_present")) is not bool(required.get("instance_id_present", True)):
        errors.append("target instance_id missing")
    if bool(target.get("webhook_secret_present")) is not bool(required.get("webhook_secret_present", True)):
        errors.append("target webhook_secret missing")
    if bool(env.get("public_base_url")) is not bool(required.get("public_base_url_present", True)):
        errors.append("PUBLIC_BASE_URL missing")
    if bool(env.get("provider_gateway_inbound_enabled")) is not bool(required.get("provider_gateway_inbound_enabled", True)):
        errors.append(
            "provider gateway inbound enablement mismatch -> "
            f"expected={required.get('provider_gateway_inbound_enabled', True)} actual={env.get('provider_gateway_inbound_enabled')}"
        )
    if required.get("integration_state") and _normalize(target.get("integration_state")) != _normalize(required.get("integration_state")):
        errors.append(
            "target integration_state mismatch -> "
            f"expected={required.get('integration_state')} actual={target.get('integration_state')} reason={target.get('integration_reason')}"
        )
    if required.get("no_recent_inbound_hard_degrade_disabled", True) and bool(env.get("no_recent_inbound_hard_degrade_enabled")):
        errors.append("INTEGRATION_WATCHDOG_NO_RECENT_INBOUND_DEGRADES must be disabled for go-live readiness")
    probe = probes.get("canonical_webhook_probe") if isinstance(probes.get("canonical_webhook_probe"), dict) else {}
    if required.get("canonical_webhook_probe_ok", True) and not bool(probe.get("ok")):
        errors.append(f"canonical webhook probe failed -> {probe.get('error') or probe.get('http_status') or 'unknown'}")
    return errors


def _target_warnings(snapshot: dict[str, Any], config: dict[str, Any]) -> list[str]:
    target = snapshot.get("target") if isinstance(snapshot.get("target"), dict) else {}
    env = snapshot.get("env") if isinstance(snapshot.get("env"), dict) else {}
    warnings: list[str] = []
    stale_after = env.get("integration_watchdog_stale_minutes") or 120
    age = target.get("latest_inbound_age_minutes")
    if isinstance(age, (int, float)) and age > stale_after:
        warnings.append(f"latest inbound is stale -> age_minutes={age} stale_after_minutes={stale_after}")
    if target.get("latest_inbound_at") is None:
        warnings.append("no inbound has ever been recorded for target branch")
    origin = target.get("latest_inbound_origin") if isinstance(target.get("latest_inbound_origin"), dict) else {}
    if origin and origin.get("origin_source") not in {"provider", "chatflow", "whatsapp", None}:
        warnings.append(
            "latest inbound origin is not external-provider proof -> "
            f"source={origin.get('source')} origin_source={origin.get('origin_source')}"
        )
    if not env.get("provider_gateway_outbound_enabled"):
        warnings.append("provider gateway outbound is disabled; outbound uses canonical outbox/transport path")
    if config.get("residual_policy", {}).get("do_not_hide_external_canary_gap"):
        warnings.append("external provider canary is not proven by this local route/config truth")
    return warnings


def _current_owner_truth(config: dict[str, Any]) -> dict[str, Any]:
    truth = config.get("current_owner_truth")
    return truth if isinstance(truth, dict) else {}


def _external_channel_errors(config: dict[str, Any]) -> list[str]:
    truth = _current_owner_truth(config)
    status = _normalize(truth.get("chatflow_whatsapp_status"))
    if status in {"commercially_unavailable", "unpaid", "not_enabled", "disabled"}:
        reason = truth.get("reason") or status
        return [f"CHATFLOW_WHATSAPP_COMMERCIALLY_UNAVAILABLE -> reason={reason}"]
    return []


def _external_channel_warnings(config: dict[str, Any]) -> list[str]:
    truth = _current_owner_truth(config)
    if not truth:
        return []
    warnings: list[str] = []
    does_not_block = truth.get("does_not_block")
    if does_not_block:
        warnings.append(f"owner truth: provider channel blocker does not block {does_not_block}")
    return warnings


def evaluate_snapshot(snapshot: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    repo_errors = list(snapshot.get("repo_contract_errors") or [])
    target_errors = _target_errors(snapshot, config)
    external_channel_errors = _external_channel_errors(config)
    errors = repo_errors + target_errors + external_channel_errors
    warnings = _target_warnings(snapshot, config) + _external_channel_warnings(config)
    return {
        "valid": not errors,
        "contract_name": config.get("contract_name"),
        "version": config.get("version"),
        "target": snapshot.get("target"),
        "env": snapshot.get("env"),
        "route_probes": snapshot.get("route_probes"),
        "target_verdict": {
            "provider_integration_ready": not target_errors and not external_channel_errors,
            "config_route_ready": not target_errors,
            "external_channel_ready": not external_channel_errors,
            "internal_booking_blocked_by_provider": False,
            "stale_inbound_warning_only": True,
            "external_provider_canary_proven": False,
        },
        "errors": errors,
        "warnings": warnings,
        "repo_contract_errors": repo_errors,
        "snapshot": snapshot,
    }


def run_truth(
    repo_root: Path,
    config_path: Path,
    *,
    env_file: Path | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    config = load_config(config_path)
    repo_errors = validate_repo_contract(repo_root, config)
    snapshot = collect_live_snapshot(repo_root, config, env_file=env_file, base_url=base_url)
    snapshot["repo_contract_errors"] = repo_errors
    return evaluate_snapshot(snapshot, config)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate provider integration readiness for the first go-live tenant.")
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = repo_root / config_path
    env_file = resolve_env_file(args.env_file)

    payload = run_truth(repo_root, config_path, env_file=env_file, base_url=args.base_url)
    rendered = json.dumps(_jsonable(payload), ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if payload.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
