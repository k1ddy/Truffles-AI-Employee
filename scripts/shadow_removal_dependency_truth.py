#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, NamedTuple


class ShadowService(NamedTuple):
    key: str
    container_name: str
    app_path: str
    restart_script: str
    port: int


SHADOW_SERVICES: tuple[ShadowService, ...] = (
    ShadowService(
        key="provider_gateway",
        container_name="truffles-provider-gateway",
        app_path="truffles-api/app/provider_gateway_app.py",
        restart_script="scripts/restart_provider_gateway.sh",
        port=8011,
    ),
    ShadowService(
        key="knowledge_gateway",
        container_name="truffles-knowledge-gateway",
        app_path="truffles-api/app/knowledge_gateway_app.py",
        restart_script="scripts/restart_knowledge_gateway.sh",
        port=8010,
    ),
    ShadowService(
        key="inbox_service",
        container_name="truffles-inbox-service",
        app_path="truffles-api/app/inbox_service_app.py",
        restart_script="scripts/restart_inbox_service.sh",
        port=8012,
    ),
    ShadowService(
        key="decision_core",
        container_name="truffles-decision-core",
        app_path="truffles-api/app/decision_core_app.py",
        restart_script="scripts/restart_decision_core.sh",
        port=8013,
    ),
    ShadowService(
        key="outbox_service",
        container_name="truffles-outbox-service",
        app_path="truffles-api/app/outbox_service_app.py",
        restart_script="scripts/restart_outbox_service.sh",
        port=8014,
    ),
)

TEXT_SUFFIXES = {
    "",
    ".cfg",
    ".conf",
    ".env",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".tsx",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}

EXCLUDED_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    "node_modules",
}

EXCLUDED_RELATIVE_PREFIXES = (
    "docs/_generated/",
    "console-web/tsconfig.tsbuildinfo",
)

GUARD_OR_TRUTH_FILES = {
    "scripts/arch_guard.py",
    "scripts/observability_truth.py",
    "scripts/product_work_map_guard.py",
    "scripts/release_topology_truth.py",
    "scripts/shadow_removal_dependency_truth.py",
    "scripts/tool_inventory_guard.py",
    "truffles-api/tests/architecture/test_observability_truth.py",
    "truffles-api/tests/architecture/test_product_work_map_guard.py",
    "truffles-api/tests/architecture/test_release_topology_truth.py",
    "truffles-api/tests/architecture/test_shadow_removal_dependency_truth.py",
    "truffles-api/tests/architecture/test_tool_inventory_guard.py",
}

DOC_OR_INVENTORY_PREFIXES = (
    "docs/",
    "SPECS/",
    "STRATEGY/",
)

DOC_OR_INVENTORY_FILES = {
    "AGENTS.md",
    "STATE.md",
    "STRUCTURE.md",
    "TECH.md",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _normalize(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _is_excluded(relative_path: str) -> bool:
    return any(relative_path.startswith(prefix) for prefix in EXCLUDED_RELATIVE_PREFIXES)


def _iter_repo_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative_path = _normalize(root, path)
        if _is_excluded(relative_path):
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        files.append(path)
    return sorted(files)


def _token_map(service: ShadowService) -> dict[str, str]:
    app_module = Path(service.app_path).stem
    restart_name = Path(service.restart_script).name
    return {
        "container_name": service.container_name,
        "app_path": service.app_path,
        "app_module": app_module,
        "app_import": f"app.{app_module}:app",
        "restart_script": service.restart_script,
        "restart_script_name": restart_name,
        "localhost_port": f"localhost:{service.port}",
        "loopback_port": f"127.0.0.1:{service.port}",
    }


def _reference_tokens(text: str, service: ShadowService) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    for token_type, token in _token_map(service).items():
        if token and token in text:
            matches.append({"token_type": token_type, "token": token})
    return matches


def _classify_reference(relative_path: str, service: ShadowService) -> str:
    if relative_path in {service.app_path, service.restart_script}:
        return "allowed_shadow_self"
    if relative_path in GUARD_OR_TRUTH_FILES or (
        relative_path.startswith("scripts/") and Path(relative_path).name.endswith("_guard.py")
    ):
        return "allowed_guard_or_truth"
    if relative_path.startswith("truffles-api/tests/") or "/tests/" in relative_path:
        return "allowed_test"
    if relative_path in DOC_OR_INVENTORY_FILES or relative_path.startswith(DOC_OR_INVENTORY_PREFIXES):
        return "allowed_doc_or_inventory"
    if relative_path.endswith((".yml", ".yaml")) or "docker-compose" in relative_path:
        return "blocking_deploy_config"
    if relative_path.startswith(".github/"):
        return "blocking_ci_config"
    if relative_path.startswith("truffles-api/app/"):
        return "blocking_runtime_code"
    if relative_path.startswith("console-web/src/"):
        return "blocking_console_code"
    if relative_path.startswith("scripts/"):
        return "blocking_operational_script"
    if relative_path.startswith("ops/"):
        return "blocking_operational_tool"
    return "blocking_unclassified"


def _record_reference(
    *,
    root: Path,
    path: Path,
    service: ShadowService,
    match: dict[str, str],
) -> dict[str, str]:
    relative_path = _normalize(root, path)
    return {
        "service": service.key,
        "container_name": service.container_name,
        "path": relative_path,
        "classification": _classify_reference(relative_path, service),
        **match,
    }


def collect_static_references(root: Path, extra_files: list[Path] | None = None) -> list[dict[str, str]]:
    files = _iter_repo_files(root)
    for path in extra_files or []:
        if path.exists() and path.is_file():
            files.append(path)

    references: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for path in sorted(set(files)):
        text = _read_text(path)
        for service in SHADOW_SERVICES:
            for match in _reference_tokens(text, service):
                reference = _record_reference(root=root, path=path, service=service, match=match)
                key = (
                    reference["path"],
                    reference["service"],
                    reference["token_type"],
                    reference["token"],
                )
                if key not in seen:
                    references.append(reference)
                    seen.add(key)
    return sorted(references, key=lambda item: (item["classification"], item["path"], item["service"], item["token_type"]))


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _docker_inspect(name: str) -> dict[str, Any] | None:
    completed = _run(["docker", "inspect", name])
    if completed.returncode != 0:
        return None
    payload = json.loads(completed.stdout)
    if not payload:
        return None
    return payload[0]


def _collect_running_container_dependency_hits() -> list[dict[str, str]]:
    completed = _run(["docker", "ps", "--format", "{{.Names}}"])
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "docker ps failed")

    hits: list[dict[str, str]] = []
    shadow_names = {service.container_name for service in SHADOW_SERVICES}
    for name in [line.strip() for line in completed.stdout.splitlines() if line.strip()]:
        if name in shadow_names:
            continue
        inspected = _docker_inspect(name)
        if not inspected:
            continue
        haystack = json.dumps(
            {
                "Config": inspected.get("Config", {}),
                "HostConfig": inspected.get("HostConfig", {}),
                "NetworkSettings": inspected.get("NetworkSettings", {}),
            },
            sort_keys=True,
        )
        for service in SHADOW_SERVICES:
            for match in _reference_tokens(haystack, service):
                hits.append(
                    {
                        "container": name,
                        "service": service.key,
                        "container_name": service.container_name,
                        "classification": "blocking_live_container_dependency",
                        **match,
                    }
                )
    return hits


def collect_runtime_state() -> dict[str, Any]:
    services: dict[str, Any] = {}
    runtime_errors: list[str] = []
    for service in SHADOW_SERVICES:
        inspected = _docker_inspect(service.container_name)
        if not inspected:
            services[service.key] = {
                "container_name": service.container_name,
                "exists": False,
                "running": False,
                "status": "missing",
            }
            continue
        state = inspected.get("State", {})
        running = bool(state.get("Running"))
        status = str(state.get("Status") or "unknown")
        services[service.key] = {
            "container_name": service.container_name,
            "exists": True,
            "running": running,
            "status": status,
        }
        if running:
            runtime_errors.append(f"shadow container still running -> {service.container_name}")

    live_dependency_hits = _collect_running_container_dependency_hits()
    runtime_errors.extend(
        f"running container {hit['container']} references shadow {hit['container_name']} via {hit['token_type']}={hit['token']}"
        for hit in live_dependency_hits
    )
    return {
        "checked": True,
        "services": services,
        "live_dependency_hits": live_dependency_hits,
        "errors": runtime_errors,
    }


def build_report(
    root: Path,
    *,
    include_runtime: bool = False,
    extra_files: list[Path] | None = None,
) -> dict[str, Any]:
    references = collect_static_references(root, extra_files=extra_files)
    blocking_references = [
        reference
        for reference in references
        if reference["classification"].startswith("blocking_")
    ]
    counts: dict[str, int] = {}
    for reference in references:
        counts[reference["classification"]] = counts.get(reference["classification"], 0) + 1

    runtime_state: dict[str, Any] = {"checked": False, "errors": []}
    if include_runtime:
        try:
            runtime_state = collect_runtime_state()
        except Exception as exc:  # pragma: no cover - environment-specific failure
            runtime_state = {"checked": True, "errors": [f"runtime dependency check failed -> {exc}"]}

    errors = [
        f"{reference['classification']} -> {reference['path']} references {reference['container_name']} via {reference['token_type']}={reference['token']}"
        for reference in blocking_references
    ]
    errors.extend(runtime_state.get("errors") or [])

    return {
        "valid": not errors,
        "contract_name": "shadow_removal_dependency_truth",
        "version": "2026-05-02.v1",
        "repo_root": str(root),
        "services": [
            {
                "key": service.key,
                "container_name": service.container_name,
                "app_path": service.app_path,
                "restart_script": service.restart_script,
                "port": service.port,
            }
            for service in SHADOW_SERVICES
        ],
        "static_reference_counts": counts,
        "blocking_references": blocking_references,
        "runtime_state": runtime_state,
        "errors": errors,
        "decision": "removal_ready_for_later_block" if not errors and include_runtime else "static_guard_ready" if not errors else "blocked",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--include-runtime", action="store_true")
    parser.add_argument("--extra-file", action="append", default=[])
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    root = Path(args.repo_root or _repo_root()).resolve()
    extra_files = [Path(item).resolve() for item in args.extra_file]
    report = build_report(root, include_runtime=args.include_runtime, extra_files=extra_files)

    if args.output:
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if report["valid"]:
        print("shadow_removal_dependency_truth: OK")
        if args.output:
            print(f"wrote {args.output}")
        return 0

    for error in report["errors"]:
        print(f"shadow_removal_dependency_truth: FAIL: {error}")
    if args.output:
        print(f"wrote {args.output}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
