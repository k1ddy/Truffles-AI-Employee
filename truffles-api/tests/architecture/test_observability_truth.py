from __future__ import annotations

import importlib.util
import json
import subprocess
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


def _base_config(tmp_root: Path | None = None) -> dict:
    def _path(name: str) -> str:
        assert tmp_root is not None
        return str(tmp_root / name)

    return {
        "version": "test",
        "contract_name": "observability_surface_truth",
        "repo_contract": {
            "required_file_tokens": [
                {
                    "path": "TECH.md",
                    "tokens": ["docs/OBSERVABILITY_SURFACES.yaml", "scripts/observability_truth.py"],
                }
            ]
        },
        "live_inputs": {
            "prometheus_api_url": "http://localhost:9090/api/v1/targets",
            "prometheus_config_path": _path("prometheus.yml") if tmp_root else "/tmp/prometheus.yml",
        },
        "proofs": {
            "prometheus_targets": [
                {
                    "id": "api-target",
                    "job": "truffles-api",
                    "scrape_url": "http://truffles-api:8000/metrics",
                }
            ],
            "http_checks": [
                {
                    "id": "grafana-health",
                    "url": "http://localhost:3001/api/health",
                    "expect_json": {"database": "ok"},
                }
            ],
            "yaml_checks": [
                {
                    "id": "grafana-prometheus-datasource",
                    "path": _path("prometheus-datasource.yml") if tmp_root else "/tmp/prometheus-datasource.yml",
                    "expected_datasource_names": ["Prometheus"],
                }
            ],
            "json_checks": [
                {
                    "id": "api-dashboard",
                    "path": _path("dashboard.json") if tmp_root else "/tmp/dashboard.json",
                    "expected_title": "Truffles API",
                }
            ],
        },
        "required_surfaces": [
            {
                "surface": "truffles-api",
                "plane": "runtime",
                "proof_ids": ["api-target", "api-dashboard"],
            },
            {
                "surface": "grafana",
                "plane": "observability",
                "proof_ids": ["grafana-health", "grafana-prometheus-datasource"],
            },
            {
                "surface": "truffles-console-web",
                "plane": "control_plane",
                "proof_ids": [],
                "gap_reason": "no stable proof yet",
            },
        ],
    }


def _write_repo(tmp_path: Path, *, config: dict, tech_text: str | None = None) -> Path:
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "scripts").mkdir(parents=True)
    (repo / "TECH.md").write_text(
        tech_text or "docs/OBSERVABILITY_SURFACES.yaml\nscripts/observability_truth.py\n",
        encoding="utf-8",
    )
    (repo / "docs" / "OBSERVABILITY_SURFACES.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )
    (repo / "scripts" / "observability_truth.py").write_text("# placeholder\n", encoding="utf-8")
    return repo


def test_validate_repo_contract_matches_current_repo() -> None:
    module = load_module("observability_truth", SCRIPTS / "observability_truth.py")
    config = module.load_config(ROOT / "docs" / "OBSERVABILITY_SURFACES.yaml")

    assert module.validate_repo_contract(ROOT, config) == []


def test_validate_repo_contract_flags_missing_tokens(tmp_path: Path) -> None:
    module = load_module("observability_truth", SCRIPTS / "observability_truth.py")
    temp_root = tmp_path / "files"
    temp_root.mkdir()
    config = _base_config(temp_root)
    repo = _write_repo(tmp_path, config=config, tech_text="missing token\n")
    loaded = module.load_config(repo / "docs" / "OBSERVABILITY_SURFACES.yaml")

    violations = module.validate_repo_contract(repo, loaded)

    assert any("TECH.md missing required observability token" in item for item in violations)


def test_run_truth_accepts_fully_covered_contract(monkeypatch, tmp_path: Path) -> None:
    module = load_module("observability_truth", SCRIPTS / "observability_truth.py")
    temp_root = tmp_path / "files"
    temp_root.mkdir()
    config = _base_config(temp_root)
    repo = _write_repo(tmp_path, config=config)

    (temp_root / "prometheus.yml").write_text(
        yaml.safe_dump({"scrape_configs": [{"job_name": "truffles-api"}]}),
        encoding="utf-8",
    )
    (temp_root / "prometheus-datasource.yml").write_text(
        yaml.safe_dump({"datasources": [{"name": "Prometheus"}]}),
        encoding="utf-8",
    )
    (temp_root / "dashboard.json").write_text(
        json.dumps({"title": "Truffles API"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        module,
        "_fetch_prometheus_targets",
        lambda _url: {
            "data": {
                "activeTargets": [
                    {
                        "labels": {"job": "truffles-api"},
                        "scrapeUrl": "http://truffles-api:8000/metrics",
                        "health": "up",
                    }
                ]
            }
        },
    )
    monkeypatch.setattr(
        module,
        "_fetch_url",
        lambda _url: (200, json.dumps({"database": "ok"})),
    )

    payload = module.run_truth(repo, repo / "docs" / "OBSERVABILITY_SURFACES.yaml")

    assert payload["valid"] is False
    assert payload["surface_results"]["truffles-api"]["ok"] is True
    assert payload["surface_results"]["grafana"]["ok"] is True
    assert payload["surface_results"]["truffles-console-web"]["ok"] is False
    assert any("surface has no observability proof mapping -> truffles-console-web" in item for item in payload["surface_errors"])


def test_run_truth_flags_failed_prometheus_and_dashboard(monkeypatch, tmp_path: Path) -> None:
    module = load_module("observability_truth", SCRIPTS / "observability_truth.py")
    temp_root = tmp_path / "files"
    temp_root.mkdir()
    config = _base_config(temp_root)
    config["required_surfaces"] = [
        {
            "surface": "truffles-api",
            "plane": "runtime",
            "proof_ids": ["api-target", "api-dashboard"],
        }
    ]
    repo = _write_repo(tmp_path, config=config)

    (temp_root / "prometheus.yml").write_text(
        yaml.safe_dump({"scrape_configs": [{"job_name": "other"}]}),
        encoding="utf-8",
    )
    (temp_root / "prometheus-datasource.yml").write_text(
        yaml.safe_dump({"datasources": [{"name": "Prometheus"}]}),
        encoding="utf-8",
    )
    (temp_root / "dashboard.json").write_text(
        json.dumps({"title": "Wrong"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        module,
        "_fetch_prometheus_targets",
        lambda _url: {"data": {"activeTargets": []}},
    )
    monkeypatch.setattr(
        module,
        "_fetch_url",
        lambda _url: (200, json.dumps({"database": "ok"})),
    )

    payload = module.run_truth(repo, repo / "docs" / "OBSERVABILITY_SURFACES.yaml")

    assert payload["valid"] is False
    assert payload["proof_results"]["api-target"]["ok"] is False
    assert payload["proof_results"]["api-dashboard"]["ok"] is False
    assert any("surface proof failures -> truffles-api" in item for item in payload["surface_errors"])


def test_http_check_supports_docker_container_resolution(monkeypatch) -> None:
    module = load_module("observability_truth", SCRIPTS / "observability_truth.py")

    def _fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=["docker", "inspect", "truffles-console-web"],
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "NetworkSettings": {
                            "Networks": {
                                "truffles_internal-net": {"IPAddress": "172.24.0.14"},
                                "proxy-net": {"IPAddress": "172.20.0.5"},
                            }
                        }
                    }
                ]
            ),
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(module, "_fetch_url", lambda url: (200, f"reachable -> {url} -> Truffles Console"))

    result = module._evaluate_http_check(
        {
            "id": "console-root",
            "docker_container": "truffles-console-web",
            "docker_network": "truffles_internal-net",
            "docker_port": 3000,
            "path": "/",
            "expect_substring": "Truffles Console",
        }
    )

    assert result["ok"] is True
    assert result["details"]["resolved_url"] == "http://172.24.0.14:3000/"


def _docker_inspect_result(*, running: bool, status: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["docker", "inspect", "truffles-provider-gateway"],
        returncode=0,
        stdout=json.dumps([{"State": {"Running": running, "Status": status}}]),
        stderr="",
    )


def test_shadow_state_check_accepts_running_disabled(monkeypatch) -> None:
    module = load_module("observability_truth", SCRIPTS / "observability_truth.py")

    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: _docker_inspect_result(running=True, status="running"))
    monkeypatch.setattr(
        module,
        "_fetch_url",
        lambda _url: (
            200,
            json.dumps(
                {
                    "status": "ok",
                    "service": "provider_gateway",
                    "inbound_enabled": False,
                    "status_enabled": False,
                    "inbox_enabled": False,
                    "outbound_enabled": False,
                }
            ),
        ),
    )

    result = module._evaluate_shadow_state_check(
        {
            "id": "provider-gateway-stopped-or-disabled",
            "docker_container": "truffles-provider-gateway",
            "health_url": "http://localhost:8011/health",
            "expect_json": {"status": "ok", "service": "provider_gateway"},
            "disabled_health_fields": {
                "inbound_enabled": False,
                "status_enabled": False,
                "inbox_enabled": False,
                "outbound_enabled": False,
            },
        }
    )

    assert result["ok"] is True
    assert result["details"]["observed_shadow_state"] == "running_disabled"


def test_shadow_state_check_accepts_stopped_container(monkeypatch) -> None:
    module = load_module("observability_truth", SCRIPTS / "observability_truth.py")

    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: _docker_inspect_result(running=False, status="exited"))
    monkeypatch.setattr(
        module,
        "_fetch_url",
        lambda _url: (_ for _ in ()).throw(AssertionError("stopped containers must not require a health endpoint")),
    )

    result = module._evaluate_shadow_state_check(
        {
            "id": "provider-gateway-stopped-or-disabled",
            "docker_container": "truffles-provider-gateway",
            "health_url": "http://localhost:8011/health",
        }
    )

    assert result["ok"] is True
    assert result["details"]["observed_shadow_state"] == "stopped"


def test_shadow_state_check_rejects_running_authority(monkeypatch) -> None:
    module = load_module("observability_truth", SCRIPTS / "observability_truth.py")

    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: _docker_inspect_result(running=True, status="running"))
    monkeypatch.setattr(
        module,
        "_fetch_url",
        lambda _url: (
            200,
            json.dumps(
                {
                    "status": "ok",
                    "service": "provider_gateway",
                    "inbound_enabled": True,
                    "status_enabled": False,
                    "inbox_enabled": False,
                    "outbound_enabled": False,
                }
            ),
        ),
    )

    result = module._evaluate_shadow_state_check(
        {
            "id": "provider-gateway-stopped-or-disabled",
            "docker_container": "truffles-provider-gateway",
            "health_url": "http://localhost:8011/health",
            "expect_json": {"status": "ok", "service": "provider_gateway"},
            "disabled_health_fields": {"inbound_enabled": False},
        }
    )

    assert result["ok"] is False
    assert result["details"]["observed_shadow_state"] == "running_authority_or_unhealthy"
    assert result["details"]["mismatches"] == ["inbound_enabled expected False, got True"]
