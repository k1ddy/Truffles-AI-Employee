from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base_config() -> dict:
    return {
        "version": "test",
        "contract_name": "release_topology_truth",
        "required_release_cohort": "runtime_api_workers_console",
        "repo_contract": {
            "release_script": "scripts/restart_release.sh",
            "compose_file": "truffles-api/docker-compose.yml",
            "required_release_script_tokens": [
                'CONSOLE_SCRIPT="${CONSOLE_SCRIPT:-${SCRIPT_DIR}/restart_console_web.sh}"',
                'RESTART_CONSOLE_WEB="${RESTART_CONSOLE_WEB:-1}"',
                'RUN_RELEASE_TOPOLOGY_TRUTH="${RUN_RELEASE_TOPOLOGY_TRUTH:-1}"',
                'RELEASE_TOPOLOGY_TRUTH_SCRIPT="${RELEASE_TOPOLOGY_TRUTH_SCRIPT:-${SCRIPT_DIR}/release_topology_truth.py}"',
                'bash "$CONSOLE_SCRIPT"',
                'topology_truth_cmd=(',
                '"$TOPOLOGY_TRUTH_PYTHON"',
                '"$RELEASE_TOPOLOGY_TRUTH_SCRIPT"',
            ],
            "required_compose_container_tokens": [
                "container_name: truffles-outbox",
                "container_name: truffles-knowledge-activation",
                "container_name: truffles-sentinel",
                "container_name: truffles-console-web",
            ],
        },
        "required_services": [
            {
                "name": "truffles-api",
                "plane": "runtime",
                "commit_source": "admin_version",
                "build_source": "admin_version",
                "image_cohort": "runtime_main",
            },
            {
                "name": "truffles-outbox",
                "plane": "runtime_worker",
                "env_commit_key": "GIT_COMMIT",
                "env_build_key": "BUILD_TIME",
                "image_cohort": "runtime_main",
            },
            {
                "name": "truffles-knowledge-activation",
                "plane": "runtime_worker",
                "env_commit_key": "GIT_COMMIT",
                "env_build_key": "BUILD_TIME",
                "image_cohort": "runtime_main",
            },
            {
                "name": "truffles-sentinel",
                "plane": "runtime_worker",
                "env_commit_key": "GIT_COMMIT",
                "env_build_key": "BUILD_TIME",
                "image_cohort": "runtime_main",
            },
            {
                "name": "truffles-console-web",
                "plane": "control_plane",
                "env_commit_key": "NEXT_PUBLIC_BUILD_SHA",
                "env_build_key": "NEXT_PUBLIC_BUILD_TIME",
            },
        ],
        "optional_active_services": [
            {
                "name": "truffles-knowledge-activation-service",
                "plane": "runtime_side_service",
                "env_commit_key": "GIT_COMMIT",
                "env_build_key": "BUILD_TIME",
            }
        ],
        "shadow_services": [
            {
                "name": "truffles-provider-gateway",
                "plane": "shadow_gateway",
                "target_state": "shadow_only_disabled",
                "health_url": "http://localhost:8011/health",
                "disabled_health_fields": {
                    "inbound_enabled": False,
                    "status_enabled": False,
                    "inbox_enabled": False,
                },
            }
        ],
    }


def _make_repo(tmp_path: Path, *, config: dict, release_script: str, compose: str) -> Path:
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "truffles-api").mkdir(parents=True)
    (repo / "docs").mkdir(parents=True)
    (repo / "scripts" / "restart_release.sh").write_text(release_script, encoding="utf-8")
    (repo / "scripts" / "restart_console_web.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (repo / "scripts" / "release_topology_truth.py").write_text("# placeholder\n", encoding="utf-8")
    (repo / "truffles-api" / "docker-compose.yml").write_text(compose, encoding="utf-8")
    (repo / "docs" / "RELEASE_TOPOLOGY_TRUTH.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )
    return repo


def _base_snapshot() -> dict:
    commit = "9db031ee967999545f8a9673e7e57cf4d7202e73"
    image_id = "sha256:runtime"
    return {
        "api_version": {
            "version": "main",
            "git_commit": commit,
            "build_time": "2026-04-17T14:45:35Z",
        },
        "services": {
            "truffles-api": {
                "running": True,
                "image_id": image_id,
                "image_ref": "truffles-local:booking-matrix-20260417n",
            },
            "truffles-outbox": {
                "running": True,
                "image_id": image_id,
                "image_ref": "ghcr.io/k1ddy/truffles-ai-employee@sha256:runtime",
                "env": {"GIT_COMMIT": commit, "BUILD_TIME": "2026-04-17T14:45:35Z"},
                "status": "Up 10 days",
            },
            "truffles-knowledge-activation": {
                "running": True,
                "image_id": image_id,
                "image_ref": "ghcr.io/k1ddy/truffles-ai-employee@sha256:runtime",
                "env": {"GIT_COMMIT": commit, "BUILD_TIME": "2026-04-17T14:45:35Z"},
                "status": "Up 10 days",
            },
            "truffles-sentinel": {
                "running": True,
                "image_id": image_id,
                "image_ref": "ghcr.io/k1ddy/truffles-ai-employee@sha256:runtime",
                "env": {"GIT_COMMIT": commit, "BUILD_TIME": "2026-04-17T14:45:35Z"},
                "status": "Up 10 days",
            },
            "truffles-console-web": {
                "running": True,
                "image_id": "sha256:console",
                "image_ref": "truffles-api-console-web",
                "env": {"NEXT_PUBLIC_BUILD_SHA": commit, "NEXT_PUBLIC_BUILD_TIME": "2026-04-17T14:45:35Z"},
                "status": "Up 10 days",
            },
            "truffles-knowledge-activation-service": {
                "running": True,
                "image_id": image_id,
                "image_ref": "ghcr.io/k1ddy/truffles-ai-employee@sha256:runtime",
                "env": {"GIT_COMMIT": commit, "BUILD_TIME": "2026-04-17T14:45:35Z"},
                "status": "Up 10 days",
            },
            "truffles-provider-gateway": {
                "running": True,
                "image_id": "sha256:shadow",
                "image_ref": "legacy/provider-gateway",
                "env": {"GIT_COMMIT": "a0b56eaa0ef5395dfd94f844d29efc99ce3c60a0"},
                "status": "Up 2 months",
            },
        },
        "shadow_health": {
            "truffles-provider-gateway": {
                "ok": True,
                "payload": {
                    "status": "ok",
                    "service": "provider_gateway",
                    "inbound_enabled": False,
                    "status_enabled": False,
                    "inbox_enabled": False,
                },
            }
        },
    }


def test_validate_repo_contract_matches_current_repo() -> None:
    module = load_module("release_topology_truth", SCRIPTS / "release_topology_truth.py")
    config = module.load_config(ROOT / "docs" / "RELEASE_TOPOLOGY_TRUTH.yaml")

    assert module.validate_repo_contract(ROOT, config) == []


def test_validate_repo_contract_flags_missing_console_release_tokens(tmp_path: Path) -> None:
    module = load_module("release_topology_truth", SCRIPTS / "release_topology_truth.py")
    repo = _make_repo(
        tmp_path,
        config=_base_config(),
        release_script="#!/usr/bin/env bash\nbash \"$API_SCRIPT\"\n",
        compose="services:\n  truffles-outbox:\n    container_name: truffles-outbox\n",
    )
    config = module.load_config(repo / "docs" / "RELEASE_TOPOLOGY_TRUTH.yaml")

    violations = module.validate_repo_contract(repo, config)

    assert any("restart_release.sh missing required release token" in item for item in violations)
    assert any("docker-compose release cohort missing required container" in item for item in violations)


def test_evaluate_snapshot_accepts_required_cohort_and_warns_on_disabled_shadow_residue() -> None:
    module = load_module("release_topology_truth", SCRIPTS / "release_topology_truth.py")
    config = _base_config()

    payload = module.evaluate_snapshot(_base_snapshot(), config)

    assert payload["valid"] is True
    assert payload["warnings"]
    assert any("shadow service still mounted in disabled mode -> truffles-provider-gateway" in item for item in payload["warnings"])
    assert payload["active_shadow_services"] == {}


def test_evaluate_snapshot_flags_required_commit_mismatch() -> None:
    module = load_module("release_topology_truth", SCRIPTS / "release_topology_truth.py")
    config = _base_config()
    snapshot = _base_snapshot()
    snapshot["services"]["truffles-console-web"]["env"]["NEXT_PUBLIC_BUILD_SHA"] = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

    payload = module.evaluate_snapshot(snapshot, config)

    assert payload["valid"] is False
    assert any("required service commit mismatch -> truffles-console-web" in item for item in payload["errors"])


def test_evaluate_snapshot_flags_runtime_image_drift_and_active_optional_drift() -> None:
    module = load_module("release_topology_truth", SCRIPTS / "release_topology_truth.py")
    config = _base_config()
    snapshot = _base_snapshot()
    snapshot["services"]["truffles-sentinel"]["image_id"] = "sha256:other"
    snapshot["services"]["truffles-knowledge-activation-service"]["env"]["GIT_COMMIT"] = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    payload = module.evaluate_snapshot(snapshot, config)

    assert payload["valid"] is False
    assert any("runtime image cohort drift [runtime_main]" in item for item in payload["errors"])
    assert any("active optional service commit mismatch -> truffles-knowledge-activation-service" in item for item in payload["errors"])


def test_evaluate_snapshot_flags_shadow_authority_when_disable_contract_is_broken() -> None:
    module = load_module("release_topology_truth", SCRIPTS / "release_topology_truth.py")
    config = _base_config()
    snapshot = _base_snapshot()
    snapshot["shadow_health"]["truffles-provider-gateway"]["payload"]["inbound_enabled"] = True

    payload = module.evaluate_snapshot(snapshot, config)

    assert payload["valid"] is False
    assert any("shadow service authority-active -> truffles-provider-gateway" in item for item in payload["errors"])
    assert "truffles-provider-gateway" in payload["active_shadow_services"]


def test_evaluate_snapshot_can_fail_on_disabled_shadow_residue_if_requested() -> None:
    module = load_module("release_topology_truth", SCRIPTS / "release_topology_truth.py")
    config = _base_config()

    payload = module.evaluate_snapshot(_base_snapshot(), config, fail_on_active_shadow=True)

    assert payload["valid"] is False
    assert any("shadow service still mounted in disabled mode -> truffles-provider-gateway" in item for item in payload["errors"])
