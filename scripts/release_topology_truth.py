#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any
from urllib import error, request

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = "docs/RELEASE_TOPOLOGY_TRUTH.yaml"


def load_config(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: invalid YAML mapping: {path}")
    return data


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_repo_contract(repo_root: Path, config: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    repo_contract = config.get("repo_contract") or {}

    release_script = repo_root / str(repo_contract.get("release_script", "scripts/restart_release.sh"))
    compose_path = repo_root / str(repo_contract.get("compose_file", "truffles-api/docker-compose.yml"))

    if not release_script.exists():
        return [f"missing release script: {release_script}"]
    if not compose_path.exists():
        return [f"missing compose file: {compose_path}"]

    release_text = _read_text(release_script)
    compose_text = _read_text(compose_path)

    for token in repo_contract.get("required_release_script_tokens") or []:
        if token not in release_text:
            violations.append(f"restart_release.sh missing required release token -> {token}")

    for token in repo_contract.get("required_compose_container_tokens") or []:
        if token not in compose_text:
            violations.append(f"docker-compose release cohort missing required container -> {token}")

    return violations


def _run(command: list[str]) -> str:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        detail = stderr or stdout or f"exit={completed.returncode}"
        raise RuntimeError(f"{' '.join(command)} failed: {detail}")
    return completed.stdout


def _fetch_api_version(base_url: str) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/admin/version"
    try:
        with request.urlopen(url, timeout=10) as response:
            payload = response.read().decode("utf-8")
    except error.URLError as exc:
        raise RuntimeError(f"failed to fetch {url}: {exc}") from exc
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON from {url}: {exc}") from exc
    data["endpoint"] = url
    return data


def _fetch_json(url: str) -> dict[str, Any]:
    try:
        with request.urlopen(url, timeout=10) as response:
            payload = response.read().decode("utf-8")
    except error.URLError as exc:
        raise RuntimeError(f"failed to fetch {url}: {exc}") from exc
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON from {url}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"invalid JSON object from {url}: expected object")
    return data


def _collect_running_containers() -> dict[str, dict[str, Any]]:
    output = _run(["docker", "ps", "--format", "{{json .}}"])
    containers: dict[str, dict[str, Any]] = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        containers[item["Names"]] = item
    return containers


def _inspect_container(name: str) -> dict[str, Any]:
    output = _run(["docker", "inspect", name])
    payload = json.loads(output)
    if not payload:
        raise RuntimeError(f"docker inspect returned no payload for {name}")
    data = payload[0]
    env_map: dict[str, str] = {}
    for item in data.get("Config", {}).get("Env", []) or []:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        env_map[key] = value
    return {
        "name": name,
        "image_id": data.get("Image"),
        "image_ref": data.get("Config", {}).get("Image"),
        "env": env_map,
        "status": data.get("State", {}).get("Status"),
    }


def _service_list(config: dict[str, Any], key: str) -> list[dict[str, Any]]:
    payload = config.get(key) or []
    if not isinstance(payload, list):
        raise SystemExit(f"ERROR: expected list for {key} in {DEFAULT_CONFIG}")
    return [item for item in payload if isinstance(item, dict) and item.get("name")]


def collect_live_snapshot(base_url: str, config: dict[str, Any]) -> dict[str, Any]:
    running = _collect_running_containers()
    shadow_configs = _service_list(config, "shadow_services")
    service_names = [
        item["name"]
        for key in ("required_services", "optional_active_services", "shadow_services")
        for item in _service_list(config, key)
    ]

    services: dict[str, dict[str, Any]] = {}
    for name in service_names:
        if name not in running:
            services[name] = {"name": name, "running": False}
            continue
        inspect_data = _inspect_container(name)
        services[name] = {
            "name": name,
            "running": True,
            "status": running[name].get("Status"),
            "image": running[name].get("Image"),
            "image_id": inspect_data.get("image_id"),
            "image_ref": inspect_data.get("image_ref"),
            "env": inspect_data.get("env", {}),
        }

    shadow_health: dict[str, Any] = {}
    for service_config in shadow_configs:
        name = str(service_config["name"])
        service = services.get(name, {})
        if not service.get("running"):
            continue
        health_url = service_config.get("health_url")
        if not health_url:
            continue
        try:
            shadow_health[name] = {"ok": True, "payload": _fetch_json(str(health_url))}
        except RuntimeError as exc:
            shadow_health[name] = {"ok": False, "error": str(exc), "url": str(health_url)}

    return {
        "api_version": _fetch_api_version(base_url),
        "services": services,
        "shadow_health": shadow_health,
    }


def _service_commit(service_name: str, service: dict[str, Any], api_version: dict[str, Any], service_config: dict[str, Any]) -> tuple[str | None, str | None]:
    if service_config.get("commit_source") == "admin_version":
        return api_version.get("git_commit"), api_version.get("build_time")

    env = service.get("env", {})
    commit = env.get(str(service_config.get("env_commit_key", "")))
    build_time = env.get(str(service_config.get("env_build_key", "")))
    return commit, build_time


def _evaluate_service(
    *,
    service_name: str,
    service: dict[str, Any],
    service_config: dict[str, Any],
    api_version: dict[str, Any],
) -> dict[str, Any]:
    commit, build_time = _service_commit(service_name, service, api_version, service_config)
    return {
        "running": True,
        "plane": service_config.get("plane"),
        "description": service_config.get("description"),
        "image": service.get("image"),
        "image_id": service.get("image_id"),
        "image_ref": service.get("image_ref"),
        "commit": commit,
        "build_time": build_time,
        "status": service.get("status"),
    }


def _health_value(payload: dict[str, Any], key: str) -> Any:
    current: Any = payload
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def evaluate_snapshot(
    snapshot: dict[str, Any],
    config: dict[str, Any],
    *,
    expected_commit: str | None = None,
    fail_on_active_shadow: bool = False,
) -> dict[str, Any]:
    services = snapshot.get("services", {})
    api_version = snapshot.get("api_version", {})
    shadow_health = snapshot.get("shadow_health", {})
    errors: list[str] = []
    warnings: list[str] = []

    required_configs = _service_list(config, "required_services")
    optional_configs = _service_list(config, "optional_active_services")
    shadow_configs = _service_list(config, "shadow_services")

    cohort_commit = expected_commit or api_version.get("git_commit")
    if not cohort_commit:
        errors.append("api /admin/version did not expose git_commit; release truth cannot be established")

    required_report: dict[str, Any] = {}
    image_groups: dict[str, dict[str, str]] = {}

    for service_config in required_configs:
        name = str(service_config["name"])
        service = services.get(name, {"running": False})
        if not service.get("running"):
            errors.append(f"required service not running -> {name}")
            required_report[name] = {
                "running": False,
                "plane": service_config.get("plane"),
                "description": service_config.get("description"),
            }
            continue

        entry = _evaluate_service(service_name=name, service=service, service_config=service_config, api_version=api_version)
        required_report[name] = entry

        image_cohort = service_config.get("image_cohort")
        image_id = service.get("image_id")
        if image_cohort:
            cohort = image_groups.setdefault(str(image_cohort), {})
            if image_id:
                cohort[name] = image_id
            else:
                errors.append(f"required runtime image id missing -> {name}")

        commit = entry["commit"]
        if not commit or commit == "unknown":
            errors.append(f"required service build fingerprint missing -> {name}")
        elif cohort_commit and commit != cohort_commit:
            errors.append(f"required service commit mismatch -> {name}: expected {cohort_commit}, got {commit}")

    for image_cohort, members in sorted(image_groups.items()):
        distinct_ids = {item for item in members.values() if item}
        if len(distinct_ids) > 1:
            errors.append(
                f"runtime image cohort drift [{image_cohort}] -> "
                + ", ".join(f"{name}={image_id}" for name, image_id in sorted(members.items()))
            )

    optional_report: dict[str, Any] = {}
    for service_config in optional_configs:
        name = str(service_config["name"])
        service = services.get(name, {"running": False})
        if not service.get("running"):
            continue
        entry = _evaluate_service(service_name=name, service=service, service_config=service_config, api_version=api_version)
        optional_report[name] = entry
        commit = entry["commit"]
        if not commit or commit == "unknown":
            errors.append(f"active optional service fingerprint missing -> {name}")
        elif cohort_commit and commit != cohort_commit:
            errors.append(f"active optional service commit mismatch -> {name}: expected {cohort_commit}, got {commit}")

    shadow_report: dict[str, Any] = {}
    active_shadow_report: dict[str, Any] = {}
    for service_config in shadow_configs:
        name = str(service_config["name"])
        service = services.get(name, {"running": False})
        entry: dict[str, Any] = {
            "running": bool(service.get("running")),
            "plane": service_config.get("plane"),
            "description": service_config.get("description"),
            "target_state": service_config.get("target_state", "shadow_only_disabled"),
            "canonical_surface": service_config.get("canonical_surface"),
        }
        if service.get("running"):
            entry.update(
                _evaluate_service(
                    service_name=name,
                    service=service,
                    service_config=service_config,
                    api_version=api_version,
                )
            )
        shadow_report[name] = entry

        if not service.get("running"):
            continue

        health_info = shadow_health.get(name)
        if health_info is not None:
            entry["health"] = health_info

        target_state = str(service_config.get("target_state", "shadow_only_disabled"))
        if target_state == "retired":
            message = f"retired shadow service still running -> {name}"
            errors.append(message)
            active_shadow_report[name] = entry
            continue

        disabled_fields = service_config.get("disabled_health_fields") or {}
        if not disabled_fields:
            message = f"shadow service target state missing disabled contract -> {name}"
            errors.append(message)
            active_shadow_report[name] = entry
            continue

        if not isinstance(health_info, dict) or not health_info.get("ok"):
            detail = "shadow health unavailable"
            if isinstance(health_info, dict) and health_info.get("error"):
                detail = str(health_info["error"])
            message = f"shadow service disabled-state proof missing -> {name}: {detail}"
            errors.append(message)
            active_shadow_report[name] = entry
            continue

        payload = health_info.get("payload")
        mismatches: list[str] = []
        if not isinstance(payload, dict):
            mismatches.append("health payload is not a JSON object")
        else:
            for field_name, expected_value in disabled_fields.items():
                actual_value = _health_value(payload, str(field_name))
                if actual_value != expected_value:
                    mismatches.append(f"{field_name} expected {expected_value!r}, got {actual_value!r}")

        entry["disabled_contract"] = {
            "expected_fields": disabled_fields,
            "valid": not mismatches,
            "mismatches": mismatches,
        }
        if mismatches:
            message = f"shadow service authority-active -> {name}: " + "; ".join(mismatches)
            errors.append(message)
            active_shadow_report[name] = entry
            continue

        message = f"shadow service still mounted in disabled mode -> {name}"
        if fail_on_active_shadow:
            errors.append(message)
            active_shadow_report[name] = entry
        else:
            warnings.append(message)

    return {
        "valid": not errors,
        "expected_commit": expected_commit,
        "cohort_commit": cohort_commit,
        "api_version": api_version,
        "required_services": required_report,
        "optional_active_services": optional_report,
        "shadow_services": shadow_report,
        "active_shadow_services": active_shadow_report,
        "errors": errors,
        "warnings": warnings,
    }


def run_truth(
    repo_root: Path,
    config_path: Path,
    *,
    base_url: str,
    expected_commit: str | None,
    fail_on_active_shadow: bool,
) -> dict[str, Any]:
    config = load_config(config_path)
    repo_violations = validate_repo_contract(repo_root, config)
    snapshot = collect_live_snapshot(base_url, config)
    live_report = evaluate_snapshot(
        snapshot,
        config,
        expected_commit=expected_commit,
        fail_on_active_shadow=fail_on_active_shadow,
    )
    return {
        "valid": not repo_violations and live_report["valid"],
        "repo_root": str(repo_root),
        "config_path": str(config_path),
        "contract_name": config.get("contract_name"),
        "contract_version": config.get("version"),
        "required_release_cohort": config.get("required_release_cohort"),
        "repo_contract_errors": repo_violations,
        "live_report": live_report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect Truffles release topology truth for the required production cohort and shadow-runtime target-state residue."
    )
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Machine-readable release truth contract YAML.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--expected-commit")
    parser.add_argument("--fail-on-active-shadow", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    config_path = (repo_root / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config).resolve()
    payload = run_truth(
        repo_root,
        config_path,
        base_url=args.base_url,
        expected_commit=args.expected_commit,
        fail_on_active_shadow=args.fail_on_active_shadow,
    )

    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
