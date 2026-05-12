#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TRUFFLES_API_ROOT = ROOT / "truffles-api"
if str(TRUFFLES_API_ROOT) not in sys.path:
    sys.path.insert(0, str(TRUFFLES_API_ROOT))

from app.services.runtime_mode_service import get_eval_mode, get_transport_send_mode  # noqa: E402


def parse_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def _is_enabled(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def derive_outbox_worker_mode(env: dict[str, str]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    enabled = _is_enabled(env.get("OUTBOX_WORKER_ENABLED"), default=False)
    eval_mode = get_eval_mode(env)
    transport_send_mode = get_transport_send_mode(env)
    explicit_mode = (env.get("OUTBOX_WORKER_MODE") or "").strip().lower() or None

    if not enabled:
        derived = "off"
    elif eval_mode == "prod":
        derived = "prod"
    elif transport_send_mode == "allowlist":
        derived = "local_debug"
    else:
        derived = "off"

    if explicit_mode and explicit_mode != derived:
        warnings.append(
            f"env OUTBOX_WORKER_MODE={explicit_mode} conflicts with derived release mode={derived}"
        )
    return derived, warnings


def derive_webhook_enqueue_only(env: dict[str, str], *, outbox_worker_mode: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    derived = "1" if outbox_worker_mode in {"local_debug", "prod"} else "0"
    explicit = env.get("WEBHOOK_ENQUEUE_ONLY")
    if explicit is not None:
        explicit_enabled = "1" if _is_enabled(explicit, default=False) else "0"
        if explicit_enabled != derived:
            warnings.append(
                f"env WEBHOOK_ENQUEUE_ONLY={explicit} conflicts with derived release value={derived}"
            )
    return derived, warnings


def inspect_network_subnets(network: str) -> list[str]:
    try:
        completed = subprocess.run(
            ["docker", "network", "inspect", network],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return []
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list) or not payload:
        return []
    network_payload = payload[0] if isinstance(payload[0], dict) else {}
    ipam = network_payload.get("IPAM") if isinstance(network_payload.get("IPAM"), dict) else {}
    configs = ipam.get("Config") if isinstance(ipam.get("Config"), list) else []
    subnets: list[str] = []
    for item in configs:
        if not isinstance(item, dict):
            continue
        subnet = str(item.get("Subnet") or "").strip()
        if subnet:
            subnets.append(subnet)
    return subnets


def build_release_runtime_profile(env: dict[str, str], *, network: str) -> dict[str, Any]:
    outbox_worker_mode_override, warnings = derive_outbox_worker_mode(env)
    webhook_enqueue_only_override, enqueue_warnings = derive_webhook_enqueue_only(
        env,
        outbox_worker_mode=outbox_worker_mode_override,
    )
    warnings.extend(enqueue_warnings)
    database_local_cidrs = inspect_network_subnets(network)
    return {
        "outbox_worker_mode_override": outbox_worker_mode_override,
        "webhook_enqueue_only_override": webhook_enqueue_only_override,
        "database_local_cidrs": database_local_cidrs,
        "warnings": warnings,
        "eval_mode": get_eval_mode(env),
        "transport_send_mode": get_transport_send_mode(env),
        "network": network,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive release/runtime mode overrides for coherent API+worker startup."
    )
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--network", default="truffles_internal-net")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    env = parse_env_file(Path(args.env_file))
    payload = build_release_runtime_profile(env, network=args.network)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
