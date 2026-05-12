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
DEFAULT_CONFIG = "docs/OBSERVABILITY_SURFACES.yaml"


def load_config(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: invalid YAML mapping: {path}")
    return data


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _fetch_url(url: str) -> tuple[int, str]:
    req = request.Request(url, headers={"User-Agent": "truffles-observability-truth/1.0"})
    with request.urlopen(req, timeout=10) as response:
        body = response.read().decode("utf-8")
        return response.getcode(), body


def _resolve_docker_http_url(proof: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    container = str(proof["docker_container"])
    port = int(proof["docker_port"])
    path = str(proof.get("path") or "/")
    if not path.startswith("/"):
        path = f"/{path}"

    try:
        completed = subprocess.run(
            ["docker", "inspect", container],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"docker inspect failed for {container}: {exc.stderr.strip() or exc.stdout.strip()}") from exc

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid docker inspect JSON for {container}: {exc}") from exc

    if not isinstance(payload, list) or not payload:
        raise RuntimeError(f"docker inspect returned no container payload for {container}")
    container_payload = payload[0] if isinstance(payload[0], dict) else {}
    networks = container_payload.get("NetworkSettings", {}).get("Networks", {}) or {}
    if not isinstance(networks, dict) or not networks:
        raise RuntimeError(f"container has no networks -> {container}")

    requested_network = proof.get("docker_network")
    selected_network = None
    selected_settings = None
    if requested_network:
        candidate = networks.get(str(requested_network))
        if isinstance(candidate, dict):
            selected_network = str(requested_network)
            selected_settings = candidate
    if selected_settings is None:
        selected_network = sorted(networks.keys())[0]
        candidate = networks.get(selected_network)
        selected_settings = candidate if isinstance(candidate, dict) else None
    if selected_settings is None:
        raise RuntimeError(f"unable to resolve docker network settings -> {container}")

    ip_address = str(selected_settings.get("IPAddress") or "").strip()
    if not ip_address:
        raise RuntimeError(f"container IP missing for {container} on network {selected_network}")

    url = f"http://{ip_address}:{port}{path}"
    details = {
        "docker_container": container,
        "docker_network": selected_network,
        "docker_ip": ip_address,
        "docker_port": port,
        "docker_path": path,
        "resolved_url": url,
    }
    return url, details


def _inspect_docker_container(container: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["docker", "inspect", container],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return {
            "exists": False,
            "running": False,
            "status": "missing",
            "error": completed.stderr.strip() or completed.stdout.strip(),
        }

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return {
            "exists": False,
            "running": False,
            "status": "invalid_inspect_json",
            "error": str(exc),
        }

    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
        return {
            "exists": False,
            "running": False,
            "status": "missing_payload",
            "error": "docker inspect returned no container payload",
        }

    state = payload[0].get("State") or {}
    return {
        "exists": True,
        "running": bool(state.get("Running")),
        "status": str(state.get("Status") or "unknown"),
    }


def _fetch_prometheus_targets(url: str) -> dict[str, Any]:
    try:
        _status, body = _fetch_url(url)
    except error.URLError as exc:
        raise RuntimeError(f"failed to fetch Prometheus targets from {url}: {exc}") from exc
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid Prometheus target JSON from {url}: {exc}") from exc
    return payload


def _load_yaml_file(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _load_json_file(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


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
                violations.append(f"{rel_path} missing required observability token -> {token}")
    return violations


def _proof_registry(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    proofs = config.get("proofs") or {}
    for proof in proofs.get("prometheus_targets") or []:
        registry[str(proof["id"])] = {"kind": "prometheus_target", **proof}
    for proof in proofs.get("http_checks") or []:
        registry[str(proof["id"])] = {"kind": "http_check", **proof}
    for proof in proofs.get("shadow_state_checks") or []:
        registry[str(proof["id"])] = {"kind": "shadow_state_check", **proof}
    for proof in proofs.get("yaml_checks") or []:
        registry[str(proof["id"])] = {"kind": "yaml_check", **proof}
    for proof in proofs.get("json_checks") or []:
        registry[str(proof["id"])] = {"kind": "json_check", **proof}
    return registry


def _configured_prometheus_jobs(path: Path) -> list[str]:
    if not path.exists():
        return []
    data = _load_yaml_file(path)
    jobs = []
    for item in data.get("scrape_configs") or []:
        job = item.get("job_name")
        if isinstance(job, str):
            jobs.append(job)
    return jobs


def _active_prometheus_targets(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") or {}
    targets = data.get("activeTargets") or []
    return [item for item in targets if isinstance(item, dict)]


def _evaluate_prometheus_target(proof: dict[str, Any], active_targets: list[dict[str, Any]], configured_jobs: list[str]) -> dict[str, Any]:
    job = str(proof["job"])
    matching = [item for item in active_targets if (item.get("labels") or {}).get("job") == job]
    scrape_url = proof.get("scrape_url")
    target = None
    if scrape_url:
        for item in matching:
            if item.get("scrapeUrl") == scrape_url:
                target = item
                break
    elif matching:
        target = matching[0]

    ok = bool(target) and target.get("health") == "up" and job in configured_jobs
    details = {
        "kind": "prometheus_target",
        "job": job,
        "configured_job_present": job in configured_jobs,
        "matching_targets": [
            {
                "scrape_url": item.get("scrapeUrl"),
                "health": item.get("health"),
            }
            for item in matching
        ],
    }
    if target is not None:
        details["selected_target"] = {
            "scrape_url": target.get("scrapeUrl"),
            "health": target.get("health"),
        }
    if scrape_url:
        details["expected_scrape_url"] = scrape_url
    return {"ok": ok, "details": details}


def _evaluate_http_check(proof: dict[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    if "docker_container" in proof:
        try:
            url, resolved = _resolve_docker_http_url(proof)
        except Exception as exc:
            return {
                "ok": False,
                "details": {
                    "kind": "http_check",
                    "error": str(exc),
                    **resolved,
                },
            }
    else:
        url = str(proof["url"])
    try:
        status, body = _fetch_url(url)
    except Exception as exc:  # pragma: no cover - covered via monkeypatch tests
        return {
            "ok": False,
            "details": {
                "kind": "http_check",
                "url": url,
                "error": str(exc),
                **resolved,
            },
        }

    ok = 200 <= status < 400
    details: dict[str, Any] = {
        "kind": "http_check",
        "url": url,
        "status_code": status,
        **resolved,
    }
    if ok and "expect_substring" in proof:
        expected = str(proof["expect_substring"])
        ok = expected in body
        details["expect_substring"] = expected
        details["substring_found"] = expected in body
    if ok and "expect_json" in proof:
        expected_json = proof["expect_json"] or {}
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            ok = False
            details["error"] = "invalid_json"
        else:
            matches = True
            for key, value in expected_json.items():
                if payload.get(key) != value:
                    matches = False
                    break
            ok = matches
            details["expect_json"] = expected_json
            details["observed_json_keys"] = sorted(payload.keys())
    return {"ok": ok, "details": details}


def _json_value(payload: dict[str, Any], key: str) -> Any:
    current: Any = payload
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _evaluate_shadow_state_check(proof: dict[str, Any]) -> dict[str, Any]:
    container = str(proof["docker_container"])
    accepted_states = {str(item) for item in proof.get("accepted_states") or ["running_disabled", "stopped"]}
    stopped_statuses = {str(item) for item in proof.get("accepted_stopped_statuses") or ["created", "exited"]}
    state = _inspect_docker_container(container)
    details: dict[str, Any] = {
        "kind": "shadow_state_check",
        "docker_container": container,
        "accepted_states": sorted(accepted_states),
        "docker_state": state,
    }

    if not state.get("exists"):
        observed_state = "absent"
        details["observed_shadow_state"] = observed_state
        return {"ok": observed_state in accepted_states, "details": details}

    if not state.get("running"):
        observed_state = "stopped"
        details["observed_shadow_state"] = observed_state
        details["accepted_stopped_statuses"] = sorted(stopped_statuses)
        ok = observed_state in accepted_states and str(state.get("status")) in stopped_statuses
        return {"ok": ok, "details": details}

    if "running_disabled" not in accepted_states:
        details["observed_shadow_state"] = "running"
        return {"ok": False, "details": details}

    health_url = str(proof["health_url"])
    try:
        status, body = _fetch_url(health_url)
    except Exception as exc:
        details["observed_shadow_state"] = "running_health_unavailable"
        details["health_url"] = health_url
        details["error"] = str(exc)
        return {"ok": False, "details": details}

    details["health_url"] = health_url
    details["health_status_code"] = status
    mismatches: list[str] = []
    if not 200 <= status < 400:
        mismatches.append(f"health_status_code expected 2xx/3xx, got {status}")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        details["observed_shadow_state"] = "running_invalid_health_json"
        details["error"] = "invalid_json"
        return {"ok": False, "details": details}

    for key, expected in (proof.get("expect_json") or {}).items():
        actual = _json_value(payload, str(key))
        if actual != expected:
            mismatches.append(f"{key} expected {expected!r}, got {actual!r}")
    for key, expected in (proof.get("disabled_health_fields") or {}).items():
        actual = _json_value(payload, str(key))
        if actual != expected:
            mismatches.append(f"{key} expected {expected!r}, got {actual!r}")

    details["observed_json_keys"] = sorted(payload.keys())
    details["disabled_health_fields"] = proof.get("disabled_health_fields") or {}
    details["mismatches"] = mismatches
    details["observed_shadow_state"] = "running_disabled" if not mismatches else "running_authority_or_unhealthy"
    return {"ok": not mismatches, "details": details}


def _evaluate_yaml_check(proof: dict[str, Any]) -> dict[str, Any]:
    path = Path(str(proof["path"]))
    if not path.exists():
        return {
            "ok": False,
            "details": {
                "kind": "yaml_check",
                "path": str(path),
                "error": "missing_file",
            },
        }

    payload = _load_yaml_file(path)
    observed_names = []
    for item in payload.get("datasources") or []:
        name = item.get("name")
        if isinstance(name, str):
            observed_names.append(name)
    expected_names = [str(item) for item in proof.get("expected_datasource_names") or []]
    ok = all(name in observed_names for name in expected_names)
    return {
        "ok": ok,
        "details": {
            "kind": "yaml_check",
            "path": str(path),
            "expected_datasource_names": expected_names,
            "observed_datasource_names": observed_names,
        },
    }


def _evaluate_json_check(proof: dict[str, Any]) -> dict[str, Any]:
    path = Path(str(proof["path"]))
    if not path.exists():
        return {
            "ok": False,
            "details": {
                "kind": "json_check",
                "path": str(path),
                "error": "missing_file",
            },
        }

    payload = _load_json_file(path)
    expected_title = proof.get("expected_title")
    observed_title = payload.get("title")
    ok = observed_title == expected_title
    return {
        "ok": ok,
        "details": {
            "kind": "json_check",
            "path": str(path),
            "expected_title": expected_title,
            "observed_title": observed_title,
        },
    }


def collect_proof_results(config: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    inputs = config.get("live_inputs") or {}
    prometheus_api_url = str(inputs.get("prometheus_api_url", "http://localhost:9090/api/v1/targets"))
    prometheus_payload = _fetch_prometheus_targets(prometheus_api_url)
    active_targets = _active_prometheus_targets(prometheus_payload)
    configured_jobs = _configured_prometheus_jobs(Path(str(inputs.get("prometheus_config_path", ""))))

    registry = _proof_registry(config)
    proof_results: dict[str, dict[str, Any]] = {}
    for proof_id, proof in registry.items():
        kind = proof["kind"]
        if kind == "prometheus_target":
            proof_results[proof_id] = _evaluate_prometheus_target(proof, active_targets, configured_jobs)
        elif kind == "http_check":
            proof_results[proof_id] = _evaluate_http_check(proof)
        elif kind == "shadow_state_check":
            proof_results[proof_id] = _evaluate_shadow_state_check(proof)
        elif kind == "yaml_check":
            proof_results[proof_id] = _evaluate_yaml_check(proof)
        elif kind == "json_check":
            proof_results[proof_id] = _evaluate_json_check(proof)
        else:  # pragma: no cover
            proof_results[proof_id] = {
                "ok": False,
                "details": {"kind": kind, "error": "unknown_proof_kind"},
            }

    live_context = {
        "prometheus_api_url": prometheus_api_url,
        "configured_prometheus_jobs": configured_jobs,
        "active_prometheus_targets": [
            {
                "job": (item.get("labels") or {}).get("job"),
                "scrape_url": item.get("scrapeUrl"),
                "health": item.get("health"),
            }
            for item in active_targets
        ],
    }
    return proof_results, live_context


def evaluate_required_surfaces(config: dict[str, Any], proof_results: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    surfaces: dict[str, Any] = {}
    for surface in config.get("required_surfaces") or []:
        name = str(surface["surface"])
        proof_ids = [str(item) for item in surface.get("proof_ids") or []]
        if not proof_ids:
            message = f"surface has no observability proof mapping -> {name}: {surface.get('gap_reason', 'missing proof ids')}"
            errors.append(message)
            surfaces[name] = {
                "ok": False,
                "plane": surface.get("plane"),
                "description": surface.get("description"),
                "gap_reason": surface.get("gap_reason"),
                "proof_ids": [],
            }
            continue

        missing_proof_ids = [proof_id for proof_id in proof_ids if proof_id not in proof_results]
        failed_proof_ids = [proof_id for proof_id in proof_ids if proof_id in proof_results and not proof_results[proof_id]["ok"]]
        ok = not missing_proof_ids and not failed_proof_ids
        if missing_proof_ids:
            errors.append(f"surface references unknown proofs -> {name}: {', '.join(missing_proof_ids)}")
        if failed_proof_ids:
            errors.append(f"surface proof failures -> {name}: {', '.join(failed_proof_ids)}")

        surfaces[name] = {
            "ok": ok,
            "plane": surface.get("plane"),
            "description": surface.get("description"),
            "proof_ids": proof_ids,
            "failed_proof_ids": failed_proof_ids,
            "missing_proof_ids": missing_proof_ids,
            "gap_reason": surface.get("gap_reason"),
        }

    return surfaces, errors


def run_truth(repo_root: Path, config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    repo_contract_errors = validate_repo_contract(repo_root, config)
    proof_results, live_context = collect_proof_results(config)
    surface_results, surface_errors = evaluate_required_surfaces(config, proof_results)
    valid = not repo_contract_errors and not surface_errors
    return {
        "valid": valid,
        "repo_root": str(repo_root),
        "config_path": str(config_path),
        "contract_name": config.get("contract_name"),
        "contract_version": config.get("version"),
        "repo_contract_errors": repo_contract_errors,
        "surface_errors": surface_errors,
        "proof_results": proof_results,
        "surface_results": surface_results,
        "live_context": live_context,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect whole-system observability truth against the persistent repo contract."
    )
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    config_path = (repo_root / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config).resolve()
    payload = run_truth(repo_root, config_path)

    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
